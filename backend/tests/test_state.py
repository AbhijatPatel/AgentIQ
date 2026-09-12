"""
Tests for the shared AgentIQ graph state.
"""

from app.graph.state import (
    AgentState,
    AgentEvent,
    Critique,
    CriticStatus,
    DraftReport,
    Evidence,
    EvidenceType,
    ConfidenceLevel,
    MAX_REVISIONS,
    Priority,
    Source,
    Task,
    create_initial_state,
)


def test_create_initial_state_sets_required_defaults():
    state = create_initial_state("Research AI in healthcare")

    assert state["user_goal"] == "Research AI in healthcare"
    assert state["tasks"] == []
    assert state["evidence"] == []
    assert state["sources"] == []
    assert state["revision_count"] == 0
    assert state["agent_events"] == []
    assert state["errors"] == []


def test_task_defaults_to_medium_priority():
    task = Task(id=1, description="Find adoption stats")
    assert task.priority == Priority.MEDIUM
    assert task.completed is False


def test_evidence_requires_task_id_and_claim():
    evidence = Evidence(
        task_id=1,
        claim="AI adoption grew 40%",
        source_title="TechReport",
        type=EvidenceType.EVIDENCE,
        confidence=ConfidenceLevel.HIGH,
    )
    assert evidence.task_id == 1
    assert evidence.type == EvidenceType.EVIDENCE


def test_draft_report_references_default_to_empty_list():
    draft = DraftReport(
        title="AI in Healthcare",
        executive_summary="...",
        introduction="...",
        findings="...",
        analysis="...",
        limitations="...",
        conclusion="...",
    )
    assert draft.references == []


def test_critique_pass_status():
    critique = Critique(status=CriticStatus.PASS, score=8.5)
    assert critique.status == "pass"
    assert critique.issues == []


def test_max_revisions_constant_is_three():
    assert MAX_REVISIONS == 3


def test_agent_event_has_auto_timestamp():
    event = AgentEvent(agent="planner", event="started", message="Planning tasks")
    assert event.agent == "planner"
    assert event.timestamp is not None


def test_source_url_and_domain_are_optional():
    source = Source(title="Some Article")
    assert source.url is None
    assert source.domain is None


def test_state_can_be_progressively_updated():
    """Simulates how LangGraph nodes would update state step by step."""
    state = create_initial_state("Research AI in healthcare")

    # Planner node adds tasks
    state["tasks"] = [Task(id=1, description="Find adoption stats")]
    assert len(state["tasks"]) == 1

    # Researcher node adds evidence
    state["evidence"] = [
        Evidence(
            task_id=1,
            claim="AI adoption grew 40%",
            source_title="TechReport",
        )
    ]
    assert len(state["evidence"]) == 1

    # Revision loop increments counter
    state["revision_count"] += 1
    assert state["revision_count"] == 1