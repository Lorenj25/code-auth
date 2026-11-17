# CodeAuthentic — Code Viewer, Timestamps, Status Handling & Live Updates

Updated on 16 November 2026. Source: `CodeAuthentic_Source_For_Review(1).zip`, carrying forward the earlier three-fix update.

## Improvements

1. **Inspect / View Code:** authenticated, lobby-owner-only API route returns the exact saved text; CodeBERT token counting uses the local tokenizer cache if available, so the viewer does not start a Hugging Face download. Missing token count displays as Unavailable. Missing/outdated backend returns a meaningful error rather than a vague Not Found.
2. **Philippine time:** existing database values (naive UTC) are unchanged; JSON and WebSocket timestamps now include UTC `Z`. React converts legacy timestamp strings to UTC and displays Philippine Standard Time (PHT, UTC+8). Student receipts, instructor table, modal, and CSV follow the same convention.
3. **Submission/analysis error states:** queued submissions become `pending` → `analyzing` → `done` or `failed`; missing trained models or model errors result in Failed with no fabricated probability. An unexpected critical error attempts to preserve Failed status. Missing tokenizer validation now returns HTTP 503 instead of accepting a different token count. Frontend also prevents multiple FileReader races for batch uploads and hides malformed/incomplete scores.
4. **Live dashboard:** the previously installed WebSocket subscriptions, reconnection and 10-second HTTP polling fallback are preserved. Vite's local `/ws` proxy is now enabled, and simultaneous refresh responses cannot overwrite newer data. An open Inspect modal updates its status with fresh dashboard data.
5. **Version verification:** `START_SYSTEM.bat` rejects occupied ports 8000/3000 instead of silently connecting to an older backend. `GET /health` includes `api_release: "2026-11-16-phase2"` and `code_viewer_endpoint: true`.

## Not changed

- Instructor passwords/JWT login and the intentional removal of email verification.
- Supabase / PostgreSQL schema, existing database records, model thresholds, model IDs, classifier architecture, or training pipeline.
- No synthetic AI detector, no training datasets, and no classifier weights were added.

**AI predictions will still fail until the original pretrained classifier head artifacts / correct Hugging Face AI detector are identified and installed.** This is separate from the code viewer and database-backed submission flow.

## Install safely on Windows

1. Back up the **entire currently working project folder**, particularly `.env`, model files, and database settings. Do not delete the original folder.
2. **Close both CodeAuthentic backend and frontend command windows**. Check ports 8000 and 3000 before running the launcher again; close any old server still using them.
3. Extract `CodeAuthentic_PHASE2_CHANGED_FILES_ONLY.zip` and copy **all folders/files preserving the directory tree** into the project root (the folder containing `START_SYSTEM.bat`), allowing overwrite for included files. This patch includes the previous protected API endpoint, so it applies whether you used the original extracted source or the previous three-fix package.
4. Do not replace or share `.env`. Do not move/delete model weights, dataset files, or the live database.
5. Run `START_SYSTEM.bat`; make sure **neither port-in-use message appears**. The backend and React frontend must be started together.
6. Verify `http://127.0.0.1:8000/health` contains `api_release: "2026-11-16-phase2"` and `code_viewer_endpoint: true`. At `http://127.0.0.1:8000/docs`, look for `GET /lobbies/{lobby_id}/submissions/{submission_id}/code`.
7. In the browser open `http://localhost:3000`, press `Ctrl+Shift+R`, then sign in as instructor.

If the **old FastAPI** process remains on port 8000, Inspect may still say Not Found. Updating only the frontend is not sufficient. If hosting online, redeploy **frontend and backend together**; local restarting will not update Vercel.

## Manual acceptance test (requires live local app)

1. Sign in as an existing instructor without OTP. Create a new Python lobby. Open the copied student link in private/incognito mode on a second browser or device.
2. Submit a valid `.py` code file. Check that it is saved, displays as Pending/Analyzing, then Completed with a real model score **or Failed with no percentage** when the trained classifier is absent.
3. Click **Inspect**. Verify the *exact code*, filename/language, ownership, and a time tagged PHT. The token count may say Unavailable if no local tokenizer is present; that does not block viewing code.
4. Keep the instructor dashboard open during another upload. The new row should appear automatically. To test fallback, disconnect the WebSocket connection in browser devtools; with HTTP available, the row should still appear within approximately 10 seconds.
5. Sign in as a different instructor and verify another instructor's private code endpoint returns 404; without an auth token, it must return 401.
6. Refresh and re-open the existing submission, then restart the backend and verify the persisted submission remains. Confirm current account/login remains available.
7. Check that an 04:30 UTC submission is rendered as **12:30 PM PHT** on the same date.

## Automated checks performed for this package

- Python syntax `compileall`: passed.
- Isolated SQLAlchemy/FastAPI regression tests: **8 passed**: owner-only code retrieval (using mocked auth identity), saved submission with mock successful and failing inference, WebSocket event payload transitions, timestamp normalization, missing-tokenizer 503, batch validation and existing model thresholds.
- Frontend mocked WebSocket/API checks: passed; secure WebSocket URL, token, event delivery, teardown, code fetch headers, useful 404 errors, UTC→PHT.
- TypeScript/TSX **syntax/transpilation** for all source files: passed. **A complete `npm run lint` / `npm run build` with installed React dependencies was not possible in this offline inspection environment.**
- **Not performed:** actual JWT/bcrypt registration/login end-to-end, real Supabase records, real two-device browser smoke test, full real CodeBERT inference (classifier `.joblib` files absent). Complete the manual acceptance test above on your friend's machine.

## Command-line checks

```powershell
# In project root, with project dependencies already installed
.\.venv\Scripts\python.exe -m pytest -q tests\test_review_fixes.py tests\test_phase2_regressions.py
node tests\test_websocket_client.cjs
npm run lint
npm run build
```

The WebSocket JS test uses the `typescript` package from the project's `node_modules`, installed with `npm ci` on your machine. It does not need internet when dependencies are already installed.
