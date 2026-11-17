# CodeAuthentic: instructor sign-in without email confirmation

## What changed

- Creating an instructor account immediately stores an active account in PostgreSQL (including Supabase); registration does not send email.
- After successful registration, React and the legacy HTML instructor portal sign in automatically using the entered email and password.
- Existing accounts originally created as `is_verified=false` can now sign in with their original password; **do not create duplicate accounts**.
- The "Check your inbox" and "Resend confirmation email" UI and backend routes have been removed.
- Bcrypt password hashing, JWT access tokens, authentication on instructor routes, and lobby ownership checks remain in place.

## Database and environment

- No database reset or Supabase SQL migration is needed. Leave the existing `instructors.is_verified` field and `email_verification_tokens` table as they are for compatibility. New instructor accounts set `is_verified=true`; old `false` values are simply ignored for sign-in.
- Keep `DATABASE_URL` and `SECRET_KEY` properly configured in the **backend** environment.
- `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, and `API_PUBLIC_URL` are not needed for instructor registration. They may be removed from `.env` once no other features use them.
- No change is required to the Supabase RLS rules already set up.

## How to apply

1. Back up the project before replacing the files.
2. Extract the changed-files ZIP and copy the `thesis-main` folder contents over the matching project files, preserving folder paths.
3. Restart the FastAPI backend and React Vite frontend (`START_SYSTEM.bat`). If the Vercel frontend is deployed, rebuild/redeploy it **after** updating the backend.
4. Existing account test: sign in with an account that used to show "Please confirm your email". It should now allow access with the correct password.
5. New account test: register with a new email; the system should automatically open the instructor dashboard, without sending mail.
6. Check duplicate-email registration still gives an error, and incorrect-password login still fails.
7. Create a lobby and test student entry in an incognito window. Email registration changes do not by themselves resolve backend deployment or ML model issues.

## Security tradeoff (important for a university system)

**Anyone who can access the public `/auth/register` API can currently create an instructor account.** Removing email ownership confirmation also lets people register using someone else's email address (though they cannot sign into that actual email account). This version implements the team's requested simplified registration, **not** an administrator approval mechanism. Before broad deployment for real university examinations, strongly consider an instructor invitation or administrator-provisioning system, registration code, or an approved faculty allowlist. Do not use an email-domain check alone as proof of instructor identity.

This change does not disable 2-Step Verification on the group's Google account; that is separate from CodeAuthentic.

## Validation completed in the development environment

- Python backend syntax checks and TypeScript/TSX parsing passed.
- Mocked FastAPI + SQLite tests passed for account registration, immediate login, duplicate-account rejection, invalid-password rejection, old unverified account login, and retired verification endpoints.
- Full React Vite build, real Supabase login, and Windows launcher were **not** tested in this environment and should be tested locally before live deployment.
