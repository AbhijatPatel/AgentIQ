"""
Shared dependencies for the API layer.

For now, this holds a simple in-memory store for research sessions.
Module 16 will replace this with PostgreSQL so sessions persist across
restarts - the interface (get/set/update) is designed to make that
swap easy later without touching the route code much.
"""

from __future__ import annotations

import threading
import uuid
from typing import Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)

# research_id -> session dict. Simple, thread-safe in-memory storage.
_sessions: dict[str, dict] = {}
_lock = threading.Lock()


def create_session(user_goal: str) -> str:
    """Create a new research session and return its ID."""
    research_id = str(uuid.uuid4())
    with _lock:
        _sessions[research_id] = {
            "research_id": research_id,
            "status": "running",
            "user_goal": user_goal,
            "tasks": [],
            "evidence_count": 0,
            "revision_count": 0,
            "final_report": None,
            "critique": None,
            "errors": [],
            "agent_events": [],
        }
    logger.info(f"Created research session {research_id}")
    return research_id


def update_session(research_id: str, **updates) -> None:
    """Merge updates into an existing session."""
    with _lock:
        if research_id in _sessions:
            _sessions[research_id].update(updates)


def get_session(research_id: str) -> Optional[dict]:
    """Retrieve a session by ID, or None if it doesn't exist."""
    with _lock:
        return _sessions.get(research_id)