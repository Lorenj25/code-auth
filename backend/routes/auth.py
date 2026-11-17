"""Instructor registration and password-based JWT sign-in.

Email confirmation is intentionally not required. Instructor accounts are still
protected by password hashing and signed access tokens.
"""

from __future__ import annotations

from datetime import timedelta
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Instructor
from backend.schemas import InstructorCreate, InstructorLogin, RegistrationMessage, Token
from backend.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_password_hash,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
perf_logger = logging.getLogger("uvicorn.error")


@router.post(
    "/register",
    response_model=RegistrationMessage,
    status_code=status.HTTP_201_CREATED,
)
def register_instructor(
    payload: InstructorCreate,
    db: Session = Depends(get_db),
) -> RegistrationMessage:
    """Create an instructor account that is ready to sign in immediately."""
    email = str(payload.email).lower().strip()
    existing = db.query(Instructor).filter(func.lower(Instructor.email) == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    new_instructor = Instructor(
        name=payload.name.strip(),
        email=email,
        password_hash=get_password_hash(payload.password),
        # Retain this legacy column for compatibility with existing Supabase tables.
        is_verified=True,
    )
    db.add(new_instructor)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        ) from exc

    return RegistrationMessage(message="Account created. You can sign in now.")


def _authenticate(email: str, password: str, db: Session) -> dict:
    started = time.perf_counter()
    # Fast path uses the indexed, normalized email column; older mixed-case
    # records still work through the case-insensitive compatibility fallback.
    instructor = db.query(Instructor).filter(Instructor.email == email).first()
    if instructor is None:
        instructor = db.query(Instructor).filter(func.lower(Instructor.email) == email).first()
    lookup_ms = (time.perf_counter() - started) * 1000

    checked_at = time.perf_counter()
    password_valid = bool(instructor) and verify_password(password, instructor.password_hash)
    verify_ms = (time.perf_counter() - checked_at) * 1000
    total_ms = (time.perf_counter() - started) * 1000
    if lookup_ms >= 200 or verify_ms >= 300 or total_ms >= 750:
        # Deliberately never log the email, password or JWT.
        perf_logger.warning(
            "[PERF] login database_ms=%.1f bcrypt_ms=%.1f total_ms=%.1f",
            lookup_ms, verify_ms, total_ms,
        )
    if not instructor or not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        data={"sub": instructor.email, "instructor_id": instructor.id},
        expires_delta=access_token_expires,
    )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
def login_instructor(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> dict:
    """OAuth2 form-based sign in."""
    return _authenticate(
        form_data.username.lower().strip(),
        form_data.password,
        db,
    )


@router.post("/login/json", response_model=Token)
def login_instructor_json(
    payload: InstructorLogin,
    db: Session = Depends(get_db),
) -> dict:
    """JSON sign in for the React frontend."""
    return _authenticate(str(payload.email).lower().strip(), payload.password, db)
