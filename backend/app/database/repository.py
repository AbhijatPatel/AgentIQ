"""
Repository layer for research sessions.

Provides strict multi-tenant isolation, user-scoped querying,
session creation, status updating, renaming, deletion, and reconciliation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.database.models import ResearchSessionModel
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _model_to_dict(model: ResearchSessionModel) -> dict:
    """Convert a SQLAlchemy model into the dict shape the routes and graph expect."""
    return {
        "research_id": model.research_id,
        "title": model.title,
        "status": model.status,
        "user_goal": model.user_goal,
        "user_id": model.user_id,
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
        "created_at": model.created_at.isoformat() if model.created_at else None,
        "updated_at": model.updated_at.isoformat() if model.updated_at else None,
    }


def create_session(
    user_goal: str,
    user_id: Optional[str] = None,
    title: Optional[str] = None,
    db: Optional[Session] = None,
) -> str:
    """Create a new research session assigned to an authenticated user_id."""
    research_id = str(uuid.uuid4())
    owns_session = db is None
    db = db or SessionLocal()

    try:
        record = ResearchSessionModel(
            research_id=research_id,
            title=title or (user_goal[:60] + "..." if len(user_goal) > 60 else user_goal),
            user_goal=user_goal,
            user_id=str(user_id) if user_id is not None else None,
            status="running",
            tasks=[],
            errors=[],
            agent_events=[],
        )
        db.add(record)
        db.commit()
        logger.info(f"Created research session {research_id} for user {user_id}")
        return research_id
    except Exception as exc:
        db.rollback()
        logger.error(f"Error creating research session: {exc}")
        raise
    finally:
        if owns_session:
            db.close()


def update_session(research_id: str, db: Optional[Session] = None, **updates) -> None:
    """Merge state updates into an existing session row."""
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
            if key == "final_report" and value:
                if hasattr(value, "model_dump"):
                    value = value.model_dump()
                # If session has no custom title yet, sync with final_report title
                if not record.title and isinstance(value, dict) and value.get("title"):
                    record.title = value["title"]
            if key == "critique" and value and hasattr(value, "model_dump"):
                value = value.model_dump()
            if key == "agent_events" and value:
                value = [e.model_dump() if hasattr(e, "model_dump") else e for e in value]
            setattr(record, key, value)

        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error(f"Error updating research session {research_id}: {exc}")
    finally:
        if owns_session:
            db.close()


def rename_session(
    research_id: str,
    new_title: str,
    user_id: Optional[str] = None,
    db: Optional[Session] = None,
) -> bool:
    """Rename a research session, strictly verifying user ownership."""
    owns_session = db is None
    db = db or SessionLocal()

    try:
        query = db.query(ResearchSessionModel).filter(ResearchSessionModel.research_id == research_id)
        if user_id is not None:
            query = query.filter(ResearchSessionModel.user_id == str(user_id))

        record = query.first()
        if not record:
            return False

        clean_title = new_title.strip() if new_title else record.user_goal[:60]
        record.title = clean_title
        db.commit()
        logger.info(f"Renamed research session {research_id} to {clean_title!r}")
        return True
    except Exception as exc:
        db.rollback()
        logger.error(f"Error renaming session {research_id}: {exc}")
        return False
    finally:
        if owns_session:
            db.close()


def reconcile_stale_sessions(
    max_age_minutes: int = 10,
    db: Optional[Session] = None,
) -> int:
    """
    Find research sessions in 'running' status longer than max_age_minutes
    and transition them to 'failed'.
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
        db.rollback()
        logger.warning(f"Error during stale session reconciliation: {exc}")
        return 0
    finally:
        if owns_session:
            db.close()


def get_session(
    research_id: str,
    user_id: Optional[str] = None,
    db: Optional[Session] = None,
) -> Optional[dict]:
    """
    Retrieve a session by ID as a dict.
    Strictly verifies ownership if user_id is provided.
    """
    owns_session = db is None
    db = db or SessionLocal()

    try:
        query = db.query(ResearchSessionModel).filter(ResearchSessionModel.research_id == research_id)
        if user_id is not None:
            query = query.filter(ResearchSessionModel.user_id == str(user_id))

        record = query.first()
        if record is None:
            return None

        # Reconcile if single running record has timed out
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
    except Exception as exc:
        db.rollback()
        logger.error(f"Error retrieving session {research_id}: {exc}")
        return None
    finally:
        if owns_session:
            db.close()


def delete_session(
    research_id: str,
    user_id: Optional[str] = None,
    db: Optional[Session] = None,
) -> bool:
    """Delete a research session by ID, strictly verifying ownership."""
    owns_session = db is None
    db = db or SessionLocal()

    try:
        query = db.query(ResearchSessionModel).filter(ResearchSessionModel.research_id == research_id)
        if user_id is not None:
            query = query.filter(ResearchSessionModel.user_id == str(user_id))

        record = query.first()
        if not record:
            return False

        db.delete(record)
        db.commit()
        logger.info(f"Deleted research session {research_id} for user {user_id}")
        return True
    except Exception as exc:
        db.rollback()
        logger.error(f"Error deleting session {research_id}: {exc}")
        return False
    finally:
        if owns_session:
            db.close()


def clear_all_sessions(
    user_id: Optional[str] = None,
    db: Optional[Session] = None,
) -> int:
    """Delete all research sessions belonging to the user."""
    owns_session = db is None
    db = db or SessionLocal()

    try:
        query = db.query(ResearchSessionModel)
        if user_id is not None:
            query = query.filter(ResearchSessionModel.user_id == str(user_id))

        count = query.delete(synchronize_session=False)
        db.commit()
        logger.info(f"Cleared {count} research session(s) for user {user_id}.")
        return count
    except Exception as exc:
        db.rollback()
        logger.error(f"Error clearing sessions for user {user_id}: {exc}")
        return 0
    finally:
        if owns_session:
            db.close()


def list_sessions(
    limit: int = 50,
    user_id: Optional[str] = None,
    search: Optional[str] = None,
    db: Optional[Session] = None,
) -> list[dict]:
    """
    Return recent research sessions, newest first, scoped strictly to user_id.
    """
    owns_session = db is None
    db = db or SessionLocal()

    try:
        query = db.query(
            ResearchSessionModel.research_id,
            ResearchSessionModel.title,
            ResearchSessionModel.user_goal,
            ResearchSessionModel.status,
            ResearchSessionModel.created_at,
            ResearchSessionModel.updated_at,
            ResearchSessionModel.final_report,
        )

        if user_id is not None:
            query = query.filter(ResearchSessionModel.user_id == str(user_id))

        if search and search.strip():
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    ResearchSessionModel.user_goal.ilike(pattern),
                    ResearchSessionModel.title.ilike(pattern),
                )
            )

        records = (
            query.order_by(ResearchSessionModel.created_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "research_id": record.research_id,
                "title": (
                    record.title
                    or ((record.final_report or {}).get("title") if record.final_report else None)
                    or record.user_goal
                ),
                "user_goal": record.user_goal,
                "status": record.status,
                "created_at": (
                    record.created_at.isoformat()
                    if record.created_at
                    else None
                ),
                "updated_at": (
                    record.updated_at.isoformat()
                    if record.updated_at
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
    except Exception as exc:
        db.rollback()
        logger.error(f"Error listing sessions for user {user_id}: {exc}")
        return []
    finally:
        if owns_session:
            db.close()