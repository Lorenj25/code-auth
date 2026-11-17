"""Safely activate/verify two locally-trained CodeAuthentic classifier heads.

Runs against the USER'S LOCAL PROJECT. Does not patch any frontend/backend source.
Only trust artifacts trained locally by your project: .joblib uses pickle.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

LANGUAGES = ("python", "java")
ARTIFACTS = tuple(f"{language}.{ext}" for language in LANGUAGES for ext in ("joblib", "json"))


def digest(path: Path) -> str:
    block_hash = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            block_hash.update(chunk)
    return block_hash.hexdigest()


def atomic_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent, delete=False) as tmp:
            temp_path = Path(tmp.name)
            with source.open("rb") as src:
                shutil.copyfileobj(src, tmp)
        os.replace(temp_path, target)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def project_modules(root: Path):
    for required in ("ml/predictor.py", "ml/train_head.py", "ml/verify_pipeline.py", "ml/activate_head.py", "backend/analysis.py", "backend/routes/submissions.py", "src/utils/api.ts"):
        if not (root / required).is_file():
            raise RuntimeError(f"Project file is missing: {required}. Check -ProjectRoot.")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.chdir(root)
    from ml import predictor, train_head
    if predictor.HEADS_DIR.resolve() != (root / "ml" / "heads").resolve():
        raise RuntimeError("The predictor uses an unexpected model folder. Refusing to install.")
    if train_head.CANDIDATES_DIR.resolve() != (root / "ml" / "candidates").resolve():
        raise RuntimeError("The training script uses an unexpected candidate folder. Refusing to install.")
    return predictor, train_head


def review_candidate(root: Path, language: str, predictor, train_head) -> tuple[Path, Path]:
    candidate = root / "ml" / "candidates" / f"{language}.joblib"
    report_path = root / "ml" / "candidates" / f"{language}.json"
    if not candidate.is_file() or not report_path.is_file():
        raise RuntimeError(f"Missing saved candidate for {language}: {candidate.name} + {report_path.name}.")
    if candidate.stat().st_size == 0:
        raise RuntimeError(f"{candidate.name} is empty.")
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        test = report["test_metrics"]
    except (ValueError, KeyError, OSError, TypeError) as exc:
        raise RuntimeError(f"Invalid evaluation report for {language}: {exc}") from exc
    if report.get("language") != language or report.get("model_id") != predictor.MODEL_IDS[language]:
        raise RuntimeError(f"{language} candidate report model/language mismatch.")
    if report.get("feature_version") != train_head.FEATURE_VERSION:
        raise RuntimeError(f"{language} model feature version does not match this project. No files changed.")
    if not report.get("group_disjoint_splits") or report.get("grouping_method") != "Problem_id":
        raise RuntimeError(f"{language} report lacks problem-group held-out evaluation.")
    if digest(candidate) != report.get("candidate_sha256"):
        raise RuntimeError(f"{language} classifier SHA-256 does not match its evaluation report.")
    if test.get("human_samples", 0) < 20 or test.get("ai_samples", 0) < 20:
        raise RuntimeError(f"{language} held-out evaluation has too few samples.")
    if test.get("human_false_positive_rate", 1) > 0.15 or test.get("ai_f1", 0) < 0.70:
        raise RuntimeError(f"{language} classifier did not meet this project's review thresholds.")
    print(f"[VERIFIED] {language}: {test['samples']} held-out samples, "
          f"accuracy={test['accuracy']:.2%}, FPR={test['human_false_positive_rate']:.2%}; "
          f"SHA-256 matches.")
    return candidate, report_path


def status(root: Path, predictor) -> bool:
    result = predictor.model_readiness()
    deps = result.get("dependencies", {})
    for language in ("python", "java", "c"):
        info = result["languages"].get(language, {})
        available = language in result.get("ready_languages", [])
        label = "READY" if available else "NOT READY"
        print(f"[{label}] {language}: {info.get('issue') or 'verified local classifier'}")
    missing = [name for name, present in deps.items() if not present]
    if missing:
        print("[DEPENDENCIES] Missing: " + ", ".join(missing))
    if "c" not in result.get("ready_languages", []):
        print("[EXPECTED] C is not yet trained. The all-three-languages readiness flag may remain false.")
    return not missing and all(x in result.get("ready_languages", []) for x in LANGUAGES)


def rollback_files(root: Path, manifest: dict, backup_dir: Path, *, enforce_hashes: bool) -> None:
    heads = root / "ml" / "heads"
    files = manifest["files"]
    if enforce_hashes:
        # Fail before changing ANY file if the local model has been edited since installation.
        for item in files:
            dst = heads / item["name"]
            if not dst.is_file() or digest(dst) != item["installed_sha256"]:
                raise RuntimeError(f"Cannot roll back {item['name']}: it changed since this install. Manual review needed.")
    for item in files:
        dst = heads / item["name"]
        if item["previous_sha256"] is None:
            dst.unlink(missing_ok=True)
        else:
            saved = backup_dir / "previous" / item["name"]
            if not saved.is_file() or digest(saved) != item["previous_sha256"]:
                raise RuntimeError(f"Backup corrupted or missing: {saved}")
            atomic_copy(saved, dst)
    print("[RESTORED] Previous active Python and Java classifier state restored.")


def install(root: Path, predictor, train_head) -> None:
    candidate_files = {}
    for lang in LANGUAGES:
        joblib_file, report_file = review_candidate(root, lang, predictor, train_head)
        candidate_files[f"{lang}.joblib"] = joblib_file
        candidate_files[f"{lang}.json"] = report_file
    heads = root / "ml" / "heads"
    heads.mkdir(parents=True, exist_ok=True)

    # Never overwrite a differing active classifier; those may contain newer work.
    differing = [name for name, src in candidate_files.items()
                 if (heads / name).exists() and digest(heads / name) != digest(src)]
    if differing:
        raise RuntimeError("Active models differ from the candidates: " + ", ".join(differing) +
                           ". Refusing to overwrite existing models. Send this output for review.")
    to_install = [name for name, src in candidate_files.items() if not (heads / name).is_file()]
    if not to_install:
        print("[UNCHANGED] Both language heads already match the verified candidates.")
        if not status(root, predictor):
            raise RuntimeError("Model readiness did not pass; inspect dependency and report errors above.")
        return

    backups = root / "ml" / "_python_java_test_backups"
    backups.mkdir(parents=True, exist_ok=True)
    backup_dir = backups / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f_UTC")
    (backup_dir / "previous").mkdir(parents=True)
    manifest = {"created_utc": datetime.now(timezone.utc).isoformat(),
                "project_root": str(root), "purpose": "Python+Java local experimental integration",
                "files": []}

    # Capture ALL four prior artifacts so a single rollback can restore the complete state.
    for name in ARTIFACTS:
        original = heads / name
        previous_sha = digest(original) if original.is_file() else None
        if previous_sha:
            shutil.copy2(original, backup_dir / "previous" / name)
        manifest["files"].append({"name": name, "previous_sha256": previous_sha,
                                  "installed_sha256": digest(candidate_files[name])})
    (backup_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    try:
        for name in to_install:
            atomic_copy(candidate_files[name], heads / name)
            print(f"[INSTALLED] ml/heads/{name}")
        # Verify via the ORIGINAL predictor, using its integrity checks; only local classifiers.
        if not status(root, predictor):
            raise RuntimeError("Post-install readiness check failed.")
        for language in LANGUAGES:
            predictor._get_trained_head(language)  # Checks classifier classes and feature dimensions.
        print("[SUCCESS] Python and Java are installed for local testing. C was not modified.")
        print(f"[BACKUP] {backup_dir}")
        print("[NEXT] Restart the local FastAPI backend, then use the separate smoke-test command.")
    except Exception:
        print("[ERROR] Installation verification failed. Automatically restoring previous model files.")
        rollback_files(root, manifest, backup_dir, enforce_hashes=False)
        raise


def rollback(root: Path) -> None:
    base = root / "ml" / "_python_java_test_backups"
    backup_dirs = sorted((p for p in base.iterdir() if (p / "manifest.json").is_file()), reverse=True) if base.exists() else []
    if not backup_dirs:
        raise RuntimeError("No prior two-language installation backup found.")
    backup_dir = backup_dirs[0]
    manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))
    if Path(manifest["project_root"]).resolve() != root.resolve():
        raise RuntimeError("This backup belongs to a different project folder.")
    rollback_files(root, manifest, backup_dir, enforce_hashes=True)
    print("[NEXT] Restart the local FastAPI backend to clear in-process classifier caches.")


def smoke_test(root: Path, predictor) -> None:
    if not status(root, predictor):
        raise RuntimeError("Python and Java must both be READY before running smoke tests.")
    here = Path(__file__).resolve().parent
    for lang, sample in (("python", "tests/smoke_python.py"), ("java", "tests/SmokeJava.java")):
        file_path = here / sample
        if not file_path.is_file():
            raise RuntimeError(f"Missing sample: {file_path}")
        print(f"\n[INFERENCE] Testing {lang} with a synthetic smoke-test sample (not an accuracy test)...", flush=True)
        result = subprocess.run([sys.executable, "-m", "ml.verify_pipeline", "--language", lang,
                                 "--file", str(file_path)], cwd=root, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"{lang} inference smoke test failed; see the traceback above.")
    print("\n[SUCCESS] Both trained models returned real inference output. The database/UI upload flow still needs a manual test.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe local integration for the verified Python + Java CodeBERT models")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--action", choices=("install", "status", "test", "rollback"), required=True)
    args = parser.parse_args()
    root = args.project_root.expanduser().resolve()
    try:
        if not root.is_dir():
            raise RuntimeError(f"Project root does not exist: {root}")
        predictor, train_head = project_modules(root)
        if args.action == "install":
            install(root, predictor, train_head)
        elif args.action == "status":
            if not status(root, predictor):
                return 1
        elif args.action == "test":
            smoke_test(root, predictor)
        elif args.action == "rollback":
            rollback(root)
    except Exception as exc:
        print(f"[STOPPED SAFELY] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
