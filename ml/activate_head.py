"""Install an evaluated classifier into ml/heads after manual review.

Usage:
  python -m ml.activate_head --language python --confirm-reviewed

Only load joblib files trained locally using the supplied project's code.
Never load untrusted artifacts (joblib is pickle-based).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from ml.predictor import HEADS_DIR, MODEL_IDS
from ml.train_head import CANDIDATES_DIR, FEATURE_VERSION


def activate(language: str, *, confirm_reviewed: bool) -> Path:
    if not confirm_reviewed:
        raise ValueError("Review the candidate metrics and supply --confirm-reviewed before activation.")
    if language not in MODEL_IDS:
        raise ValueError(f"Unknown language: {language}")
    candidate = CANDIDATES_DIR / f"{language}.joblib"
    report_file = CANDIDATES_DIR / f"{language}.json"
    if not candidate.is_file() or not report_file.is_file():
        raise FileNotFoundError(f"Missing {candidate} or {report_file}; train with real labeled data first.")
    report = json.loads(report_file.read_text(encoding="utf-8"))
    if report.get("language") != language or report.get("model_id") != MODEL_IDS[language] or report.get("feature_version") != FEATURE_VERSION:
        raise ValueError("Candidate report does not match the configured CodeBERT feature extractor")
    fingerprint = hashlib.sha256(candidate.read_bytes()).hexdigest()
    if report.get("candidate_sha256") != fingerprint:
        raise ValueError("Candidate file was changed after evaluation; reject installation")
    if not report.get("group_disjoint_splits") or report.get("grouping_method") != "Problem_id":
        raise ValueError("Deployment requires a dataset with genuine Problem_id-grouped evaluation")
    test = report["test_metrics"]
    if test.get("human_samples", 0) < 20 or test.get("ai_samples", 0) < 20:
        raise ValueError("Too few held-out examples per class to deploy for instructor review")
    if test.get("human_false_positive_rate", 1) > 0.15:
        raise ValueError("Held-out false-positive rate exceeds 15%; improve/evaluate before deployment")
    if test.get("ai_f1", 0) < 0.70:
        raise ValueError("Held-out AI-detection F1 is below 0.70; improve/evaluate before deployment")
    HEADS_DIR.mkdir(exist_ok=True, parents=True)
    dest = HEADS_DIR / f"{language}.joblib"
    if dest.exists():
        backup = HEADS_DIR / f"{language}.joblib.backup"
        shutil.copy2(dest, backup)
        print(f"[BACKUP] Previous classifier saved to {backup}")
    shutil.copy2(candidate, dest)
    shutil.copy2(report_file, HEADS_DIR / f"{language}.json")
    print(f"[ACTIVATED] {dest}; restart backend to load updated head")
    print("[NOTE] AI estimates remain advisory only; check on real student-like assignments before actual use.")
    return dest


def main() -> int:
    p = argparse.ArgumentParser(description="Promote a real evaluated CodeBERT classifier to the live system")
    p.add_argument("--language", choices=sorted(MODEL_IDS), required=True)
    p.add_argument("--confirm-reviewed", action="store_true")
    args = p.parse_args()
    try:
        activate(args.language, confirm_reviewed=args.confirm_reviewed)
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"[NOT ACTIVATED] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
