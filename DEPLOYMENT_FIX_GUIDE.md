# CodeAuthentic – Safe Deployment Troubleshooting

These updates fix the React share-link format and make backend-connection failures easier to diagnose. **They do not deploy a backend, fix a missing database, change login rules, or supply trained AI model files.** No existing Supabase records need to be reset.

## 1. Confirm backend exists

The Vercel URL normally serves only the React frontend (`npm run build` -> `dist`). The FastAPI backend must also be deployed to a Python-capable host, reachable over HTTPS, using `python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT` (adjust host commands as required). The backend uses PostgreSQL via SQLAlchemy. Supabase provides the PostgreSQL database, **not** automatic hosting for this Python FastAPI service.

From a browser, open `https://YOUR-API-DOMAIN/health`. The endpoint should return JSON including `"database_connected": true`. `false` indicates a database connection problem; HTML/404/network errors indicate a backend domain/deployment problem. **Avoid adding database passwords or private keys to issue screenshots.**

> The backend imports heavy machine-learning packages and the provided ZIP does not contain the serialized trained `ml/heads/*.joblib` files. For full AI predictions, the actual models must be deployed appropriately. Do not assume a successful frontend build tests the ML inference service.

## 2. Configure both deployments

**Frontend on Vercel** (Project Settings -> Environment Variables):

- `VITE_API_BASE_URL=https://YOUR-DEPLOYED-FASTAPI-ORIGIN` (no `/auth`, no `/lobbies`, no trailing slash).
- Redeploy the frontend after changing it. Vite substitutes the variable **during build**, not at runtime.

**Backend host** (environment variables set privately, never in source code):

- `DATABASE_URL`: use the verified PostgreSQL connection URL from the Supabase dashboard (use required SSL parameters and a pooler endpoint appropriate for your host).
- `SECRET_KEY`: a strong private random secret; preserve the existing one for already-issued sessions, or intentionally sign everyone out when rotating it.
- `FRONTEND_PUBLIC_URL=https://YOUR-FRONTEND.vercel.app`: optional, recommended for any backend-generated links.
- `FRONTEND_ORIGINS=https://YOUR-FRONTEND.vercel.app`: browser CORS allowlist; comma-separate origins if needed.
- No SMTP credentials are required: instructor email confirmation is disabled in this version.

Use `.env.example` as a **placeholder-only** reference. Never upload actual Supabase passwords, JWT secrets, SMTP credentials, or a `.env` file to a public repository. Rotate any credentials previously shared in messages or screenshots.

**Do not** set `ALLOW_LEGACY_SCHEMA_MIGRATION=true` until the existing database has been backed up and the schema migration has been reviewed.

## 3. Confirm lobby links

- From the deployed React instructor dashboard, make a **new** lobby and click **Copy link**. It should copy `https://YOUR-FRONTEND.vercel.app/?lobby=<real-uuid>` rather than a localhost or backend `/lobby/` link.
- Opening a copied link on a different device or private window should show the student upload portal.
- Previously shared `/lobby/<uuid>` links can be recognized by the React app (Vercel rewrite in `vercel.json`).
- Real lobby codes are UUIDs, not the local demo codes `CARSU-1` or `ALGO-99` found in `src/utils/storage.ts`. Demo records must never be treated as database entries.
- A found-but-locked lobby should show `LOCKED`, not `Lobby not found`; expired lobby access still obeys original rules.

## 4. When errors remain

Open the browser Developer Tools -> Network (F12) and inspect these requests, with private values redacted:

| Request | Expected | What failure indicates |
|---|---|---|
| `POST /auth/login/json` | JSON with access token (on valid credentials) | 404/HTML: wrong API host; 401: bad credentials; 500: backend/DB logs |
| `POST /auth/register` | 201 JSON (no email confirmation needed) | 409: email already registered; 500: backend/DB logs |
| `POST /lobbies` | 201 JSON lobby with a UUID | 401: missing/expired token; 500: backend/DB logs |
| `GET /public/lobbies/<uuid>/status` | 200 JSON with `active` | 404 JSON: lobby absent from DB; HTML 404: wrong API host |
| `POST /lobbies/<uuid>/submit` | JSON or 202 confirmation | 4xx validation/lock; 5xx backend/analysis logs |

Do not interpret `Request failed` as a wrong password without checking the status and response. Browser CORS errors can show up as network failures even when FastAPI itself is running.

## 5. Validation sequence after deployment

1. Load `/health` from another device and verify the database is connected.
2. Create an instructor account and sign in immediately; no confirmation email is required. Existing previously-unverified accounts can also sign in with their passwords.
3. Create a real lobby and copy its link.
4. Open the student link in incognito; confirm it is active and upload a valid file.
5. Confirm submission appears for the instructor; verify AI classification separately with the trained model artifacts.

This package does **not** modify production records, turn off password authentication, bypass locks, or replace real AI predictions with demo scores. It intentionally removes instructor email confirmation. Public self-registration should be restricted to authorized faculty before a production rollout.
