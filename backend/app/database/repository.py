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
        "evidence_count": model.evidence_count,
        "revision_count": model.revision_count,
        "final_report": model.final_report,
        "critique": model.critique,
        "errors": model.errors or [],
        "agent_events": model.agent_events or [],
    }


def create_session(user_goal: str, db: Optional[Session] = None) -> str:
    """Create a new research session in the database and return its ID."""
    research_id = str(uuid.uuid4())
    owns_session = db is None
    db = db or SessionLocal()

    try:
        record = ResearchSessionModel(
            research_id=research_id,
            user_goal=user_goal,
            status="running",
            tasks=[],
            errors=[],
            agent_events=[],
        )
        db.add(record)
        db.commit()
        logger.info(f"Created research session {research_id}")
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


def get_session(research_id: str, db: Optional[Session] = None) -> Optional[dict]:
    """Retrieve a session by ID as a dict, or None if it doesn't exist."""
    owns_session = db is None
    db = db or SessionLocal()

    try:
        record = db.get(ResearchSessionModel, research_id)
        if record is None:
            return None
        return _model_to_dict(record)
    finally:
        if owns_session:
            db.close()

def list_sessions(limit: int = 20, db: Optional[Session] = None) -> list[dict]:
    """
    Return the most recent research sessions, newest first.
    Used for the research history view - does not include full
    evidence/events to keep the response light; use get_session()
    for full detail on one session.
    """
    owns_session = db is None
    db = db or SessionLocal()

    try:
        records = (
            db.query(ResearchSessionModel)
            .order_by(ResearchSessionModel.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "research_id": r.research_id,
                "user_goal": r.user_goal,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "final_report_title": (r.final_report or {}).get("title") if r.final_report else None,
            }
            for r in records
        ]
    finally:
        if owns_session:
            db.close()