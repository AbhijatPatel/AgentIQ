"""
SQLAlchemy database models.

We use one main table (research_sessions) with JSON columns for the
nested data (tasks, evidence, final_report, critique, agent_events).
This keeps the schema simple while still letting us reconstruct a
completed research session later.

JSON columns work identically for both SQLite (used in tests) and
PostgreSQL (used in production), which keeps our test suite fast and
independent of a real database connection.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class ResearchSessionModel(Base):
    __tablename__ = "research_sessions"

    research_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="running")

    tasks: Mapped[list] = mapped_column(JSON, default=list)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    images: Mapped[list] = mapped_column(JSON, default=list)
    videos: Mapped[list] = mapped_column(JSON, default=list)
    revision_count: Mapped[int] = mapped_column(Integer, default=0)
    final_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    critique: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    errors: Mapped[list] = mapped_column(JSON, default=list)
    agent_events: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )