# Safe Fix v1 – November 13, 2026

## Changes made (source only)

- `src/utils/api.ts`: instructor Copy link now resolves to the same React public website in the browser (`/?lobby=<UUID>`), regardless of a wrong backend-generated link. Better network/CORS/HTML-vs-JSON/HTTP diagnostics for sign-in, creation and public lobby lookups.
- `src/App.tsx`: recognizes both `?lobby=<UUID>` and the legacy `/lobby/<UUID>` URL format.
- `src/components/StudentDashboard.tsx`: displays the actual API/backend error instead of labeling every failure as a nonexistent lobby.
- `backend/routes/lobbies.py`: optionally uses `FRONTEND_PUBLIC_URL` for backend-generated React links; preserves old FastAPI HTML links when not configured.
- `backend/main.py`: optional `FRONTEND_ORIGINS` CORS configuration; wildcard origin fallback no longer incorrectly enables cookie credentials.
- `vercel.json`: allows old `/lobby/<UUID>` deep links to load the React app.
- `.env.example`, `DEPLOYMENT_FIX_GUIDE.md`, `README.md`: documented required frontend and backend host setup, Supabase connection, SMTP verification and tests.

## Explicitly not changed

- No database tables, migrations, production accounts, passwords, or student records were edited.
- No authentication bypass, lock bypass, demo substitutions or AI prediction scoring changes.
- No interface redesign; sample code snippets remain samples, not real database lobbies.

## Validation

- Python source files compile (syntax check).
- TypeScript syntax transpilation succeeds for all five inspected UI/API files.
- Focused mocked frontend tests passed: URL generation, network error, HTML 404, JSON lobby 404, HTML 200, and valid JSON login responses.
- Focused backend URL tests passed for `FRONTEND_PUBLIC_URL` and legacy fallback.
- **Full Vite build and live end-to-end test not performed**: npm dependencies were unavailable in offline cache and the deployed backend's URL/configuration are still unknown. The official source of truth will be a rebuild and live instructor/student test.

## Next steps

Read `DEPLOYMENT_FIX_GUIDE.md` and get the friend's deployed FastAPI origin. Rebuild/redeploy the frontend after configuring `VITE_API_BASE_URL`, then retest login and student uploads. Back up Supabase and do not run migrations without explicit approval.

## Update: Direct instructor sign-in (November 16, 2026)

- Removed mandatory instructor email verification and resend/confirm UI and API routes.
- Register now commits an active instructor account without SMTP; the React and legacy HTML portals automatically sign in after registration.
- Previously unverified accounts can sign in using their existing password (no database reset).
- Kept the `is_verified` column and old verification token table for backward-compatible Supabase schemas; unused email service code remains untouched and is not called.
- Updated `.env.example`, README, and deployment guidance.
- **Security warning:** Email ownership is not validated and the public registration endpoint remains open. Consider administrator approval or invitation-based signup before real faculty use.
