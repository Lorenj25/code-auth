# CodeAuthentic — Phase 3: Real CodeBERT AI-Authorship Training

## Why this update exists

The supplied Hugging Face checkpoints (`neulab/codebert-python`, `neulab/codebert-java`, `neulab/codebert-c`) are **masked-language models** trained to represent code. They are **not** trained out of the box to distinguish human-written from AI-generated programs. The old backend looked for `ml/heads/{language}.joblib`, which wasn't present. It correctly returned **FAILED** rather than a score.

Phase 3 keeps these original frozen CodeBERT checkpoints, preserves instructor logins, lobbies, Supabase/PostgreSQL tables, uploaded source code, Inspect, timestamps, and WebSocket updates. The new ML workflow can produce real **evaluated** classifier heads using published labeled data. **No model weights or dataset are included in these ZIPs.** Nothing has been trained or validated on real data yet.

## Where to obtain real labeled data

Recommended starting point (not a guarantee of accuracy):

- Ghizlane Boukili, Said El Garouani, Jamal Riffi, **“A dataset for human-written and AI-generated code source classification”**, *Data in Brief* 65 (2026) 112527. DOI: https://doi.org/10.1016/j.dib.2026.112527
- Dataset (Mendeley Data): https://data.mendeley.com/datasets/kjh95n54f8/2
- 10,000 labeled examples; Python, Java, C, C++. Importer intentionally skips C++ because CodeAuthentic only accepts `.py`, `.java`, `.c`.
- The CSV is named `HumanVsAI_CodeDataset.csv` and has `Problem_id, Sample_Code, Generated, Language, Source`. **Check the dataset publisher's license and terms** before use. The classification task only uses clearly labeled originals, not fabricated samples.

### Set up on your Windows backend/training computer

Open PowerShell inside the root `thesis-main` folder (the folder with `ml/` and `backend/`). Keep the same virtual environment you use for FastAPI.

```powershell
# If you already use a virtual environment, activate it first.
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# Download and extract Code_Dataset from the publisher, then locate its CSV.
python -m ml.import_research_dataset --csv "C:\path\to\HumanVsAI_CodeDataset.csv" --dry-run
python -m ml.import_research_dataset --csv "C:\path\to\HumanVsAI_CodeDataset.csv"

# Train and evaluate one classifier, then repeat for the other two languages.
python -m ml.train_head --language python --data dataset/python
python -m ml.train_head --language java --data dataset/java
python -m ml.train_head --language c --data dataset/c
```

The importer creates local, gitignored directories `dataset/python/human`, `dataset/python/ai`, etc. alongside a **manifest tracking each file's real label, original source, SHA-256, and programming-problem group**. It never invents AI-generated code, and it rejects conflicting authorship labels.

The trainer uses the original project's 770-feature frozen-CodeBERT extraction and a real `StandardScaler + LogisticRegression` classifier. It uses **problem-group-disjoint** train/validation/test splits (approximately 70/15/15); solutions to a shared `Problem_id` never leak between training and evaluation. It caches deterministic CodeBERT feature vectors for repeat runs; training can be **slow and memory-intensive on CPU**. Internet is needed on first use to download the pretrained CodeBERT checkpoints. A GPU, sufficient RAM, and available disk space are recommended. All dataset/code is local during training.

### Evaluate the model before turning it on

Training creates **candidate files only**:

```text
ml/candidates/python.joblib
ml/candidates/python.json     # human false-positive rate, AI precision/recall/F1, ROC-AUC, confusion matrix
ml/candidates/java.joblib
ml/candidates/java.json
ml/candidates/c.joblib
ml/candidates/c.json
```

Review the held-out report and validate the model on **separate, real student-like laboratory problems** (not used in the imported training data). Do not call raw logistic-regression output a calibrated or validated measure of cheating. Evaluate false positives on student-written code and differences between code generators, problem types, and paraphrased/hybrid work.

After a human reviewer approves a candidate, activate each language explicitly:

```powershell
python -m ml.activate_head --language python --confirm-reviewed
python -m ml.activate_head --language java --confirm-reviewed
python -m ml.activate_head --language c --confirm-reviewed
```

Activation requires a verifiable matching training report, problem-separated evaluation, **at least 20 human and 20 AI test examples**, **AI F1 ≥ 0.70**, and **human false-positive rate ≤ 0.15** in that held-out evaluation. These are minimum installation guardrails, **not proof of suitability or calibration**. Candidate files that fail the guardrails remain undeployed. Existing classifiers, if any, are backed up before replacement. Review the limitations with your thesis advisers before live examination use.

**Restart the backend**, then run:

```powershell
python -m ml.verify_pipeline --status
python -m ml.verify_pipeline --language python --file "C:\path\to\new_test_file.py"
```

If only Python is active, the readiness output will show `ready_languages: ["python"]`; that is acceptable during staged rollout. The general `ready_for_inference_attempt` property means **all three** languages are available. Java and C must be trained separately before their predictions work.

In the app, upload a new sample to an instructor-owned lobby, open Inspect and review the result. The student's source file remains viewable even if analysis fails. **Never treat an AI score as proof of misconduct**; it is only a potentially fallible review aid.

## What changed / what did not

- **Updated:** labeled dataset importer, group-aware training and honest test metrics, staged candidate approval, checksum/evaluation checks before loading local `.joblib`, per-language readiness reports, non-fabricated UI text, backend-only CodeBERT token counting, a removed hardcoded Hugging Face token fallback, and an updated Datasets help modal.
- **Unchanged:** instructor login and registration (no email OTP), database schema and records, existing protected code-view endpoint, lobby creation and upload, WS/live updates, CodeBERT feature extraction (770D), and original Low/Medium/High threshold values.
- **Not included:** real research dataset, downloaded CodeBERT weights, trained classifiers, production deployment, new student submissions, or real academic accuracy claims.

## Safe installation

1. Back up the entire working project, including `.env`, `dataset/`, `ml/heads/`, and the database backups. **Never delete any existing trained models.**
2. Stop both frontend and FastAPI processes.
3. Extract `CodeAuthentic_PHASE3_CHANGED_FILES_ONLY.zip` into the project root and replace matching files while preserving relative paths. The package also includes Phase 2 patches if those were missed.
4. Restart with `START_SYSTEM.bat`, and verify `http://127.0.0.1:8000/health` reports `api_release: "2026-11-16-phase3"`. Then validate login, code-viewing, timestamps and submissions.
5. Separately import the external labeled dataset and train/review/activate models (above). Do this only on a trusted backend/training machine, not in a serverless frontend deployment.

**Security note:** `joblib` uses Python pickle semantics: loading a malicious file can execute arbitrary code. Only activate/load models trained locally by someone you trust. Artifacts and the dataset are gitignored; copy evaluated artifacts to the real backend through a trusted deployment process.

## Running regression tests

```powershell
$env:DATABASE_URL = "sqlite://"
python -m pytest -q tests/test_model_training_workflow.py tests/test_review_fixes.py tests/test_phase2_regressions.py
Remove-Item Env:DATABASE_URL
```

These tests use synthetic **test fixtures only**, not actual training data. Do not confuse passed integration tests with actual AI detection quality.
