# CodeAuthentic — Performance Optimization Update

This patch is based on the **Phase 3 full updated source** and does **not** change the CodeBERT pipeline, pretrained models, datasets, database structure, passwords, or email verification policy. The full-source ZIP also includes the separate Windows dataset-import checksum fix.

## What changed

- **One dashboard request:** `GET /instructor/dashboard` now returns owned lobby details and only submission *metadata* in one HTTP request. It performs two database SELECTs under normal conditions and does not load or include `source_code`. The private, owner-checked Inspect endpoint remains unchanged.
- **Faster Create, Lock/Unlock, Delete:** The frontend uses successful server responses to update just the affected lobby and related UI state. These actions no longer wait for a complete dashboard reload. A failed request does not display a successful change.
- **Fewer refresh collisions:** Concurrent refreshes are deduplicated. One follow-up refresh runs if another event arrives mid-request. The dashboard polls every 10 seconds while disconnected from WebSockets; while connected, it keeps a 60-second safety-net poll. Real-time submission events still refresh it.
- **Less database work:** Expired lobbies are updated in one batch; the new summary endpoint updates only when an actual expired lobby is found. The login lookup tries the indexed normalized email first, retaining a compatibility fallback for older mixed-case records. The bcrypt password check is unchanged.
- **Visible delays/errors:** API responses have `Server-Timing` and `X-Process-Time-Ms` headers. The FastAPI console logs `[PERF]` for requests taking 750 ms or more. Slow sign-ins separately log DB lookup and bcrypt duration, **never the email/password/token**. Requests have a bounded wait (45 seconds; 120 for uploads); a timed-out mutation may still have committed, so refresh before retrying.
- **Prevent double-clicks:** Lock/Unlock and Delete controls disable during each other's requests, with a visible `Updating...` state for lock/unlock.

## Safest installation on Windows

1. **If CodeBERT is still extracting/training in this project folder, let that training finish first.** Do not replace files or restart the server during training.
2. Make a full backup copy of `C:\Users\REO JOHN\Downloads\thesis-main\thesis-main` and preserve the existing `.env`, `dataset/`, `ml/candidates/`, `ml/heads/*.joblib`, and database.
3. Close CodeAuthentic's **frontend and FastAPI** terminal windows, making sure there is no old process on port 8000.
4. Extract `CodeAuthentic_PERFORMANCE_CHANGED_FILES_ONLY.zip`. Copy its contents into the project root, retaining paths (`src/...`, `backend/...`, `vite.config.ts`) and replace matching files. Do **not** copy just the loose filenames into the project root. The **new** `backend/routes/dashboard.py` is required.
5. Restart `START_SYSTEM.bat` (your existing launcher is preserved).
6. Open `http://127.0.0.1:8000/health`. Expected indicators: `api_release: "2026-11-16-performance"`, `dashboard_summary_endpoint: true`. Open `http://127.0.0.1:8000/docs` to confirm `GET /instructor/dashboard` appears. This route requires an instructor bearer token; direct browser visits without a token should return **401**, not public data.
7. Hard-refresh the frontend (Ctrl+Shift+R). If deployed, update the **backend and frontend together**; a new frontend with an old backend will show a version mismatch message.

**Prefer changed-files-only** if the original project is already working. Full-source ZIP is a separate reference copy and does not include private `.env`, local datasets, or trained model files; **do not replace the entire working project with it** without copying those private resources and backups.

## Manual verification checklist

- Sign in as instructor. Verify the dashboard loads. Open DevTools → Network → Fetch/XHR: the frontend should request `GET /instructor/dashboard` rather than GET `/lobbies` plus every lobby's detail.
- Create a disposable lobby. Its tile should appear after the POST succeeds; there should be no extra full dashboard reload *on the button's completion path*.
- Lock and unlock it. Double-clicking should not submit two changes. Expired lobbies must not unlock.
- Upload a valid student file in a separate browser. It should appear via WebSocket notification or polling fallback; source code should **not** appear inside the dashboard API response. Inspect should fetch the code only for the owning instructor.
- Delete **only the disposable lobby**. Verify it disappears and its submissions aren't in the dashboard. Do not delete real examination records.
- Test with WebSockets disconnected and verify the 10-second fallback. Test WebSockets healthy and verify regular events update the dashboard.
- Review timings: Network → select request → Timing; compare the total time to the `Server-Timing` response header, and check FastAPI logs for `[PERF] login database_ms=... bcrypt_ms=...`. High backend time means bottlenecks remain in server/DB/CPU; high network time with low backend time points to connection/proxy latency.
- If you see `request timed out`, **check the dashboard or backend state before retrying writes**, since the action could have completed on the server.

## Verification in the isolated review environment

- **20 Python tests passed**: previous code-viewer ownership and upload-status tests, training safeguards, new owned-dashboard projection and expiration tests, and login fast-path/legacy/password-check tests. Auth/bcrypt is stubbed in the last test; production sign-in must be tested on the actual laptop.
- **2 frontend Node integration scripts passed**: date/time, WebSocket cleanup, code viewer, one-request dashboard, lock response and connection state.
- Modified TypeScript/TSX files passed transpilation/syntax checks. **A full dependency-based React build has not been verified here** because project node dependencies were unavailable.
- No live Supabase/PostgreSQL performance benchmark, full browser end-to-end run, or actual AI model run was performed. Real-world speed improvement is expected based on removing redundant work, but exact latency must be measured on your computer.

## Changed implementation files

`backend/main.py`, `backend/schemas.py`, `backend/routes/auth.py`, `backend/routes/lobbies.py`, **new** `backend/routes/dashboard.py`, `src/App.tsx`, `src/utils/api.ts`, `src/components/InstructorDashboard.tsx`, and `vite.config.ts`.

The training scripts in `ml/` are **not changed** by this performance patch.
