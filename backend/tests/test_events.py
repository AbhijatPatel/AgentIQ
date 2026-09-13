"""
Tests for agent event emission helpers.
"""

from app.graph.events import append_event, make_event
from app.graph.state import AgentEvent


def test_make_event_creates_valid_agent_event():
    event = make_event("planner", "started", "Planning tasks")

    assert isinstance(event, AgentEvent)
    assert event.agent == "planner"
    assert event.event == "started"
    assert event.message == "Planning tasks"
    assert event.status == "running"
    assert event.timestamp is not None


def test_make_event_accepts_custom_status():
    event = make_event("researcher", "failed", "Something broke", status="error")
    assert event.status == "error"


def test_append_event_adds_to_list():
    events = []
    events = append_event(events, "planner", "started", "Planning tasks")

    assert len(events) == 1
    assert events[0].agent == "planner"


def test_append_event_does_not_mutate_original_list():
    """
    Critical for LangGraph state updates - we must return a NEW list,
    not mutate the one passed in, to avoid state-sharing bugs.
    """
    original = []
    result = append_event(original, "planner", "started", "Planning tasks")

    assert original == []  # original untouched
    assert len(result) == 1


def test_append_event_preserves_existing_events():
    events = [make_event("planner", "started", "First event")]
    events = append_event(events, "planner", "completed", "Second event", status="success")

    assert len(events) == 2
    assert events[0].message == "First event"
    assert events[1].message == "Second event"