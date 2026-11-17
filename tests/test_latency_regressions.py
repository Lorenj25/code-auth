"""Post-commit request minimization and owner-only lobby mutation smoke tests."""
from __future__ import annotations

import importlib
import sys
import types
import uuid
from unittest.mock import patch

from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.models import Instructor


def test_lobby_create_and_lock_do_not_reselect_after_commit():
    fake_security = types.ModuleType("backend.security")

    def get_current_instructor(x_test_instructor: int | None = Header(default=None)):
        if x_test_instructor is None:
            raise HTTPException(status_code=401, detail="Sign in")
        return types.SimpleNamespace(id=x_test_instructor)

    fake_security.get_current_instructor = get_current_instructor
    with patch.dict(sys.modules, {"backend.security": fake_security}):
        lobbies = importlib.import_module("backend.routes.lobbies")

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as db:
        db.add(Instructor(id=501, name="Owner", email="owner@test.invalid", password_hash="x"))
        db.commit()

    app = FastAPI()
    app.include_router(lobbies.router)

    def override_db():
        with Session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    recorded = []

    def log_sql(conn, cursor, statement, parameters, context, executemany):
        recorded.append(statement.lower().strip())

    event.listen(engine, "before_cursor_execute", log_sql)
    headers = {"x-test-instructor": "501"}
    with TestClient(app) as client:
        response = client.post(
            "/lobbies",
            json={"subject":"ITE", "title":"Final", "language":"python", "max_students": 35, "duration_minutes": 60},
            headers=headers,
        )
        assert response.status_code == 201, response.text
        lobby_id = response.json()["id"]
        assert str(uuid.UUID(lobby_id)) == lobby_id
        assert not any(sql.startswith("select") for sql in recorded), recorded
        recorded.clear()
        response = client.post(f"/lobbies/{lobby_id}/lock", headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "LOCKED"
        assert len([sql for sql in recorded if sql.startswith("select")]) == 1, recorded
        recorded.clear()
        response = client.post(f"/lobbies/{lobby_id}/unlock", headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "ACTIVE"
        assert len([sql for sql in recorded if sql.startswith("select")]) == 1, recorded
        assert client.post(f"/lobbies/{lobby_id}/lock", headers={"x-test-instructor":"502"}).status_code == 403
    event.remove(engine, "before_cursor_execute", log_sql)
    engine.dispose()
