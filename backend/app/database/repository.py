"""
Repository layer for research sessions.

This has the EXACT SAME function names/signatures as the in-memory
version from Module 14 (app/api/dependencies.py) - create_session,
update_session, get_session - so the API routes don't need to change.
Only the storage mechanism underneath changes: Postgres instead of a
Python dict.
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.database.models import ResearchSessionModel
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _model_to_dict(model: ResearchSessionModel) -> dict:
    """Convert a SQLAlchemy model into the same dict shape the routes expect."""
    return {
        "research_id": model.research_id,
        "status": model.status,
        "user_goal": model.user_goal,
        "tasks": model.tasks or [],
        "evidence": model.evidence or [],
        "images": model.images or [],
        "videos": model.videos or [],
        "sources": model.sources or [],
        "evidence_count": model.evidence_count,
        "revision_count": model.revision_count,
        "final_report": model.final_report,
        "critique": model.critique,
        "errors": model.errors or [],
        "agent_events": model.agent_events or [],
    }


def create_session(user_goal: str, user_id: Optional[str] = None, db: Optional[Session] = None) -> str:
    """Create a new research session in the database and return its ID."""
    research_id = str(uuid.uuid4())
    owns_session = db is None
    db = db or SessionLocal()

    try:
        record = ResearchSessionModel(
            research_id=research_id,
            user_goal=user_goal,
            user_id=user_id,
            status="running",
            tasks=[],
            errors=[],
            agent_events=[],
        )
        db.add(record)
        db.commit()
        logger.info(f"Created research session {research_id} for user {user_id}")
        return research_id
    finally:
        if owns_session:
            db.close()


def update_session(research_id: str, db: Optional[Session] = None, **updates) -> None:
    """Merge updates into an existing session row."""
    owns_session = db is None
    db = db or SessionLocal()

    try:
        record = db.get(ResearchSessionModel, research_id)
        if record is None:
            logger.warning(f"Tried to update nonexistent session {research_id}")
            return

        for key, value in updates.items():
            if key == "tasks" and value:
                value = [t.model_dump() if hasattr(t, "model_dump") else t for t in value]
            if key == "evidence" and value:
                value = [e.model_dump() if hasattr(e, "model_dump") else e for e in value]
            if key == "sources" and value:
                value = [s.model_dump() if hasattr(s, "model_dump") else s for s in value]
            if key == "final_report" and value and hasattr(value, "model_dump"):
                value = value.model_dump()
            if key == "critique" and value and hasattr(value, "model_dump"):
                value = value.model_dump()
            if key == "agent_events" and value:
                value = [e.model_dump() if hasattr(e, "model_dump") else e for e in value]
            setattr(record, key, value)

        db.commit()
    finally:
        if owns_session:
            db.close()


from datetime import datetime, timedelta, timezone


def reconcile_stale_sessions(
    max_age_minutes: int = 10,
    db: Optional[Session] = None,
) -> int:
    """
    Find research sessions that have been in 'running' status longer than max_age_minutes,
    and transition them to 'failed' with an explanatory error.
    This prevents crashed, interrupted, or orphaned jobs from staying 'running' forever.
    """
    owns_session = db is None
    db = db or SessionLocal()
    count = 0

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
        stale_records = (
            db.query(ResearchSessionModel)
            .filter(
                ResearchSessionModel.status == "running",
            )
            .all()
        )

        for record in stale_records:
            rec_time = record.updated_at or record.created_at
            if rec_time:
                if rec_time.tzinfo is None:
                    rec_time = rec_time.replace(tzinfo=timezone.utc)
                if rec_time < cutoff:
                    record.status = "failed"
                    existing_errors = list(record.errors or [])
                    if not existing_errors:
                        existing_errors.append(
                            "Research job timed out or was interrupted before completion."
                        )
                    record.errors = existing_errors
                    count += 1

        if count > 0:
            db.commit()
            logger.info(f"Reconciled {count} stale running research session(s) to failed.")

        return count
    except Exception as exc:
        logger.warning(f"Error during stale session reconciliation: {exc}")
        return 0
    finally:
        if owns_session:
            db.close()


def get_session(research_id: str, user_id: Optional[str] = None, db: Optional[Session] = None) -> Optional[dict]:
    """Retrieve a session by ID as a dict, or None if it doesn't exist."""
    owns_session = db is None
    db = db or SessionLocal()

    try:
        query = db.query(ResearchSessionModel).filter(ResearchSessionModel.research_id == research_id)
        if user_id:
            query = query.filter((ResearchSessionModel.user_id == user_id) | (ResearchSessionModel.user_id.is_(None)))
        record = query.first()
        if record is None:
            return None

        # Check if single record is stale
        if record.status == "running":
            rec_time = record.updated_at or record.created_at
            if rec_time:
                if rec_time.tzinfo is None:
                    rec_time = rec_time.replace(tzinfo=timezone.utc)
                if rec_time < datetime.now(timezone.utc) - timedelta(minutes=10):
                    record.status = "failed"
                    existing_errors = list(record.errors or [])
                    if not existing_errors:
                        existing_errors.append(
                            "Research job timed out or was interrupted before completion."
                        )
                    record.errors = existing_errors
                    db.commit()

        return _model_to_dict(record)
    finally:
        if owns_session:
            db.close()


def delete_session(research_id: str, user_id: Optional[str] = None, db: Optional[Session] = None) -> bool:
    """Delete a research session by ID, returning True if deleted."""
    owns_session = db is None
    db = db or SessionLocal()

    try:
        query = db.query(ResearchSessionModel).filter(ResearchSessionModel.research_id == research_id)
        if user_id:
            query = query.filter((ResearchSessionModel.user_id == user_id) | (ResearchSessionModel.user_id.is_(None)))
        record = query.first()
        if not record:
            return False
        db.delete(record)
        db.commit()
        logger.info(f"Deleted research session {research_id}")
        return True
    finally:
        if owns_session:
            db.close()


def list_sessions(
    limit: int = 20,
    user_id: Optional[str] = None,
    search: Optional[str] = None,
    db: Optional[Session] = None,
) -> list[dict]:
    """
    Return recent research sessions, newest first, with optional user_id and text search filtering.
    """
    owns_session = db is None
    db = db or SessionLocal()

    try:
        # Reconcile any stale running sessions first
        reconcile_stale_sessions(max_age_minutes=10, db=db)

        query = db.query(
            ResearchSessionModel.research_id,
            ResearchSessionModel.user_goal,
            ResearchSessionModel.status,
            ResearchSessionModel.created_at,
            ResearchSessionModel.final_report,
        )

        if user_id:
            query = query.filter((ResearchSessionModel.user_id == user_id) | (ResearchSessionModel.user_id.is_(None)))

        if search and search.strip():
            pattern = f"%{search.strip()}%"
            query = query.filter(ResearchSessionModel.user_goal.ilike(pattern))

        records = (
            query.order_by(ResearchSessionModel.created_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "research_id": record.research_id,
                "user_goal": record.user_goal,
                "status": record.status,
                "created_at": (
                    record.created_at.isoformat()
                    if record.created_at
                    else None
                ),
                "final_report_title": (
                    (record.final_report or {}).get("title")
                    if record.final_report
                    else None
                ),
            }
            for record in records
        ]

    finally:
        if owns_session:
            db.close()