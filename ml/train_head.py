"""Train a CodeAuthentic AI-authorship classifier on real, labeled code.

Frozen per-language CodeBERT 770D features + StandardScaler/LogisticRegression.
The importer writes a manifest with Problem_id groups, so solutions to the same
problem never appear in both training and evaluation sets.

New classifiers are written to ml/candidates, NOT deployed automatically.
Review test metrics, then use ml.activate_head for explicit installation.

Usage:
  python -m ml.train_head --language python --data dataset/python
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, brier_score_loss, confusion_matrix,
                             f1_score, precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.predictor import (CodeTooShortError, HEADS_DIR, MODEL_IDS,
                          count_tokens, extract_features, MIN_TOKENS)

CANDIDATES_DIR = HEADS_DIR.parent / "candidates"
FEATURE_VERSION = "codebert-frozen-meanpool-masked-nll-770-v1"
LABEL_NAMES = {0: "human", 1: "ai"}
LANGUAGE_EXTENSIONS = {"python": ".py", "java": ".java", "c": ".c"}


@dataclass(frozen=True)
class Example:
    path: Path
    label: int
    group: str
    code_sha256: str


def load_records(data_dir: Path, language: str, *, allow_ungrouped: bool = False) -> list[Example]:
    """Load only local labeled files. A manifest is required for defensible grouped splits."""
    if language not in MODEL_IDS:
        raise ValueError(f"Unsupported language: {language}")
    root = data_dir.resolve()
    manifest = root / "manifest.jsonl"
    samples: list[Example] = []
    if manifest.is_file():
        for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            info = json.loads(line)
            label = int(info["label"])
            if label not in LABEL_NAMES:
                raise ValueError(f"Invalid label on manifest line {line_number}")
            relative = Path(str(info["path"]))
            path = (root / relative).resolve()
            if not path.is_relative_to(root):
                raise ValueError(f"Manifest path escapes dataset directory on line {line_number}")
            if path.suffix.lower() != LANGUAGE_EXTENSIONS[language] or not path.is_file():
                raise ValueError(f"Missing/wrong language file on manifest line {line_number}: {relative}")
            if path.parent.name != LABEL_NAMES[label]:
                raise ValueError(f"Manifest label/path mismatch on line {line_number}")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != str(info["sha256"]):
                raise ValueError(f"Source file changed since import: {path}")
            group = str(info["group_id"]).strip()
            if not group:
                raise ValueError(f"Missing problem group on line {line_number}")
            samples.append(Example(path, label, group, digest))
    elif allow_ungrouped:
        print("[WARNING] No manifest: can't guarantee problem-level grouping. Prefer the published dataset importer.")
        for label, folder in LABEL_NAMES.items():
            for path in sorted((root / folder).glob("*")):
                if path.suffix.lower() == LANGUAGE_EXTENSIONS[language] and path.is_file():
                    digest = hashlib.sha256(path.read_bytes()).hexdigest()
                    samples.append(Example(path, label, f"file:{digest}", digest))
    else:
        raise FileNotFoundError(
            f"{manifest} is missing. First import the original published dataset with "
            "python -m ml.import_research_dataset --csv <path>; for legacy ungrouped "
            "folders, explicitly supply --allow-ungrouped (less reliable evaluation)."
        )
    seen: dict[str, int] = {}
    unique: list[Example] = []
    for sample in samples:
        if sample.code_sha256 in seen:
            if seen[sample.code_sha256] != sample.label:
                raise ValueError("Identical code occurs under both labels: correct dataset before training")
            continue
        seen[sample.code_sha256] = sample.label
        unique.append(sample)
    return unique


def _has_both(labels: np.ndarray, indices: np.ndarray, min_per_class: int = 5) -> bool:
    counts = Counter(int(v) for v in labels[indices])
    return counts[0] >= min_per_class and counts[1] >= min_per_class


def split_grouped(records: list[Example], seed: int = 42) -> dict[str, np.ndarray]:
    """Deterministic 70/15/15 problem-group holdouts; no group appears in two splits."""
    if not records:
        raise ValueError("No labeled code files available")
    labels = np.array([r.label for r in records], dtype=int)
    groups = np.array([r.group for r in records], dtype=str)
    counts = Counter(labels.tolist())
    if counts[0] < 50 or counts[1] < 50:
        raise ValueError(f"Need at least 50 human and 50 AI code files per language; found {dict(counts)}")
    if len(set(groups)) < 30:
        raise ValueError("Need at least 30 distinct programming problems for a meaningful group split")
    full = np.arange(len(records))
    for left, right in GroupShuffleSplit(n_splits=100, test_size=0.30, random_state=seed).split(full, labels, groups):
        if not _has_both(labels, left, 30) or not _has_both(labels, right, 10):
            continue
        for v, t in GroupShuffleSplit(n_splits=100, test_size=0.50, random_state=seed+17).split(
            right, labels[right], groups[right]
        ):
            val = right[v]
            test = right[t]
            if not (_has_both(labels, val) and _has_both(labels, test)):
                continue
            splits = {"train": np.sort(left), "validation": np.sort(val), "test": np.sort(test)}
            a, b, c = (set(groups[idx]) for idx in splits.values())
            assert not (a & b or a & c or b & c)
            return splits
    raise ValueError("Could not make group-disjoint train/validation/test sets containing both labels; review dataset")


def features_for_records(records: list[Example], language: str, cache_root: Path) -> np.ndarray:
    """Feature cache holds only deterministic frozen embeddings, never classifier predictions."""
    cache_root.mkdir(parents=True, exist_ok=True)
    result = []
    for number, record in enumerate(records, 1):
        key = hashlib.sha256(f"{FEATURE_VERSION}:{MODEL_IDS[language]}:{record.code_sha256}".encode()).hexdigest()
        cache = cache_root / f"{key}.npy"
        if cache.is_file():
            vector = np.load(cache, allow_pickle=False)
        else:
            code = record.path.read_text(encoding="utf-8", errors="strict")
            vector = np.asarray(extract_features(code, language), dtype=np.float64)
            if vector.shape != (770,) or not np.all(np.isfinite(vector)):
                raise ValueError(f"CodeBERT produced invalid features for {record.path}")
            np.save(cache, vector, allow_pickle=False)
        if vector.shape != (770,) or not np.all(np.isfinite(vector)):
            raise ValueError(f"Feature cache invalid for {record.path}; delete {cache} and retry")
        result.append(vector)
        if number % 25 == 0 or number == len(records):
            print(f"  Features ready: {number}/{len(records)}", flush=True)
    return np.stack(result)


def calculate_metrics(y: np.ndarray, probability: np.ndarray) -> dict:
    predictions = (probability >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, predictions, labels=[0, 1]).ravel().tolist()
    return {
        "samples": int(len(y)), "human_samples": int((y == 0).sum()), "ai_samples": int((y == 1).sum()),
        "accuracy": float(accuracy_score(y, predictions)),
        "ai_precision": float(precision_score(y, predictions, zero_division=0)),
        "ai_recall": float(recall_score(y, predictions, zero_division=0)),
        "ai_f1": float(f1_score(y, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, probability)),
        "brier_score": float(brier_score_loss(y, probability)),
        "human_false_positive_rate": float(fp / (tn + fp)),
        "confusion_matrix": {"true_human": tn, "human_flagged_ai": fp, "ai_missed": fn, "ai_flagged_ai": tp},
        "threshold": 0.5,
    }


def train(language: str, data_dir_str: str, *, allow_ungrouped: bool = False) -> int:
    data_dir = Path(data_dir_str)
    records = load_records(data_dir, language, allow_ungrouped=allow_ungrouped)
    # Reject too-short samples before splitting; the same real CodeBERT tokenizer
    # is used for submitted code. Never silently skip model/dependency errors.
    valid = []
    for record in records:
        code = record.path.read_text(encoding="utf-8")
        if count_tokens(code, language) >= MIN_TOKENS:
            valid.append(record)
    print(f"[FILTER] Skipped {len(records) - len(valid)} code files below {MIN_TOKENS} CodeBERT tokens")
    records = valid
    splits = split_grouped(records)
    print(f"[TRAINING] {language}: {len(records)} code samples, {len(set(r.group for r in records))} problem groups")
    for name, indices in splits.items():
        counts = Counter(records[int(i)].label for i in indices)
        print(f"  {name}: {len(indices)} files, human={counts[0]}, AI={counts[1]}, groups={len(set(records[int(i)].group for i in indices))}")
    print("[FEATURES] Extracting frozen CodeBERT embeddings (can be slow on CPU)...")
    try:
        features = features_for_records(records, language, data_dir / ".feature_cache")
    except CodeTooShortError as exc:
        raise ValueError(f"Dataset contains code below the {30}-token minimum: {exc}. Filter/replace it, then retry.") from exc
    labels = np.array([r.label for r in records])
    train_idx, val_idx, test_idx = (splits[name] for name in ("train", "validation", "test"))
    classifier = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
    ])
    classifier.fit(features[train_idx], labels[train_idx])
    val_proba = classifier.predict_proba(features[val_idx])[:, list(classifier.classes_).index(1)]
    test_proba = classifier.predict_proba(features[test_idx])[:, list(classifier.classes_).index(1)]
    validation = calculate_metrics(labels[val_idx], val_proba)
    test = calculate_metrics(labels[test_idx], test_proba)
    print(f"[RESULTS] validation={json.dumps(validation, indent=2)}")
    print(f"[RESULTS] held-out TEST={json.dumps(test, indent=2)}")
    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    target = CANDIDATES_DIR / f"{language}.joblib"
    joblib.dump(classifier, target)
    fingerprint = hashlib.sha256(target.read_bytes()).hexdigest()
    report = {
        "report_version": 1, "training_date_utc": datetime.now(timezone.utc).isoformat(),
        "language": language, "feature_version": FEATURE_VERSION, "model_id": MODEL_IDS[language],
        "source": "See dataset/<language>/DATASET_SOURCE.json and original labeled samples",
        "dataset_path": str(data_dir.resolve()), "number_of_problem_groups": len(set(r.group for r in records)),
        "group_disjoint_splits": True, "sample_count": len(records), "grouping_method": "Problem_id" if not allow_ungrouped else "input_folder_groups",
        "validation_metrics": validation, "test_metrics": test,
        "candidate_sha256": fingerprint,
        "limitations": "This score is a statistical estimate, not proof of AI authorship. "
                       "Test performance on this dataset cannot establish reliability on students' work, "
                       "other LLMs, unseen coding tasks or paraphrased/mixed code."
    }
    (CANDIDATES_DIR / f"{language}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[STAGED] Candidate: {target.resolve()}")
    print(f"[STAGED] Evaluation: {(CANDIDATES_DIR / f'{language}.json').resolve()}")
    print("[NOT DEPLOYED] Review held-out human false-positive rate and evaluation report before activation.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Train and evaluate an undeployed CodeBERT classification head")
    parser.add_argument("--language", choices=sorted(MODEL_IDS), required=True)
    parser.add_argument("--data", type=str, required=True)
    parser.add_argument("--allow-ungrouped", action="store_true", help="Riskier compatibility mode without problem IDs")
    args = parser.parse_args()
    try:
        return train(args.language, args.data, allow_ungrouped=args.allow_ungrouped)
    except (ValueError, OSError, ImportError) as exc:
        print(f"[TRAINING FAILED] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
