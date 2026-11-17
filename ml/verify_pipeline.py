"""Offline readiness checks and optional real end-to-end CodeBERT inference.

Usage:
  python -m ml.verify_pipeline --status
  python -m ml.verify_pipeline --language python --file path/to/sample.py

Never creates classifier weights, never substitutes synthetic probabilities.
Only use trusted local classifier .joblib artifacts (joblib uses pickle).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ml.predictor import EXT_TO_LANG, analyze, model_readiness


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify CodeAuthentic real ML readiness and inference")
    parser.add_argument("--status", action="store_true", help="Offline checks of dependencies and trained head files")
    parser.add_argument("--language", choices=["python", "java", "c"])
    parser.add_argument("--file", type=Path, help="Source code file for a real CodeBERT inference test")
    args = parser.parse_args()

    if args.status or not args.file:
        status = model_readiness()
        print(json.dumps(status, indent=2))
        if not args.file:
            if args.language:
                return 0 if args.language in status["ready_languages"] else 1
            return 0 if status["ready_for_inference_attempt"] else 1

    if not args.language:
        parser.error("--language is required with --file")
    if EXT_TO_LANG.get(args.file.suffix.lower()) != args.language:
        parser.error(f"File extension does not match --language={args.language}")

    try:
        code = args.file.read_text(encoding="utf-8", errors="ignore")
        print(json.dumps(analyze(code, args.file.name), indent=2))
    except Exception as exc:
        print(f"INFERENCE FAILED (no score generated): {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
