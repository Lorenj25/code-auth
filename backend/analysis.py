"""Background AI analysis and live status notifications.

No fallback scores are generated: unavailable models produce explicit failures.
"""

from __future__ import annotations

import logging
import threading
import time
from backend.database import SessionLocal
from backend.models import Submission
from backend.time_utils import utc_isoformat
from backend.ws import manager

logger = logging.getLogger(__name__)
# Limit concurrent model inference in a single FastAPI process.
inference_lock = threading.Lock()


def _broadcast(submission: Submission) -> None:
    """Send a minimal lobby-scoped status event (never send submitted source code)."""
    try:
        manager.broadcast_threadsafe(
            str(submission.lobby_id),
            {
                "type": "submission_updated",
                "submission": {
                    "id": submission.id,
                    "lobby_id": str(submission.lobby_id),
                    "student_id": submission.student_id,
                    "file_name": submission.file_name,
                    "language": submission.language,
                    "status": submission.status,
                    "ai_probability": submission.ai_probability,
                    "risk_level": submission.risk_level,
                    "error_message": submission.error_message,
                    "created_at": utc_isoformat(submission.created_at),
                },
            },
        )
    except Exception:
        # A WebSocket problem must not affect the durable database result.
        logger.exception("Unable to notify lobby for submission %s", submission.id)


def run_analysis(submission_id: int) -> None:
    """Analyze a submitted file in its own session and persist final status.

    Transitions pending -> analyzing -> done/failed. On errors, the row remains
    available for instructor review, including a failure explanation.
    """
    started = time.perf_counter()
    db = SessionLocal()
    submission = None
    try:
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if submission is None:
            logger.error("[ANALYSIS ERROR] Submission %s not found", submission_id)
            return

        submission.status = "analyzing"
        submission.ai_probability = None
        submission.risk_level = None
        submission.error_message = None
        db.commit()
        _broadcast(submission)
        logger.info("[ANALYSIS START] %s: %s (%s)", submission_id, submission.file_name, submission.language)

        with inference_lock:
            try:
                from ml.predictor import analyze
                result = analyze(submission.source_code, submission.file_name)
                # Preserve the existing predictor's own validation, never invent results.
                submission.ai_probability = float(result["ai_probability"])
                submission.risk_level = str(result["risk_level"])
                submission.status = "done"
                submission.error_message = None
            except Exception as error:
                logger.exception("[ANALYSIS EXCEPTION] %s", submission_id)
                submission.status = "failed"
                submission.ai_probability = None
                submission.risk_level = None
                submission.error_message = str(error) or type(error).__name__

        db.commit()
        _broadcast(submission)
        logger.info("[ANALYSIS COMPLETE] %s status=%s elapsed=%.2fs", submission_id, submission.status, time.perf_counter() - started)
    except Exception as error:
        logger.exception("[ANALYSIS CRITICAL ERROR] %s", submission_id)
        db.rollback()
        # A database transaction failure may be temporary. Best effort: store
        # a failed status so the UI does not show a perpetual "Analyzing" state.
        try:
            if submission is not None:
                submission = db.query(Submission).filter(Submission.id == submission_id).first()
                if submission is not None:
                    submission.status = "failed"
                    submission.ai_probability = None
                    submission.risk_level = None
                    submission.error_message = f"Analysis could not complete: {type(error).__name__}"
                    db.commit()
                    _broadcast(submission)
        except Exception:
            logger.exception("Unable to persist failure for submission %s", submission_id)
            db.rollback()
    finally:
        db.close()
