
"""
Tests for the research session repository.

Uses an in-memory SQLite database instead of real PostgreSQL, so
tests run instantly and don't require a running Postgres server.
JSON columns behave the same way across both backends.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.database import repository


@pytest.fixture
def db_session():
    """Create a fresh in-memory SQLite database for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSessionLocal = sessionmaker(bind=engine)
    session = TestSessionLocal()
    yield session
    session.close()


def test_create_session_returns_id(db_session):
    research_id = repository.create_session(
        "Research AI adoption",
        db=db_session,
    )

    assert research_id is not None
    assert len(research_id) == 36


def test_get_session_returns_created_session(db_session):
    research_id = repository.create_session(
        "Research AI adoption",
        db=db_session,
    )

    session = repository.get_session(
        research_id,
        db=db_session,
    )

    assert session["research_id"] == research_id
    assert session["user_goal"] == "Research AI adoption"
    assert session["status"] == "running"
    assert session["tasks"] == []


def test_get_session_returns_none_for_unknown_id(db_session):
    result = repository.get_session(
        "nonexistent-id",
        db=db_session,
    )

    assert result is None


def test_update_session_merges_changes(db_session):
    research_id = repository.create_session(
        "Research AI adoption",
        db=db_session,
    )

    repository.update_session(
        research_id,
        db=db_session,
        status="completed",
        evidence_count=5,
    )

    session = repository.get_session(
        research_id,
        db=db_session,
    )

    assert session["status"] == "completed"
    assert session["evidence_count"] == 5


def test_update_session_ignores_unknown_id(db_session):
    repository.update_session(
        "nonexistent-id",
        db=db_session,
        status="completed",
    )


def test_update_session_stores_final_report(db_session):
    research_id = repository.create_session(
        "Research AI adoption",
        db=db_session,
    )

    repository.update_session(
        research_id,
        db=db_session,
        final_report={
            "title": "Test Report",
            "executive_summary": "Summary",
        },
    )

    session = repository.get_session(
        research_id,
        db=db_session,
    )

    assert session["final_report"]["title"] == "Test Report"


def test_list_sessions_returns_lightweight_history(db_session):
    first_id = repository.create_session(
        "First research",
        db=db_session,
    )

    second_id = repository.create_session(
        "Second research",
        db=db_session,
    )

    repository.update_session(
        first_id,
        db=db_session,
        status="completed",
        final_report={
            "title": "First Report",
            "executive_summary": "Summary",
        },
    )

    sessions = repository.list_sessions(
        limit=10,
        db=db_session,
    )

    assert len(sessions) == 2

    session_ids = {
        session["research_id"]
        for session in sessions
    }

    assert first_id in session_ids
    assert second_id in session_ids

    first_session = next(
        session
        for session in sessions
        if session["research_id"] == first_id
    )

    assert first_session["user_goal"] == "First research"
    assert first_session["status"] == "completed"
    assert first_session["final_report_title"] == "First Report"

    assert set(first_session.keys()) == {
        "research_id",
        "user_goal",
        "status",
        "created_at",
        "final_report_title",
    }

