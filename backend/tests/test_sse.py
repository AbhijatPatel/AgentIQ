"""
Tests for the SSE research event streaming endpoint.

We mock run_agentiq (so no real pipeline runs) and verify the stream
produces valid SSE-formatted output ending with a 'done' event.
"""

import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.database.connection import init_db

init_db()

client = TestClient(app)


def test_stream_returns_404_for_unknown_session():
    response = client.get("/api/research/nonexistent-id/stream")
    assert response.status_code == 404


@patch("app.api.routes.research.run_agentiq")
def test_stream_returns_event_stream_content_type(mock_run_agentiq):
    from app.graph.state import AgentEvent

    mock_run_agentiq.return_value = {
        "tasks": [],
        "evidence": [],
        "revision_count": 0,
        "final_report": None,
        "critique": None,
        "errors": [],
        "agent_events": [
            AgentEvent(agent="planner", event="started", message="Planning..."),
            AgentEvent(agent="planner", event="completed", message="Done", status="success"),
        ],
    }

    start_response = client.post("/api/research", json={"goal": "Research AI adoption trends"})
    research_id = start_response.json()["research_id"]

    with client.stream("GET", f"/api/research/{research_id}/stream") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        received_events = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                payload = json.loads(line[len("data: "):])
                received_events.append(payload)
                if payload.get("event") == "done":
                    break

        # Should have received both agent events plus a final 'done' event
        assert any(e.get("agent") == "planner" and e.get("event") == "started" for e in received_events)
        assert any(e.get("agent") == "planner" and e.get("event") == "completed" for e in received_events)
        assert received_events[-1]["event"] == "done"
        assert received_events[-1]["status"] == "completed"