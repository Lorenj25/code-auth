"""Isolated performance and access-control tests (no production DB or ML downloads)."""
from __future__ import annotations

import importlib
import os
os.environ["DATABASE_URL"] = "sqlite://"  # isolated test configuration
import sys
import types
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.models import Instructor, Lobby, Submission


def test_single_dashboard_request_is_owned_and_does_not_load_code():
    fake_security = types.ModuleType('backend.security')

    def get_current_instructor(x_test_instructor: int | None = Header(default=None)):
        if x_test_instructor is None:
            raise HTTPException(status_code=401, detail='Sign in')
        return types.SimpleNamespace(id=x_test_instructor)

    fake_security.get_current_instructor = get_current_instructor
    with patch.dict(sys.modules, {'backend.security': fake_security}):
        dashboard = importlib.import_module('backend.routes.dashboard')

    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    owner_id, stranger_id = 201, 202
    owned, stranger = uuid.uuid4(), uuid.uuid4()
    expired = uuid.uuid4()
    empty = uuid.uuid4()
    now = datetime.utcnow()
    with Session() as db:
        db.add_all([
            Instructor(id=owner_id, name='Owner', email='perf-owner@test.invalid', password_hash='x'),
            Instructor(id=stranger_id, name='Other', email='perf-other@test.invalid', password_hash='x'),
            Lobby(id=owned, instructor_id=owner_id, subject='ITE', title='Final', language='python', max_students=35, created_at=now, expires_at=now + timedelta(hours=2)),
            Lobby(id=expired, instructor_id=owner_id, subject='IT', title='Expired', language='java', max_students=35, created_at=now-timedelta(days=2), expires_at=now-timedelta(days=1)),
            Lobby(id=empty, instructor_id=owner_id, subject='IT', title='Empty', language='python', max_students=35, created_at=now-timedelta(hours=1), expires_at=now+timedelta(days=1)),
            Lobby(id=stranger, instructor_id=stranger_id, subject='Private', title='Hidden', language='c', max_students=35, created_at=now, expires_at=now+timedelta(hours=2)),
        ])
        db.commit()
        db.add_all([
            Submission(lobby_id=owned, student_id='s1', file_name='first.py', language='python', source_code='SENSITIVE CODE 42', status='pending'),
            Submission(lobby_id=owned, student_id='s1', file_name='second.py', language='python', source_code='SENSITIVE CODE 12', status='failed'),
            Submission(lobby_id=expired, student_id='s2', file_name='two.java', language='java', source_code='SENSITIVE CODE 23', status='failed'),
            Submission(lobby_id=stranger, student_id='s3', file_name='private.c', language='c', source_code='VERY PRIVATE', status='done'),
        ])
        db.commit()

    app = FastAPI()
    app.include_router(dashboard.router)
    def override_db():
        with Session() as db:
            yield db
    app.dependency_overrides[get_db] = override_db

    statements = []
    def track_sql(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement.lower())

    event.listen(engine, 'before_cursor_execute', track_sql)
    with TestClient(app) as client:
        assert client.get('/instructor/dashboard').status_code == 401
        response = client.get('/instructor/dashboard', headers={'X-Test-Instructor': str(owner_id)})
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data['lobbies']) == 3, 'Outer join must preserve empty lobbies without duplicating nonempty ones'
        assert len(data['submissions']) == 3
        assert {row['file_name'] for row in data['submissions']} == {'first.py', 'second.py', 'two.java'}
        assert 'SENSITIVE CODE' not in response.text
        assert 'source_code' not in response.text
        assert 'VERY PRIVATE' not in response.text
        assert data['lobbies'][0]['shareable_url']
        assert next(row for row in data['lobbies'] if row['id'] == str(expired))['status'] == 'LOCKED'
        # One joined SELECT, one bulk-expiration update; no source code loaded.
        assert len([sql for sql in statements if sql.lstrip().startswith('select')]) == 1
        assert len([sql for sql in statements if sql.lstrip().startswith('update')]) == 1

        statements.clear()
        response = client.get('/instructor/dashboard', headers={'X-Test-Instructor': str(stranger_id)})
        assert response.status_code == 200
        assert [row['file_name'] for row in response.json()['submissions']] == ['private.c']
        assert len([sql for sql in statements if sql.lstrip().startswith('update')]) == 0

    event.remove(engine, 'before_cursor_execute', track_sql)
    engine.dispose()


def test_login_lookup_keeps_old_account_compatibility_and_password_check():
    """Stub bcrypt/JWT only; verify the route's DB and authentication branches."""
    fake = types.ModuleType('backend.security')
    fake.ACCESS_TOKEN_EXPIRE_MINUTES = 480
    fake.create_access_token = lambda data, expires_delta: 'test-token'
    fake.get_password_hash = lambda password: 'hashed-'+password
    fake.verify_password = lambda supplied, stored: 'hashed-'+supplied == stored
    with patch.dict(sys.modules, {'backend.security': fake}):
        auth = importlib.import_module('backend.routes.auth')

    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        db.add_all([
            Instructor(id=301, name='Normalized', email='ready@example.org', password_hash='hashed-pass'),
            Instructor(id=302, name='Legacy', email='OldCase@Example.org', password_hash='hashed-legacy'),
        ])
        db.commit()
        assert auth._authenticate('ready@example.org', 'pass', db)['access_token'] == 'test-token'
        assert auth._authenticate('oldcase@example.org', 'legacy', db)['access_token'] == 'test-token'
        from fastapi import HTTPException
        try:
            auth._authenticate('ready@example.org', 'wrong', db)
        except HTTPException as exc:
            assert exc.status_code == 401
        else:
            assert False, 'Incorrect password should never be accepted'
    engine.dispose()
