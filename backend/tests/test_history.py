"""
Tests for research history (list sessions).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.database import repository


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSessionLocal = sessionmaker(bind=engine)
    session = TestSessionLocal()
    yield session
    session.close()


def test_list_sessions_returns_empty_when_none_exist(db_session):
    result = repository.list_sessions(db=db_session)
    assert result == []


def test_list_sessions_returns_created_sessions(db_session):
    repository.create_session("Research topic A", db=db_session)
    repository.create_session("Research topic B", db=db_session)

    result = repository.list_sessions(db=db_session)

    assert len(result) == 2
    assert result[0]["user_goal"] in ("Research topic A", "Research topic B")


def test_list_sessions_respects_limit(db_session):
    for i in range(5):
        repository.create_session(f"Topic {i}", db=db_session)

    result = repository.list_sessions(limit=3, db=db_session)

    assert len(result) == 3


def test_list_sessions_includes_report_title_when_completed(db_session):
    research_id = repository.create_session("Research topic", db=db_session)
    repository.update_session(
        research_id,
        db=db_session,
        status="completed",
        final_report={"title": "My Report Title"},
    )

    result = repository.list_sessions(db=db_session)

    assert result[0]["final_report_title"] == "My Report Title"