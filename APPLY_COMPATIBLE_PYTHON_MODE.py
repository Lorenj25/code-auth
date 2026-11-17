"""Safe, narrowly-scoped adapter for experimental Python CodeBERT.

This installer DOES NOT overwrite the user's newer predictor with the old file.
It patches only recognized statements used by the existing training-aware
predictor. If an ML-relevant statement has changed, abort before writing.
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

EXPECTED_CANDIDATE_SHA256 = "762feb11d7cf735995e8dc1b54d3d6ef62d3e97de0e7637355fa6603c6223c1c"
# Optional UI update is allowed ONLY for the exact original reviewed version.
ORIGINAL_UI_HASHES = {
    Path('src/utils/api.ts'): '772df41ddc4f9c48c80c1cfd88d097fc8f81c1156ebd97c07f6c3edd4426cd13',
    Path('src/components/InstructorDashboard.tsx'): '13bb091bbe7073a2bba53105430f7e11d5660224aae2f17b5fee580c70266e90',
}
ENV_VAR = "CODEAUTHENTIC_PYTHON_TEST_MODE"


def stop(message: str):
    raise RuntimeError("STOPPED SAFELY: " + message + ". No project files were changed.")


def sha256(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def substitute_exact(source: str, original: str, replacement: str, note: str) -> str:
    count = source.count(original)
    if count != 1:
        stop(f"Cannot safely identify {note}: expected exactly one matching code block, found {count}")
    return source.replace(original, replacement, 1)


def build_patch(source: str) -> tuple[str, bool]:
    # Reject partial updates, or a significantly different predictor implementation.
    if ENV_VAR in source:
        if 'def _head_directory(' in source and 'def _experimental_python(' in source:
            print("[INFO] Python experimental routing already exists in predictor; leaving it as-is.")
            return source, False
        stop("Test-mode marker exists but its implementation is not recognized")
    try:
        tree = ast.parse(source, filename="ml/predictor.py")
    except SyntaxError as exc:
        stop(f"Current predictor has a Python syntax error ({exc})")
    funcs = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if not {"_verified_head_report", "model_readiness", "_get_trained_head", "predict", "analyze"}.issubset(funcs):
        stop("Current predictor has an incompatible structure; current ml/predictor.py is needed for a custom patch")
    # Every edit below is anchored to the existing verified-report approach.
    # Preserve all unrelated code, comments, thresholds and Java/C definitions.
    edits = [
        (
            'HEADS_DIR = Path(__file__).resolve().parent / "heads"\n',
            '''HEADS_DIR = Path(__file__).resolve().parent / "heads"
CANDIDATES_DIR = Path(__file__).resolve().parent / "candidates"
# Local-only: Python candidate loading is explicitly enabled by the test launcher.
PYTHON_TEST_MODE_ENV = "CODEAUTHENTIC_PYTHON_TEST_MODE"


def _experimental_python(language: str) -> bool:
    return language == "python" and os.getenv(PYTHON_TEST_MODE_ENV, "").strip() == "1"


def _head_directory(language: str) -> Path:
    return CANDIDATES_DIR if _experimental_python(language) else HEADS_DIR


def _head_cache_key(language: str) -> str:
    return f"{language}:{_head_directory(language).resolve()}"
''',
            "model-head directory declaration",
        ),
        (
            '    path = HEADS_DIR / f"{language}.joblib"\n    report_path = HEADS_DIR / f"{language}.json"\n',
            '    head_dir = _head_directory(language)\n    path = head_dir / f"{language}.joblib"\n    report_path = head_dir / f"{language}.json"\n',
            "verified classifier/report lookup",
        ),
        (
            '        available = (HEADS_DIR / f"{lang}.joblib").is_file()\n',
            '        available = (_head_directory(lang) / f"{lang}.joblib").is_file()\n        experimental = _experimental_python(lang)\n',
            "readiness file lookup",
        ),
        (
            '                       "loaded_in_process": lang in _HEADS,\n',
            '                       "loaded_in_process": _head_cache_key(lang) in _HEADS,\n',
            "readiness cache state",
        ),
        (
            '                       "model_loaded_in_process": lang in _MODELS,\n',
            '                       "model_loaded_in_process": lang in _MODELS,\n                       "experimental": experimental,\n                       "source": "candidate" if experimental else "active",\n',
            "readiness metadata",
        ),
        (
            '    ready = [lang for lang in MODEL_IDS if heads[lang]["evaluated_head_present"] and all(dependencies.values())]\n',
            '    ready = [lang for lang in MODEL_IDS if heads[lang]["evaluated_head_present"] and all(dependencies.values())]\n    experimental_ready = [lang for lang in ready if heads[lang]["experimental"]]\n',
            "readiness calculations",
        ),
        (
            '    return {"dependencies": dependencies, "languages": heads, "ready_languages": ready,\n',
            '    return {"dependencies": dependencies, "languages": heads, "ready_languages": ready,\n            "experimental_languages": experimental_ready,\n            "active_languages": [lang for lang in ready if lang not in experimental_ready],\n',
            "readiness summary",
        ),
        (
            '    head_path = HEADS_DIR / f"{language}.joblib"\n    if language not in _HEADS:\n',
            '    head_path = _head_directory(language) / f"{language}.joblib"\n    cache_key = _head_cache_key(language)\n    if cache_key not in _HEADS:\n',
            "verified classifier loader",
        ),
        (
            '        _HEADS[language] = joblib.load(head_path)\n    head = _HEADS[language]\n',
            '        _HEADS[cache_key] = joblib.load(head_path)\n    head = _HEADS[cache_key]\n',
            "classifier in-memory caching",
        ),
    ]
    changed = source
    for before, after, description in edits:
        changed = substitute_exact(changed, before, after, description)
    try:
        compile(changed, "ml/predictor.py", "exec")
    except SyntaxError as exc:
        stop(f"Generated patch failed syntax check ({exc})")
    # Ensure the previous verification steps have not been deleted or bypassed.
    for required in ('candidate_sha256', 'FEATURE_VERSION', 'group_disjoint_splits', 'human_false_positive_rate', 'joblib.load', '_verified_head_report(language)'):
        if required not in changed:
            stop(f"Existing verification contract is missing: {required}")
    return changed, True


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".codeauthentic_", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def install(project: Path) -> None:
    patch_folder = Path(__file__).resolve().parent
    if not (project / 'START_SYSTEM.bat').is_file() or not (project / 'ml/predictor.py').is_file():
        stop('Project root must contain START_SYSTEM.bat and ml/predictor.py')
    trusted_candidates = {}
    for ext in ('joblib', 'json'):
        rel = Path(f'ml/candidates/python.{ext}')
        bundled = patch_folder / rel
        if not bundled.is_file():
            stop(f'Patch archive is missing {rel}')
        trusted_candidates[rel] = bundled.read_bytes()
        existing = project / rel
        if existing.is_file() and existing.read_bytes() != trusted_candidates[rel]:
            stop(f'Your existing {rel} is different; refusing to overwrite it')
    model_file = trusted_candidates[Path('ml/candidates/python.joblib')]
    report_bytes = trusted_candidates[Path('ml/candidates/python.json')]
    if sha256(model_file) != EXPECTED_CANDIDATE_SHA256:
        stop('Bundled classifier does not match the previously verified SHA-256')
    try:
        report = json.loads(report_bytes)
        if report['candidate_sha256'] != EXPECTED_CANDIDATE_SHA256 or report['language'] != 'python' or report['feature_version'] != 'codebert-frozen-meanpool-masked-nll-770-v1':
            stop('Bundled classifier report does not match Python CodeBERT feature configuration')
    except (KeyError, TypeError, ValueError) as exc:
        stop(f'Classifier report cannot be validated ({exc})')

    target = project / 'ml/predictor.py'
    payload = target.read_bytes()
    prefix = b'\xef\xbb\xbf' if payload.startswith(b'\xef\xbb\xbf') else b''
    encoding_payload = payload[len(prefix):]
    try:
        original = encoding_payload.decode('utf-8')
    except UnicodeDecodeError:
        stop('Predictor source is not UTF-8 and cannot be patched safely')
    windows_newlines = b'\r\n' in encoding_payload
    normalized = original.replace('\r\n', '\n')
    modified, changed = build_patch(normalized)
    if windows_newlines:
        modified = modified.replace('\n', '\r\n')
    modified_bytes = prefix + modified.encode('utf-8')

    launcher = project / 'START_PYTHON_TEST_MODE.bat'
    bundled_launcher = (patch_folder / 'START_PYTHON_TEST_MODE.bat').read_bytes()
    if launcher.exists() and launcher.read_bytes() != bundled_launcher:
        stop('An existing START_PYTHON_TEST_MODE.bat differs from the patch; refusing to overwrite it')
    targets = {target: modified_bytes, launcher: bundled_launcher}
    for rel, data in trusted_candidates.items():
        dest = project / rel
        targets[dest] = data
    # UI is optional. Preserve both frontend source files if EITHER one differs
    # from the exact snapshot we reviewed. Do not mix API + dashboard versions.
    if all((project / rel).is_file() and sha256((project / rel).read_bytes()) == old_sha
           for rel, old_sha in ORIGINAL_UI_HASHES.items()):
        for rel in ORIGINAL_UI_HASHES:
            targets[project / rel] = (patch_folder / rel).read_bytes()
        print('[UI] Existing frontend exactly matches reviewed snapshot; applying verified UI updates.')
    else:
        print('[UI] Skipping frontend update: at least one UI file differs. Existing frontend preserved.')
        print('[UI] Python inference can still work; new experimental model badge may not be visible.')
    actual_changes = {path: data for path,data in targets.items() if not path.is_file() or path.read_bytes() != data}
    if not actual_changes:
        print('[SUCCESS] Python testing patch already installed. No changes needed.')
        return

    backup = project / ('_python_test_backup_' + dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    # Back up everything that will be overwritten, before changing any file.
    try:
        for path in actual_changes:
            if path.is_file():
                dest = backup / path.relative_to(project)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
        created = set()
        overwritten = set()
        for path, data in actual_changes.items():
            existed = path.exists()
            atomic_write(path, data)
            if existed:
                overwritten.add(path)
            else:
                created.add(path)
    except Exception:
        # Restore overwritten files; remove only files freshly added by us.
        for path in overwritten if 'overwritten' in locals() else ():
            prior = backup / path.relative_to(project)
            if prior.is_file():
                shutil.copy2(prior, path)
        for path in created if 'created' in locals() else ():
            path.unlink(missing_ok=True)
        raise
    print('[SUCCESS] Compatible Python-only test mode installed.')
    print('[SAFETY] Java/C models, datasets, .env, and database untouched.')
    print(f'[BACKUP] {backup}')
    print('[NEXT] Close existing local server windows, then run START_PYTHON_TEST_MODE.bat')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Install an isolated Python classifier test mode without overwriting unrelated source changes')
    parser.add_argument('--project', required=True, type=Path)
    args = parser.parse_args()
    try:
        install(args.project.resolve())
    except Exception as exc:
        print(f'[ERROR] {exc}', file=sys.stderr)
        sys.exit(1)
