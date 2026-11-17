"""Focused integration regressions for the three CodeAuthentic review fixes.

Use an isolated SQLite database, not a real account or Supabase database.
Mock only token verification and CodeBERT tokenization to test ownership without
requiring large pretrained model downloads.
"""
from __future__ import annotations

import os
import sys
import types
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi import FastAPI, HTTPException, Header
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite://"  # test-only, prevents touching PostgreSQL

from backend.database import Base, get_db
from backend.models import Instructor, Lobby, Submission
from ml.predictor import HeadNotTrainedError, model_readiness, predict, risk_level


def test_protected_code_viewer_does_not_leak_to_other_instructors():
    # Load only the lobby router; replace JWT dependency at test import time
    # so we can exercise ownership against a temporary database.
    fake_security = types.ModuleType("backend.security")

    def get_current_instructor(x_test_instructor: int | None = Header(default=None)):
        if x_test_instructor is None:
            raise HTTPException(status_code=401, detail="Missing instructor identity")
        return types.SimpleNamespace(id=x_test_instructor)

    fake_security.get_current_instructor = get_current_instructor
    with patch.dict(sys.modules, {"backend.security": fake_security}):
        from importlib import import_module
        lobbies = import_module("backend.routes.lobbies")

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    owner_id, other_id = 11, 22
    own_lobby, other_lobby = uuid.uuid4(), uuid.uuid4()
    code = "def great_answer():\n    return 42\n"
    with Session() as db:
        db.add_all([
            Instructor(id=owner_id, email="one@example.com", name="One", password_hash="x", is_verified=True),
            Instructor(id=other_id, email="two@example.com", name="Two", password_hash="x", is_verified=True),
            Lobby(id=own_lobby, instructor_id=owner_id, subject="A", title="A",
                  language="python", max_students=10, expires_at=datetime.utcnow() + timedelta(hours=1)),
            Lobby(id=other_lobby, instructor_id=other_id, subject="B", title="B",
                  language="python", max_students=10, expires_at=datetime.utcnow() + timedelta(hours=1)),
        ])
        db.commit()
        db.add(Submission(lobby_id=own_lobby, student_id="student-1", file_name="good.py",
                          language="python", source_code=code, status="pending"))
        db.commit()
        submission_id = db.query(Submission.id).scalar()

    app = FastAPI()
    app.include_router(lobbies.router)

    def override_db():
        with Session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    # Fake only the tokenizer so this tests code access rather than HF download.
    with patch("ml.predictor.count_tokens", return_value=43), TestClient(app) as client:
        url = f"/lobbies/{own_lobby}/submissions/{submission_id}/code"
        assert client.get(url).status_code == 401
        assert client.get(url, headers={"X-Test-Instructor": str(other_id)}).status_code == 404
        result = client.get(url, headers={"X-Test-Instructor": str(owner_id)})
        assert result.status_code == 200
        assert result.json()["source_code"] == code
        assert result.json()["token_count"] == 43
        assert client.get(f"/lobbies/{other_lobby}/submissions/{submission_id}/code",
                          headers={"X-Test-Instructor": str(other_id)}).status_code == 404

        # Dashboard summaries never return source code.
        detail = client.get(f"/lobbies/{own_lobby}", headers={"X-Test-Instructor": str(owner_id)})
        assert detail.status_code == 200
        assert "source_code" not in detail.text
        assert "def great_answer" not in detail.text

    engine.dispose()


def test_missing_models_fail_closed_without_fake_results():
    readiness = model_readiness()
    assert set(readiness["languages"]) == {"python", "java", "c"}
    assert set(readiness["dependencies"]) == {"torch", "numpy", "transformers", "joblib", "sklearn"}
    with patch("ml.predictor.HEADS_DIR") as heads_dir:
        head = heads_dir.__truediv__.return_value
        head.is_file.return_value = False
        with pytest.raises(HeadNotTrainedError):
            predict("print('hello')", "python")


def test_risk_thresholds_preserved():
    assert risk_level(0.0) == "Low"
    assert risk_level(0.3999) == "Low"
    assert risk_level(0.4) == "Medium"
    assert risk_level(0.69999) == "Medium"
    assert risk_level(0.7) == "High"
