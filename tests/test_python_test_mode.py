"""Lightweight integration guards; do not download models or contact the DB."""
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ml import predictor


class PythonTestModeTests(unittest.TestCase):
    def test_python_candidate_is_not_enabled_by_default(self):
        with patch.dict(os.environ, {predictor.PYTHON_TEST_MODE_ENV: ""}):
            self.assertEqual(predictor._head_directory("python"), predictor.HEADS_DIR)
            with self.assertRaises(predictor.HeadNotTrainedError):
                predictor._verified_head_report("python")

    def test_opt_in_only_affects_python(self):
        with patch.dict(os.environ, {predictor.PYTHON_TEST_MODE_ENV: "1"}):
            self.assertEqual(predictor._head_directory("python"), predictor.CANDIDATES_DIR)
            self.assertEqual(predictor._head_directory("java"), predictor.HEADS_DIR)
            self.assertEqual(predictor._head_directory("c"), predictor.HEADS_DIR)
            self.assertEqual(predictor._verified_head_report("python")["language"], "python")

    def test_candidate_integrity_check_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as dirname:
            folder = Path(dirname)
            (folder / "python.json").write_bytes((predictor.CANDIDATES_DIR / "python.json").read_bytes())
            (folder / "python.joblib").write_bytes((predictor.CANDIDATES_DIR / "python.joblib").read_bytes() + b"changed")
            with patch.object(predictor, "CANDIDATES_DIR", folder), patch.dict(os.environ, {predictor.PYTHON_TEST_MODE_ENV: "1"}):
                with self.assertRaisesRegex(predictor.HeadNotTrainedError, "checksum mismatch"):
                    predictor._verified_head_report("python")

    def test_readiness_reports_experimental_python_without_java_c(self):
        with patch.dict(os.environ, {predictor.PYTHON_TEST_MODE_ENV: "1"}):
            with patch.object(predictor.importlib.util, "find_spec", return_value=object()):
                status = predictor.model_readiness()
            self.assertEqual(status["ready_languages"], ["python"])
            self.assertEqual(status["experimental_languages"], ["python"])
            self.assertEqual(status["active_languages"], [])
            self.assertEqual(status["languages"]["python"]["source"], "candidate")
            self.assertFalse(status["languages"]["java"]["evaluated_head_present"])
            self.assertFalse(status["languages"]["c"]["evaluated_head_present"])

    def test_scoring_stays_fail_closed_without_head(self):
        with patch.dict(os.environ, {predictor.PYTHON_TEST_MODE_ENV: ""}):
            with self.assertRaises(predictor.HeadNotTrainedError):
                predictor.predict("def f(x): return x", "python")


if __name__ == "__main__":
    unittest.main()
