"""Tests of dataset provenance, leak-free splitting, safe staging and no fake model outputs.

Synthetic snippets here test the *plumbing*, never classifier accuracy.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from ml import activate_head, predictor, train_head
from ml.import_research_dataset import import_dataset
from ml.train_head import Example, calculate_metrics, load_records, split_grouped


def write_csv(path: Path, rows):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["Problem_id", "Sample_Code", "Generated", "Language", "Source"])
        writer.writeheader()
        writer.writerows(rows)


def test_research_dataset_import_preserves_labels_and_problem_groups(tmp_path):
    original = tmp_path / "HumanVsAI_CodeDataset.csv"
    write_csv(original, [
        {"Problem_id": "123", "Sample_Code": "def x():\n    return 1", "Generated": "0", "Language": "Python", "Source": "human"},
        {"Problem_id": "123", "Sample_Code": "def x():\n    return 2", "Generated": "1", "Language": "Python", "Source": "AI"},
        {"Problem_id": "456", "Sample_Code": "int main() { return 0; }", "Generated": "AI", "Language": "C", "Source": "ChatGPT"},
        {"Problem_id": "456", "Sample_Code": "int main() { return 1; }", "Generated": "Human", "Language": "C", "Source": "Human"},
        {"Problem_id": "789", "Sample_Code": "std::cout << 1;", "Generated": "AI", "Language": "C++", "Source": "Human"},
    ])
    root = tmp_path / "dataset"
    report = import_dataset(original, root, dry_run=True)
    assert not root.exists()
    assert len(report["python"]) == 2
    import_dataset(original, root)
    rows = load_records(root / "python", "python")
    assert sorted(r.label for r in rows) == [0, 1]
    assert len({r.group for r in rows}) == 1
    assert (root / "python" / "DATASET_SOURCE.json").exists()
    assert not list((root / "c").glob("**/*.cpp"))
    with pytest.raises(FileExistsError):
        import_dataset(original, root)


def test_conflicting_authorship_labels_are_rejected(tmp_path):
    original = tmp_path / "conflicting.csv"
    write_csv(original, [
        {"Problem_id": "1", "Sample_Code": "print('same')", "Generated": "0", "Language": "Python", "Source": "A"},
        {"Problem_id": "1", "Sample_Code": "print('same')", "Generated": "1", "Language": "Python", "Source": "B"},
    ])
    with pytest.raises(ValueError, match="Conflicting authorship"):
        import_dataset(original, tmp_path / "dataset")


def test_missing_problem_id_rejected_for_data_leakage_prevention(tmp_path):
    original = tmp_path / "no_groups.csv"
    write_csv(original, [{"Problem_id": "", "Sample_Code": "print('hello')", "Generated": "1",
                          "Language": "Python", "Source": "source"}])
    with pytest.raises(ValueError, match="Missing Problem_id"):
        import_dataset(original, tmp_path / "dataset")


def test_group_disjoint_reproducible_splits():
    records = [Example(Path(f"{p}_{label}.py"), label, f"problem:{p}", f"{p}-{label}")
               for p in range(150) for label in [0, 1]]
    first = split_grouped(records)
    again = split_grouped(records)
    for name in first:
        assert np.array_equal(first[name], again[name])
        assert {records[int(i)].label for i in first[name]} == {0, 1}
    group_sets = [{records[int(i)].group for i in idx} for idx in first.values()]
    assert group_sets[0].isdisjoint(group_sets[1])
    assert group_sets[0].isdisjoint(group_sets[2])
    assert group_sets[1].isdisjoint(group_sets[2])
    assert sum(len(v) for v in first.values()) == len(records)


def test_accuracy_report_counts_false_positive_rate():
    y = np.array([0, 0, 1, 1])
    probability = np.array([0.1, 0.9, 0.3, 0.8])
    result = calculate_metrics(y, probability)
    assert result["confusion_matrix"] == {
        "true_human": 1, "human_flagged_ai": 1, "ai_missed": 1, "ai_flagged_ai": 1,
    }
    assert result["human_false_positive_rate"] == 0.5
    assert result["samples"] == 4


def test_no_training_data_fails_without_writing_candidate(tmp_path, monkeypatch):
    monkeypatch.setattr(train_head, "CANDIDATES_DIR", tmp_path / "candidates")
    with pytest.raises(FileNotFoundError, match="manifest"):
        train_head.load_records(tmp_path / "dataset/python", "python")
    assert not (tmp_path / "candidates").exists()


def _candidate(tmp_path, monkeypatch, fpr=0.01):
    candidate = tmp_path / "candidates"
    live = tmp_path / "heads"
    candidate.mkdir()
    monkeypatch.setattr(activate_head, "CANDIDATES_DIR", candidate)
    monkeypatch.setattr(activate_head, "HEADS_DIR", live)
    (candidate / "python.joblib").write_bytes(b"TEST ONLY: not a real trained classifier")
    sha = hashlib.sha256((candidate / "python.joblib").read_bytes()).hexdigest()
    report = {"language": "python", "model_id": predictor.MODEL_IDS["python"],
              "feature_version": train_head.FEATURE_VERSION, "group_disjoint_splits": True,
              "grouping_method": "Problem_id",
              "candidate_sha256": sha, "test_metrics": {"human_samples": 50, "ai_samples": 50,
                      "human_false_positive_rate": fpr, "ai_f1": 0.80}}
    (candidate / "python.json").write_text(json.dumps(report), encoding="utf-8")
    return live


def test_activation_requires_review_and_evidence(tmp_path, monkeypatch):
    live = _candidate(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="confirm-reviewed"):
        activate_head.activate("python", confirm_reviewed=False)
    assert not live.exists()
    installed = activate_head.activate("python", confirm_reviewed=True)
    assert installed.exists()
    assert (live / "python.json").exists()


def test_activation_blocks_high_false_positive_rate(tmp_path, monkeypatch):
    live = _candidate(tmp_path, monkeypatch, fpr=0.40)
    with pytest.raises(ValueError, match="false-positive"):
        activate_head.activate("python", confirm_reviewed=True)
    assert not live.exists()


def test_old_joblib_without_evaluation_report_fails_closed(tmp_path, monkeypatch):
    (tmp_path / "python.joblib").write_bytes(b"not a trained model")
    monkeypatch.setattr(predictor, "HEADS_DIR", tmp_path)
    with pytest.raises(predictor.HeadNotTrainedError, match="evaluation report"):
        predictor._get_trained_head("python")


def test_staged_candidate_can_be_promoted_after_mocked_feature_pipeline(tmp_path, monkeypatch):
    """Integration *plumbing* test only. Synthetic features here DO NOT validate detection."""
    source = tmp_path / "fixture.csv"
    examples = []
    for problem in range(200):
        for label, name in [(0, "human"), (1, "ai")]:
            examples.append({"Problem_id": problem,
                             "Sample_Code": f"def program_{problem}():\n    {name}_marker_{problem} = 17\n    return 42",
                             "Generated": str(label), "Language": "Python", "Source": "TEST-ONLY"})
    write_csv(source, examples)
    data_root = tmp_path / "dataset"
    import_dataset(source, data_root)

    def fake_codebert_features(code, language):
        assert language == "python"
        feature = np.zeros(770)
        feature[0] = 3.0 if "ai_marker_" in code else -3.0
        return feature

    monkeypatch.setattr(train_head, "count_tokens", lambda code, language: 60)
    monkeypatch.setattr(train_head, "extract_features", fake_codebert_features)
    monkeypatch.setattr(train_head, "CANDIDATES_DIR", tmp_path / "candidates")
    assert train_head.train("python", str(data_root / "python")) == 0
    assert (tmp_path / "candidates" / "python.joblib").exists()
    report = json.loads((tmp_path / "candidates" / "python.json").read_text())
    assert report["test_metrics"]["human_false_positive_rate"] == 0
    assert report["test_metrics"]["ai_f1"] == 1
    monkeypatch.setattr(activate_head, "CANDIDATES_DIR", tmp_path / "candidates")
    monkeypatch.setattr(activate_head, "HEADS_DIR", tmp_path / "heads")
    target = activate_head.activate("python", confirm_reviewed=True)
    assert target.is_file()
    monkeypatch.setattr(predictor, "HEADS_DIR", tmp_path / "heads")
    monkeypatch.setattr(predictor, "extract_features", fake_codebert_features)
    predictor._HEADS.pop("python", None)
    assert predictor.predict("def fake(): ai_marker_999=1", "python") > 0.5
    assert predictor.predict("def fake(): human_marker_999=1", "python") < 0.5
    predictor._HEADS.pop("python", None)
