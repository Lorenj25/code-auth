"""
CodeAuthentic - ML Predictor Module.
Feature extraction and AI probability inference using frozen CodeBERT representations.
Computes a 770-dimensional feature vector:
- 768-dim: mean-pooled last hidden state of unmasked tokens
- 2-dim: mean and std of masked-token negative log-likelihood (perplexity signal)
Passes features through fitted StandardScaler + LogisticRegression head.
"""

from __future__ import annotations

import importlib.util
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, Optional, Tuple
import numpy as np

# Risk level classification thresholds
RISK_LOW_MAX = 0.40
RISK_MEDIUM_MAX = 0.70
MIN_TOKENS = 30

EXT_TO_LANG = {
    ".c": "c",
    ".java": "java",
    ".py": "python",
}

MODEL_IDS = {
    "c": "neulab/codebert-c",
    "java": "neulab/codebert-java",
    "python": "neulab/codebert-python",
}

# Cache for loaded tokenizers and models
_TOKENIZERS: Dict[str, any] = {}
_MODELS: Dict[str, any] = {}
_HEADS: Dict[str, any] = {}

HEADS_DIR = Path(__file__).resolve().parent / "heads"
CANDIDATES_DIR = Path(__file__).resolve().parent / "candidates"
# Strictly opt-in for a LOCAL Python pilot. Production still reads ml/heads.
# The candidate is checked against its evaluation report and SHA-256 as usual.
PYTHON_TEST_MODE_ENV = "CODEAUTHENTIC_PYTHON_TEST_MODE"


def _experimental_python(language: str) -> bool:
    return language == "python" and os.getenv(PYTHON_TEST_MODE_ENV, "").strip() == "1"


def _head_directory(language: str) -> Path:
    return CANDIDATES_DIR if _experimental_python(language) else HEADS_DIR


def _head_cache_key(language: str) -> str:
    # Prevent a head loaded from one location being reused if the mode changes.
    return f"{language}:{_head_directory(language).resolve()}"


class CodeTooShortError(Exception):
    """Raised when submitted code contains fewer than 30 tokens."""
    pass


class HeadNotTrainedError(Exception):
    """Raised when the scikit-learn classifier head for a language has not been fitted."""
    pass


def _verified_head_report(language: str) -> dict:
    """Verify candidate promotion evidence BEFORE unpickling a classifier.

    This is an integrity/quality check, not a security signature. Only load
    .joblib artifacts produced in a trusted environment.
    """
    head_dir = _head_directory(language)
    path = head_dir / f"{language}.joblib"
    report_path = head_dir / f"{language}.json"
    if not path.is_file() or path.stat().st_size == 0:
        raise HeadNotTrainedError(
            f"No evaluated AI-authorship classifier is available for {language} in {head_dir}. "
            "Frozen CodeBERT alone is not an AI-code detector. "
            "Import real labeled samples, train and evaluate a head, then explicitly activate it."
        )
    if not report_path.is_file():
        raise HeadNotTrainedError(
            f"{language} classifier file exists but its evaluation report is missing "
            f"(expected {report_path}). Do not use unverified AI-authorship scores."
        )
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        from ml.train_head import FEATURE_VERSION
        if report.get("language") != language or report.get("model_id") != MODEL_IDS[language]:
            raise ValueError("classifier report model/language mismatch")
        if report.get("feature_version") != FEATURE_VERSION or not report.get("group_disjoint_splits") or report.get("grouping_method") != "Problem_id":
            raise ValueError("classifier lacks matching features or problem-level holdout evaluation")
        if report.get("candidate_sha256") != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError("classifier checksum mismatch")
        test = report["test_metrics"]
        if test.get("human_samples", 0) < 20 or test.get("ai_samples", 0) < 20:
            raise ValueError("classifier needs at least 20 held-out examples per class")
        if test.get("human_false_positive_rate", 1) > 0.15 or test.get("ai_f1", 0) < 0.70:
            raise ValueError("held-out quality criteria were not met")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise HeadNotTrainedError(f"{language} classifier evaluation/integrity failed: {exc}") from exc
    return report


def model_readiness() -> dict:
    """Offline readiness: one language can be active while others await training."""
    required = ("numpy", "torch", "transformers", "joblib", "sklearn")
    dependencies = {name: importlib.util.find_spec(name) is not None for name in required}
    heads = {}
    for lang in MODEL_IDS:
        available = (_head_directory(lang) / f"{lang}.joblib").is_file()
        experimental = _experimental_python(lang)
        try:
            _verified_head_report(lang)
            verified = True
            problem = None
        except HeadNotTrainedError as exc:
            verified = False
            problem = str(exc)
        heads[lang] = {"file_present": available, "evaluated_head_present": verified,
                       "loaded_in_process": _head_cache_key(lang) in _HEADS,
                       "model_loaded_in_process": lang in _MODELS,
                       "experimental": experimental,
                       "source": "candidate" if experimental else "active",
                       "issue": problem}
    ready = [lang for lang in MODEL_IDS if heads[lang]["evaluated_head_present"] and all(dependencies.values())]
    experimental_ready = [lang for lang in ready if heads[lang]["experimental"]]
    return {"dependencies": dependencies, "languages": heads, "ready_languages": ready,
            "experimental_languages": experimental_ready,
            "active_languages": [lang for lang in ready if lang not in experimental_ready],
            "ready_for_inference_attempt": len(ready) == len(MODEL_IDS),
            "note": "Readiness verifies a local evaluation report and artifacts, not real-world detection accuracy. "
                    "Experimental Python candidate inference is for review only; do not use results as proof of authorship. "
                    "Use ml.verify_pipeline --file for an end-to-end inference test."}


def _get_trained_head(language: str):
    """Return the real fitted head; reject missing or incompatible artifacts."""
    import joblib

    if language not in MODEL_IDS:
        raise ValueError(f"Unsupported language: {language}")
    # Prevent loading random unverified .joblib files or plain MLM checkpoints.
    _verified_head_report(language)
    head_path = _head_directory(language) / f"{language}.joblib"
    cache_key = _head_cache_key(language)
    if cache_key not in _HEADS:
        # joblib files are pickles; load only classifier artifacts created by this project.
        _HEADS[cache_key] = joblib.load(head_path)
    head = _HEADS[cache_key]
    classes = list(getattr(head, "classes_", []))
    if sorted(classes) != [0, 1] or not hasattr(head, "predict_proba"):
        raise ValueError(f"Trained classifier for '{language}' must have human=0 and AI=1 classes.")
    feature_count = getattr(head, "n_features_in_", None)
    if feature_count is not None and int(feature_count) != 770:
        raise ValueError(f"Trained classifier for '{language}' expects {feature_count} features, not 770.")
    return head


def preload_models() -> None:
    """
    Loads all three CodeBERT models and tokenizers into memory.
    Optional helper for dedicated ML workers; not called during normal FastAPI startup.
    """
    import torch
    from transformers import AutoModelForMaskedLM, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[PRELOAD] Loading CodeBERT models on device: {device}")

    for lang, model_id in MODEL_IDS.items():
        if lang not in _TOKENIZERS:
            print(f"[PRELOAD] Loading tokenizer for {lang} ({model_id})...")
            _TOKENIZERS[lang] = AutoTokenizer.from_pretrained(model_id)

        if lang not in _MODELS:
            print(f"[PRELOAD] Loading model weights for {lang} ({model_id})...")
            try:
                model = AutoModelForMaskedLM.from_pretrained(model_id, device_map="auto")
            except Exception:
                model = AutoModelForMaskedLM.from_pretrained(model_id).to(device)
            model.eval()
            # Freeze all weights - study does NOT fine-tune CodeBERT weights
            for param in model.parameters():
                param.requires_grad = False
            _MODELS[lang] = model

    print("[PRELOAD] All CodeBERT models loaded and frozen successfully.")


def _get_tokenizer_and_model(language: str):
    """Retrieves or lazily initializes the tokenizer and model for a language."""
    import torch
    from transformers import AutoModelForMaskedLM, AutoTokenizer

    if language not in _TOKENIZERS or language not in _MODELS:
        model_id = MODEL_IDS.get(language)
        if not model_id:
            raise ValueError(f"Unsupported language: {language}")

        if language not in _TOKENIZERS:
            _TOKENIZERS[language] = AutoTokenizer.from_pretrained(model_id)

        if language not in _MODELS:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            try:
                model = AutoModelForMaskedLM.from_pretrained(model_id, device_map="auto")
            except Exception:
                model = AutoModelForMaskedLM.from_pretrained(model_id).to(device)
            model.eval()
            for param in model.parameters():
                param.requires_grad = False
            _MODELS[language] = model

    return _TOKENIZERS[language], _MODELS[language]


def count_tokens(code: str, language: str, *, local_files_only: bool = False) -> int:
    """Count real CodeBERT tokens; viewer may require local cache to avoid network delays."""
    if language not in MODEL_IDS:
        raise ValueError(f"Unsupported language: {language}")
    if language not in _TOKENIZERS:
        from transformers import AutoTokenizer
        _TOKENIZERS[language] = AutoTokenizer.from_pretrained(
            MODEL_IDS[language], local_files_only=local_files_only
        )
    return len(_TOKENIZERS[language].encode(code, add_special_tokens=False))


def check_context(code: str, language: str) -> int:
    """Validate a code submission against the real 30-token requirement."""
    token_count = count_tokens(code, language)
    if token_count < MIN_TOKENS:
        raise CodeTooShortError(
            f"Code is too short ({token_count} tokens). Minimum required is {MIN_TOKENS} tokens."
        )
    return token_count


def extract_features(code: str, language: str) -> np.ndarray:
    """
    Extracts a 770-dimensional feature vector from code using frozen CodeBERT:
    - 510-token chunks with [CLS] and [SEP]
    - Batched forward pass: row 0 unmasked + 4 masked rows (every 4th token masked)
    - Mean-pooled last hidden state of unmasked row (768 values)
    - Mean and std of masked-token negative log-likelihood (2 values)
    - Average across chunks weighted by chunk length
    """
    import torch
    import torch.nn.functional as F

    tokenizer, model = _get_tokenizer_and_model(language)
    device = next(model.parameters()).device

    # Tokenize without special tokens
    tokens = tokenizer.encode(code, add_special_tokens=False)
    if len(tokens) < MIN_TOKENS:
        raise CodeTooShortError(f"Code contains {len(tokens)} tokens, fewer than {MIN_TOKENS} minimum.")

    # Split into chunks of 510 tokens (max 8 chunks)
    chunk_size = 510
    chunks = [tokens[i : i + chunk_size] for i in range(0, len(tokens), chunk_size)]
    if len(chunks) > 8:
        chunks = chunks[:8]

    # Drop tiny trailing chunk if smaller than 20 tokens (unless it's the only chunk)
    if len(chunks) > 1 and len(chunks[-1]) < 20:
        chunks.pop()

    chunk_features = []
    chunk_weights = []

    mask_token_id = tokenizer.mask_token_id or 103
    cls_token_id = tokenizer.cls_token_id or 0
    sep_token_id = tokenizer.sep_token_id or 2

    with torch.no_grad():
        for chunk in chunks:
            chunk_len = len(chunk)
            chunk_weights.append(chunk_len)

            # Construct inputs: row 0 unmasked, rows 1-4 with masked offsets
            input_seq = [cls_token_id] + chunk + [sep_token_id]
            seq_len = len(input_seq)

            batch_rows = [list(input_seq) for _ in range(5)]
            masked_positions_list = []

            # Rows 1 to 4 mask every 4th token with offsets 0, 1, 2, 3
            for offset in range(4):
                row_idx = offset + 1
                masked_indices = []
                for pos in range(1, seq_len - 1):  # exclude CLS and SEP
                    if (pos - 1) % 4 == offset:
                        batch_rows[row_idx][pos] = mask_token_id
                        masked_indices.append(pos)
                masked_positions_list.append(masked_indices)

            batch_tensor = torch.tensor(batch_rows, dtype=torch.long, device=device)
            attention_mask = torch.ones_like(batch_tensor)

            outputs = model(
                input_ids=batch_tensor,
                attention_mask=attention_mask,
                output_hidden_states=True,
            )

            # 1. Mean-pooled last hidden state of unmasked row 0 (768 values)
            last_hidden = outputs.hidden_states[-1]  # [5, seq_len, 768]
            unmasked_hidden = last_hidden[0, 1 : seq_len - 1, :]  # exclude CLS/SEP
            mean_hidden = unmasked_hidden.mean(dim=0).cpu().numpy()  # shape (768,)

            # 2. Masked-token negative log-likelihood (rows 1-4)
            logits = outputs.logits  # [5, seq_len, vocab_size]
            log_probs = F.log_softmax(logits, dim=-1)

            nlls = []
            for offset in range(4):
                row_idx = offset + 1
                positions = masked_positions_list[offset]
                for pos in positions:
                    true_token = input_seq[pos]
                    token_nll = -log_probs[row_idx, pos, true_token].item()
                    nlls.append(token_nll)

            if nlls:
                nll_mean = float(np.mean(nlls))
                nll_std = float(np.std(nlls))
            else:
                nll_mean = 0.0
                nll_std = 0.0

            chunk_vec = np.concatenate([mean_hidden, np.array([nll_mean, nll_std])])
            chunk_features.append(chunk_vec)

    # Weighted average across chunks by chunk length
    weights = np.array(chunk_weights, dtype=float)
    weights /= np.sum(weights)
    final_vector = np.sum([feat * w for feat, w in zip(chunk_features, weights)], axis=0)
    return final_vector


def predict(code: str, language: str) -> float:
    """Run the trained real classifier on a 770-dimensional CodeBERT vector."""
    head = _get_trained_head(language)
    features = extract_features(code, language)
    if features.shape != (770,) or not np.all(np.isfinite(features)):
        raise ValueError("CodeBERT returned invalid or incomplete features; analysis was not scored.")
    probabilities = head.predict_proba(features.reshape(1, -1))
    ai_index = list(head.classes_).index(1)
    ai_prob = float(probabilities[0, ai_index])
    if not np.isfinite(ai_prob) or not 0.0 <= ai_prob <= 1.0:
        raise ValueError("Classifier returned an invalid probability; analysis was not scored.")
    return ai_prob


def risk_level(score: float) -> str:
    """Classifies risk level based on AI generation probability."""
    if score < RISK_LOW_MAX:
        return "Low"
    elif score < RISK_MEDIUM_MAX:
        return "Medium"
    else:
        return "High"


def analyze(code: str, filename: str) -> Dict[str, any]:
    """
    Public entry point for source code submission analysis.
    Returns: {"language": str, "ai_probability": float, "risk_level": str}
    """
    _, ext = os.path.splitext(filename.lower())
    language = EXT_TO_LANG.get(ext)
    if not language:
        raise ValueError(f"Unsupported file extension '{ext}'. Allowed: .c, .java, .py")

    # Confirm trained head availability before downloading heavyweight CodeBERT weights.
    _get_trained_head(language)

    # Verify context length
    check_context(code, language)

    # Run prediction
    score = predict(code, language)
    risk = risk_level(score)

    return {
        "language": language,
        "ai_probability": round(score, 4),
        "risk_level": risk,
    }
