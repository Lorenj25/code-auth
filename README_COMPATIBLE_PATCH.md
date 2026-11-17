# CodeAuthentic: Compatibility-safe Python test mode

This package is a revised integration installer after the original ZIP-based hash check stopped because `ml/predictor.py` had changed on your machine.

The installer **does not copy an older `ml/predictor.py` over your current file**. It edits only known, strictly matched statements in your existing predictor. If those statements also changed, it refuses to install rather than risking your work. It does not edit backend routes, Java/C classifiers, datasets, database, `.env`, or the virtual environment. The original frontend improvements are optional: they are installed **only if both current frontend source files exactly match the previously reviewed versions**; otherwise both frontend files are left untouched.

## Steps

1. Let the current Java training finish before installing into that project, or use a separate copy of the thesis project. Do not interrupt the training window.
2. Extract the ZIP to a **separate folder**.
3. From PowerShell in the extracted patch folder, run:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\APPLY_SAFE_PYTHON_MODE.ps1 -ProjectRoot "C:\Users\REO JOHN\Downloads\thesis-main\thesis-main"
   ```

4. The script creates a `_python_test_backup_*` folder with copies of any original files it modifies. On a successful install, close any previous local FastAPI/React server windows and launch `START_PYTHON_TEST_MODE.bat` **inside the thesis project directory**.
5. Test by creating a Python lobby, joining as a student, and uploading a `.py` source file of at least 30 CodeBERT tokens. The backend will use the verified Python candidate for local tests only. Java and C remain unchanged. The existing instructor UI will display AI probability and risk results. If your frontend files match the reviewed snapshot, the installer also adds the experimental readiness badge; otherwise it preserves your newer frontend unchanged and skips the badge.
6. Close test-mode server windows and use the normal `START_SYSTEM.bat` to disable experimental inference.

The candidate's SHA-256 and report are checked before installation, and the predictor retains its checksum and held-out evaluation validation before loading the classifier. Treat all outputs as experimental statistics, not proof of AI use. The system requires the original CodeBERT model weights for inference.

**If it reports `STOPPED SAFELY` again:** this means a relevant part of `ml/predictor.py` changed, not merely comments or unrelated code. Do not remove checks. Share your current `ml/predictor.py` so the update can be tailored precisely. No project files are changed when preflight fails.
