"""Import the published HumanVsAI_CodeDataset.csv into CodeAuthentic training folders.

Dataset source: Boukili et al. (2026), Data in Brief, DOI 10.1016/j.dib.2026.112527
Repository: https://data.mendeley.com/datasets/kjh95n54f8/1

This tool NEVER generates training labels or AI samples. Download the real CSV
from the original publisher and review its terms and provenance first.
Usage:
  python -m ml.import_research_dataset --csv "C:/Downloads/HumanVsAI_CodeDataset.csv"
  python -m ml.import_research_dataset --csv path/to/file.csv --dry-run
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

SOURCE = "Boukili et al. (2026), Data in Brief 65:112527, DOI:10.1016/j.dib.2026.112527"
SOURCE_URL = "https://data.mendeley.com/datasets/kjh95n54f8/1"
LANGUAGE_EXTENSIONS = {"python": ".py", "java": ".java", "c": ".c"}
REQUIRED = {"Problem_id", "Sample_Code", "Generated", "Language", "Source"}


def parse_language(value: str) -> str | None:
    token = str(value).strip().lower()
    return {"python": "python", "py": "python", "java": "java", "c": "c", "c language": "c", "c++": None,
            "cpp": None, "c plus plus": None}.get(token)


def parse_label(value: str) -> int:
    token = str(value).strip().lower()
    if token in {"1", "true", "yes", "ai", "generated", "ai-generated", "chatgpt", "machine"}:
        return 1
    if token in {"0", "false", "no", "human", "human-written", "original", "not generated"}:
        return 0
    raise ValueError(f"Unrecognized Generated value {value!r}; inspect the original CSV and update the mapping deliberately.")


def read_records(csv_path: Path) -> dict[str, list[dict]]:
    if not csv_path.is_file():
        raise FileNotFoundError(f"Dataset CSV not found: {csv_path}")
    csv.field_size_limit(10_000_000)
    data: dict[str, list[dict]] = {lang: [] for lang in LANGUAGE_EXTENSIONS}
    seen: dict[tuple[str, str], int] = {}
    skipped = Counter()
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or not REQUIRED.issubset(set(reader.fieldnames)):
            raise ValueError(f"CSV needs columns {sorted(REQUIRED)}; received {reader.fieldnames}")
        for number, row in enumerate(reader, start=2):
            lang = parse_language(row["Language"])
            if lang is None:
                skipped["unsupported_language"] += 1
                continue
            label = parse_label(row["Generated"])
            code = (row["Sample_Code"] or "").replace("\r\n", "\n")
            if not code.strip():
                skipped["empty_code"] += 1
                continue
            code = code.rstrip("\n") + "\n"
            digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
            key = (lang, digest)
            if key in seen:
                if seen[key] != label:
                    raise ValueError(f"Conflicting authorship labels for identical {lang} code at CSV line {number}.")
                skipped["duplicate_code"] += 1
                continue
            seen[key] = label
            problem = str(row["Problem_id"] or "").strip()
            # Problem-level grouping is critical: do not split implementations
            # of the same coding task between training and test sets.
            if not problem:
                raise ValueError(f"Missing Problem_id at CSV line {number}; cannot prevent same-task train/test leakage")
            group = f"problem:{problem}"
            data[lang].append({"code": code, "label": label, "group": group,
                               "sha256": digest, "row": number, "original_source": str(row["Source"] or "")})
    print(f"[IMPORT] {csv_path.name}: skipped={dict(skipped)}")
    for lang, records in data.items():
        counts = Counter(r["label"] for r in records)
        print(f"  {lang}: human={counts[0]}, AI={counts[1]}, problem_groups={len(set(r['group'] for r in records))}")
    return data


def import_dataset(csv_path: Path, output: Path, *, dry_run: bool = False, overwrite: bool = False) -> dict:
    data = read_records(csv_path)
    if dry_run:
        print("[DRY RUN] Nothing written.")
        return data
    existing = [str(output / lang / "manifest.jsonl") for lang in data if (output / lang / "manifest.jsonl").exists()]
    if existing and not overwrite:
        raise FileExistsError(f"Existing manifest(s) found: {existing}. Use --overwrite only after backing up the dataset.")
    for lang, records in data.items():
        root = output / lang
        root.mkdir(parents=True, exist_ok=True)
        entries = []
        for rec in records:
            label_name = "ai" if rec["label"] else "human"
            rel = Path(label_name) / f"sample_{rec['row']:06d}_{rec['sha256'][:12]}{LANGUAGE_EXTENSIONS[lang]}"
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            # Write precisely the bytes that were hashed above. Windows text-mode
            # writes convert LF to CRLF and otherwise invalidate the manifest.
            dest.write_bytes(rec["code"].encode("utf-8"))
            entries.append({"path": rel.as_posix(), "label": rec["label"], "group_id": rec["group"],
                            "sha256": hashlib.sha256(rec["code"].encode("utf-8")).hexdigest(),
                            "original_source": rec["original_source"]})
        # Write manifest only after all files have been written successfully.
        (root / "manifest.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in entries), encoding="utf-8")
        (root / "DATASET_SOURCE.json").write_text(json.dumps({"title": SOURCE, "url": SOURCE_URL,
            "local_csv_name": csv_path.name, "language": lang, "imported_rows": len(entries),
            "notice": "Review dataset license and known limitations; do not mix student submissions into training data."}, indent=2), encoding="utf-8")
    print(f"[IMPORTED] Data stored under {output.resolve()} (gitignored by this project).")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Import the original labeled HumanVsAI CSV without inventing samples")
    parser.add_argument("--csv", type=Path, required=True, help="Downloaded original HumanVsAI_CodeDataset.csv")
    parser.add_argument("--output", type=Path, default=Path("dataset"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        import_dataset(args.csv, args.output, dry_run=args.dry_run, overwrite=args.overwrite)
        return 0
    except (OSError, ValueError) as exc:
        print(f"[ERROR] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
