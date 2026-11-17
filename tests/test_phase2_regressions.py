"""Isolated API/inference-flow regressions; no real accounts, database or AI model used."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.models import Instructor, Lobby, Submission
from backend.routes import submissions
from backend.schemas import LobbyResponse, SubmissionResponse
from backend.time_utils import utc_isoformat


@pytest.fixture
def temp_db():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    lobby_id = uuid.uuid4()
    with session_factory() as db:
        db.add(Instructor(id=901, name='Test instructor', email='test@example.org', password_hash='TEST', is_verified=True))
        db.add(Lobby(id=lobby_id, instructor_id=901, subject='Lab', title='Example',
                     language='python', max_students=35, status='ACTIVE',
                     created_at=datetime.utcnow(), expires_at=datetime.utcnow() + timedelta(hours=2)))
        db.commit()

    app = FastAPI()
    app.include_router(submissions.router)

    def db_override():
        with session_factory() as db:
            yield db
    app.dependency_overrides[get_db] = db_override
    yield app, session_factory, lobby_id
    engine.dispose()


def test_utc_serialization_keeps_existing_database_values_unchanged():
    naive = datetime(2026, 11, 16, 4, 32, 5)
    assert utc_isoformat(naive) == '2026-11-16T04:32:05Z'
    aware = datetime(2026, 11, 16, 12, 32, 5, tzinfo=timezone(timedelta(hours=8)))
    assert utc_isoformat(aware) == '2026-11-16T04:32:05Z'
    lobby = LobbyResponse(id=uuid.uuid4(), instructor_id=901, title='Lab',
                          language='python', created_at=naive,
                          expires_at=naive + timedelta(hours=2), status='ACTIVE')
    assert lobby.model_dump(mode='json')['created_at'].endswith('Z')
    sub = SubmissionResponse(id=1, lobby_id=lobby.id, student_id='221',
                             file_name='file.py', language='python', status='pending', created_at=naive)
    assert sub.model_dump(mode='json')['created_at'] == '2026-11-16T04:32:05Z'
    assert naive.tzinfo is None  # no DB value mutation


@pytest.mark.parametrize('failure', [False, True])
def test_student_upload_and_status_changes_are_persisted_and_notified(temp_db, failure):
    from backend import analysis
    from ml import predictor
    app, Session, lobby_id = temp_db
    events = []
    def broadcast(lobby, event):
        events.append((lobby, event))

    def fake_analyze(code, file_name):
        if failure:
            raise predictor.HeadNotTrainedError('Classifier head missing for testing')
        return {'ai_probability': 0.8, 'risk_level': 'High', 'language': 'python'}

    with patch('ml.predictor.check_context', return_value=50), \
         patch('ml.predictor.analyze', side_effect=fake_analyze), \
         patch.object(analysis, 'SessionLocal', Session), \
         patch.object(submissions.manager, 'broadcast_threadsafe', side_effect=broadcast), \
         TestClient(app) as client:
        response = client.post(f'/lobbies/{lobby_id}/submit',
                               data={'student_id': '221'},
                               files=[('files', ('answer.py', b'def answer():\n    return 42\n', 'text/plain'))])
        assert response.status_code == 200, response.text
        assert response.json()['status'] == 'received'
    with Session() as db:
        row = db.query(Submission).one()
        assert row.source_code == 'def answer():\n    return 42\n'
        assert row.status == ('failed' if failure else 'done')
        if failure:
            assert row.ai_probability is None
        else:
            assert row.ai_probability == pytest.approx(0.8)
        if failure:
            assert row.risk_level is None
            assert 'Classifier head missing' in row.error_message
        else:
            assert row.risk_level == 'High'
            assert row.error_message is None
    assert [event['submission']['status'] for _, event in events] == [
        'pending', 'analyzing', 'failed' if failure else 'done'
    ]
    assert all('source_code' not in event['submission'] for _, event in events)
    assert all(event['submission']['created_at'].endswith('Z') for _, event in events)


def test_missing_tokenizer_is_explicit_service_error_not_an_arbitrary_count(temp_db):
    app, Session, lobby_id = temp_db
    with patch('ml.predictor.check_context', side_effect=RuntimeError('missing HF tokenizer')), TestClient(app) as client:
        response = client.post(f'/lobbies/{lobby_id}/submit',
                               data={'student_id': '221'},
                               files=[('files', ('answer.py', b'def x(): return 43', 'text/plain'))])
    assert response.status_code == 503
    assert 'tokenizer' in response.json()['detail'].lower()
    with Session() as db:
        assert db.query(Submission).count() == 0


def test_multi_file_upload_is_all_or_nothing(temp_db):
    app, Session, lobby_id = temp_db
    with patch('ml.predictor.check_context', return_value=45), TestClient(app) as client:
        response = client.post(f'/lobbies/{lobby_id}/submit',
                               data={'student_id': '221'},
                               files=[('files', ('valid.py', b'print(1)', 'text/plain')),
                                      ('files', ('invalid.java', b'public class A{}', 'text/plain'))])
    assert response.status_code == 400
    with Session() as db:
        assert db.query(Submission).count() == 0
