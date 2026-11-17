# CodeAuthentic — Experimental Python CodeBERT integration

**Status:** Python classifier is trained and evaluated; local experimental inference is available via opt-in. Java and C remain unchanged and are *not* trained/activated by this patch. This is not a production deployment or a claim that AI authorship can be reliably determined.

## What's changed

- `ml/predictor.py` accepts `CODEAUTHENTIC_PYTHON_TEST_MODE=1`. Only Python then uses the verified `ml/candidates/python.joblib` + `python.json`; otherwise all languages continue to use `ml/heads`. The unchanged SHA-256/evaluation checks are applied *before* loading the pickle. No fake scores or fallback labels are generated.
- `/ml/status` (instructor-only, already present) includes candidate vs. active source and experimental flags.
- Instructor dashboard displays Python / Java / C availability; it labels the Python test mode and warns when the selected language does not have a classifier. **Existing lobby creation, uploads, source viewer, and database models are unchanged**.
- `START_PYTHON_TEST_MODE.bat` opts into the candidate for this local launch only, then calls your original `START_SYSTEM.bat`. Existing launcher remains unchanged.
- `tests/test_python_test_mode.py` checks opt-in isolation, hash validation and fail-closed behavior.

## Install without losing data

1. **Back up your thesis project first.** Keep your existing `.env`, database, dataset, `.venv`, node_modules, all in-progress Java training output and `ml/heads` untouched.
2. **Do not interrupt Java training.** If it is still running, keep working from this separate review copy; apply the patch to the actual running project **after Java finishes**. No current training scripts or datasets are supplied or overwritten here.
3. Extract the ZIP to **a separate folder**, not directly over your running project. The patch includes `APPLY_PYTHON_TEST_PATCH.ps1`, which checks that the three source files match the uploaded review ZIP and makes timestamped backups before changing them. Run PowerShell from the extracted patch folder:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\APPLY_PYTHON_TEST_PATCH.ps1 -ProjectRoot "C:\Users\REO JOHN\Downloads\thesis-main\thesis-main"
   ```
   If the script reports **STOPPED SAFELY**, don't force the overwrite; your local project differs from the ZIP we inspected.
4. Confirm `ml/candidates/python.joblib` and `python.json` are present. They are bundled in the patch for convenience and are **not** copied to `ml/heads`. Original changed source files are saved in a dated `_python_test_patch_backup_*` folder for easy recovery.
5. Double-click `START_PYTHON_TEST_MODE.bat` **inside the project root** to launch the local experimental system. It inherits your existing `.env` / database configuration and opens the React UI on localhost:3000. **Close any pre-existing backend running on port 8000 first**; do not run both launchers simultaneously.
6. Sign in as instructor. The dashboard should show `Python: Experimental testing · Java: Not ready · C: Not ready` (once `/ml/status` is reachable). Create a **new Python lobby for testing**, upload a `.py` file with >=30 CodeBERT tokens, and wait for `done` to appear. Review the result in the instructor submission view. No score is displayed if inference fails.
7. In a separate PowerShell terminal, to verify the model files without downloading CodeBERT weights:
   ```powershell
   cd "C:\Users\REO JOHN\Downloads\thesis-main\thesis-main"
   .\.venv\Scripts\Activate.ps1
   $env:CODEAUTHENTIC_PYTHON_TEST_MODE = '1'
   python -m ml.verify_pipeline --language python
   ```
   For an actual end-to-end test after the model weights are cached, run:
   ```powershell
   python -m ml.verify_pipeline --language python --file .\human_test.py
   ```
8. To **turn the candidate off**, close the locally launched FastAPI/React windows and start again using the original `START_SYSTEM.bat`. Do not set `CODEAUTHENTIC_PYTHON_TEST_MODE` in the production environment.

## Safety and limitations

- All model outputs are statistical *estimates*, **never proof that a student used AI**. The earlier independent AI-written test snippets scored 44.16% and 11.49%; don't treat the held-out dataset accuracy as classroom accuracy. Benchmark on genuinely independently sourced, labeled human and AI code before promotion.
- A successful `/ml/status` proves report/artifact readiness, not runtime availability of the pretrained model weights. Your FastAPI host still needs PyTorch, Transformers and access to `neulab/codebert-python` weights. Loading can take time; inference may be slow on CPU.
- The existing FastAPI `BackgroundTasks` pipeline is best suited to a persistent local server/worker. Serverless deployments may terminate long-running jobs. **This patch does not deploy anything to Vercel** or change database schema or credentials.
- Keep the candidate files private and from a trusted source only; `.joblib` is pickle-based and unsafe to load from untrusted origins. Make sure scikit-learn stays compatible with the version used to train the classifier.
- The existing feature extractor truncates after 8 chunks (~4,080 tokens). Very long files may be only partially analyzed; further hardening can be done separately.

## Smoke checks

```powershell
python -m compileall -q backend ml
python -m unittest discover -s tests -p "test_python_test_mode.py" -v
npm run lint
npm run build
```

Tests do not replace running an end-to-end student upload and instructor review on your own machine. To promote into live `ml/heads` later, first complete independent validation and use the project's deliberate `ml.activate_head` process rather than this local candidate flag.
