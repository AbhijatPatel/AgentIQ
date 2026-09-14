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
    research_id = repository.create_session("Research AI adoption", db=db_session)
    assert research_id is not None
    assert len(research_id) == 36  # UUID format


def test_get_session_returns_created_session(db_session):
    research_id = repository.create_session("Research AI adoption", db=db_session)
    session = repository.get_session(research_id, db=db_session)

    assert session["research_id"] == research_id
    assert session["user_goal"] == "Research AI adoption"
    assert session["status"] == "running"
    assert session["tasks"] == []


def test_get_session_returns_none_for_unknown_id(db_session):
    result = repository.get_session("nonexistent-id", db=db_session)
    assert result is None


def test_update_session_merges_changes(db_session):
    research_id = repository.create_session("Research AI adoption", db=db_session)

    repository.update_session(
        research_id, db=db_session, status="completed", evidence_count=5
    )

    session = repository.get_session(research_id, db=db_session)
    assert session["status"] == "completed"
    assert session["evidence_count"] == 5


def test_update_session_ignores_unknown_id(db_session):
    # Should not raise, just log a warning and do nothing
    repository.update_session("nonexistent-id", db=db_session, status="completed")


def test_update_session_stores_final_report(db_session):
    research_id = repository.create_session("Research AI adoption", db=db_session)

    repository.update_session(
        research_id,
        db=db_session,
        final_report={"title": "Test Report", "executive_summary": "Summary"},
    )

    session = repository.get_session(research_id, db=db_session)
    assert session["final_report"]["title"] == "Test Report"