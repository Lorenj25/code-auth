# CodeAuthentic — Latency follow-up (November 16, 2026)

This update is based on the **CodeAuthentic_PERFORMANCE_FULL_UPDATED_SOURCE.zip** that was already installed previously. It is a follow-up patch, **not** a replacement database or a new AI training release.

## Why the dashboard remains slow

Your measured timings were around **230–240 ms per `SELECT 1` on a reused PostgreSQL connection**, and a first query took around **543 ms**. Earlier server logs showed dashboard requests taking approximately 1.1–2.2 seconds. This is significant remote database/network latency, not just a React rendering problem. Reducing database round trips helps, but cannot make a 230 ms network round trip instantaneous.

## Files and changes

- `backend/routes/dashboard.py`: combines lobby metadata and submission metadata in **one SQL SELECT** using an outer join; it preserves empty lobbies, does not duplicate lobbies with multiple submissions, checks instructor ownership, and never fetches source-code blobs. Previously it needed two data SELECTs, in addition to authentication.
- `backend/database.py`: keeps committed ORM attributes instead of reloading them (`expire_on_commit=False`); reuses recent connections (`pool_use_lifo=True`, `pool_recycle=900`); keeps the safe default of SQLAlchemy `pool_pre_ping=True`, now configurable with `DB_POOL_PRE_PING`.
- `backend/routes/lobbies.py`: removes three redundant `db.refresh()` requests after already-committed Create / Lock / Unlock operations.
- `src/utils/api.ts`: stops full dashboard refreshes on each *initial* WebSocket connection. After a socket reconnects, it still refreshes to recover missed events. Submission events still refresh immediately, and polling fallback still works. Sends JWT in a WebSocket subprotocol instead of a URL query parameter.
- `backend/main.py` and `backend/ws.py`: accept the `codeauthentic` WebSocket subprotocol and authorize from the supplied protocol token. Existing query-token clients are accepted for backward compatibility; new client URLs no longer contain the token. `/health` reports `2026-11-16-latency`.
- `tests/`: updated regression checks including owner separation, multiple submissions per lobby, empty lobby retention, code privacy, no token in WS URLs, avoidance of redundant socket-opening refreshes, and no post-commit reload queries for lobby create/lock/unlock.

No database schema migrations. No changes to password hashing, removed email verification, classifier training, `.joblib` files, dataset, or stored submissions.

## Installation: only AFTER ongoing Python training has finished or been safely interrupted

1. **Back up** the working `thesis-main` folder; keep `.env`, `dataset/`, `.feature_cache/`, and `ml/heads/` intact.
2. Close existing React/Vite and FastAPI windows, checking no old process remains on ports **3000** and **8000**.
3. Extract `CodeAuthentic_LATENCY_CHANGED_FILES_ONLY.zip`. Copy its contents into the root `thesis-main` folder and **replace matching paths**. Preserve folder names.
4. Restart with your existing `START_SYSTEM.bat`.
5. Open `http://127.0.0.1:8000/health` and confirm `api_release` is `2026-11-16-latency`.
6. Sign in. Select the lobby containing your two known submissions. Verify both records appear, Inspect still works, and create/lock/unlock work on a disposable lobby. Confirm server logs no longer show `?token=...` on **new** WebSocket connections.
7. Compare `GET /instructor/dashboard` time (Edge/Chrome DevTools Network panel) with the prior approximately 1.1–2.2 seconds, ideally with the AI training process not consuming the same CPU. No exact speedup is guaranteed.

### Optional database pool check (advanced)

`pool_pre_ping=True` adds a lightweight database round trip **on each pooled checkout** to make failed/stale connections safer. On your network each round trip costs roughly 230 ms. If you want to test the trade-off, in the backend `.env` set:

```dotenv
DB_POOL_PRE_PING=false
```

Restart FastAPI and test several lobby interactions *and* an idle/reconnect scenario. **This option can expose occasional stale-connection errors**, especially when a cloud database or connection pooler closes idle connections. If you encounter an intermittent 500/database error, revert to `DB_POOL_PRE_PING=true` or delete the setting. Leave it at its safe default if in doubt. This setting does not change or delete database records.

### Remaining long-term optimization

The largest remaining latency comes from the location/network path between FastAPI and PostgreSQL. Deploying FastAPI in a region close to the PostgreSQL instance can save network time across **every** request. Verify your database's actual host/region first. Changing providers, database hostnames, or credentials without a backup and migration plan is **not** part of this patch.

### Test verification in the isolated development environment

- 21 Python regression tests passed using an isolated in-memory SQLite database.
- 2 Node/TypeScript-transpiled API/WebSocket integration checks passed.
- Python source syntax compiled successfully.
- A full production Vite build, real PostgreSQL timings, and a live browser end-to-end run were **not** performed in this container. No real database or training model was accessed.
