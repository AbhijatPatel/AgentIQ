"""
Tests for the research API endpoints.

Uses FastAPI's TestClient. The actual pipeline (run_agentiq) is
mocked so tests run instantly without real LLM calls - background
tasks run synchronously within TestClient's request/response cycle,
so we don't need to wait/poll in tests.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.database.connection import init_db

init_db()

client = TestClient(app)


def test_health_endpoint_still_works():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("app.api.routes.research.run_agentiq")
def test_start_research_returns_id_and_running_status(mock_run_agentiq):
    mock_run_agentiq.return_value = {
        "tasks": [],
        "evidence": [],
        "revision_count": 0,
        "final_report": None,
        "critique": None,
        "errors": [],
        "agent_events": [],
    }

    response = client.post("/api/research", json={"goal": "Research AI adoption trends"})

    assert response.status_code == 202
    data = response.json()
    assert "research_id" in data
    assert data["status"] == "running"


def test_start_research_rejects_short_goal():
    response = client.post("/api/research", json={"goal": "hi"})
    assert response.status_code == 422  # Pydantic validation error


@patch("app.api.routes.research.run_agentiq")
def test_get_research_status_after_completion(mock_run_agentiq):
    mock_run_agentiq.return_value = {
        "tasks": [],
        "evidence": [],
        "revision_count": 0,
        "final_report": None,
        "critique": None,
        "errors": [],
        "agent_events": [],
    }

    start_response = client.post("/api/research", json={"goal": "Research AI adoption trends"})
    research_id = start_response.json()["research_id"]

    status_response = client.get(f"/api/research/{research_id}")

    assert status_response.status_code == 200
    data = status_response.json()
    assert data["research_id"] == research_id
    assert data["status"] == "completed"


def test_get_research_status_returns_404_for_unknown_id():
    response = client.get("/api/research/nonexistent-id")
    assert response.status_code == 404


def test_get_research_events_returns_404_for_unknown_id():
    response = client.get("/api/research/nonexistent-id/events")
    assert response.status_code == 404


@patch("app.api.routes.research.run_agentiq")
def test_get_research_events_returns_event_list(mock_run_agentiq):
    from app.graph.state import AgentEvent

    mock_run_agentiq.return_value = {
        "tasks": [],
        "evidence": [],
        "revision_count": 0,
        "final_report": None,
        "critique": None,
        "errors": [],
        "agent_events": [AgentEvent(agent="planner", event="started", message="Planning...")],
    }

    start_response = client.post("/api/research", json={"goal": "Research AI adoption trends"})
    research_id = start_response.json()["research_id"]

    events_response = client.get(f"/api/research/{research_id}/events")

    assert events_response.status_code == 200
    data = events_response.json()
    assert len(data["events"]) == 1
    assert data["events"][0]["agent"] == "planner"