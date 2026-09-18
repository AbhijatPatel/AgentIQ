"""
Tests for the LangGraph nodes and compiled workflow.

Node tests mock the underlying agent functions so they run instantly.
The workflow compilation test verifies the graph wires together
correctly without needing any real LLM calls.
"""

from unittest.mock import patch

from app.graph.nodes import planner_node, researcher_node, writer_critic_node
from app.graph.state import (
    Critique,
    CriticStatus,
    DraftReport,
    Evidence,
    EvidenceType,
    ConfidenceLevel,
    Task,
    create_initial_state,
)
from app.graph.workflow import build_workflow


# ---------------------------------------------------------------------------
# Node tests
# ---------------------------------------------------------------------------

@patch("app.graph.nodes.run_planner")
def test_planner_node_writes_tasks(mock_run_planner):
    mock_run_planner.return_value = [Task(id=1, description="Find stats")]

    state = create_initial_state("Research AI")
    result = planner_node(state)

    assert len(result["tasks"]) == 1
    assert result["tasks"][0].description == "Find stats"


@patch("app.graph.nodes.run_planner")
def test_planner_node_handles_failure(mock_run_planner):
    from app.agents.planner import PlannerError

    mock_run_planner.side_effect = PlannerError("LLM failed")

    state = create_initial_state("Research AI")
    result = planner_node(state)

    assert result["tasks"] == []
    assert len(result["errors"]) == 1


@patch("app.graph.nodes.run_researcher")
def test_researcher_node_combines_evidence_across_tasks(mock_run_researcher):
    task1 = Task(id=1, description="Task 1")
    task2 = Task(id=2, description="Task 2")

    mock_run_researcher.side_effect = [
    ([Evidence(task_id=1, claim="Claim A", source_title="Source A")], [], []),
    ([Evidence(task_id=2, claim="Claim B", source_title="Source B")], [], []),
    ]

    state = create_initial_state("Research AI")
    state["tasks"] = [task1, task2]
    result = researcher_node(state)

    assert len(result["evidence"]) == 2


def test_researcher_node_skips_when_no_tasks():
    state = create_initial_state("Research AI")
    state["tasks"] = []
    result = researcher_node(state)

    assert result["evidence"] == []


@patch("app.graph.nodes.run_researcher")
def test_researcher_node_continues_after_one_task_fails(mock_run_researcher):
    from app.agents.researcher import ResearcherError

    task1 = Task(id=1, description="Task 1")
    task2 = Task(id=2, description="Task 2")

    mock_run_researcher.side_effect = [
    ResearcherError("failed"),
    ([Evidence(task_id=2, claim="Claim B", source_title="Source B")], [], []),
    ]
    state = create_initial_state("Research AI")
    state["tasks"] = [task1, task2]
    result = researcher_node(state)

    assert len(result["evidence"]) == 1
    assert len(result["errors"]) == 1


@patch("app.graph.nodes.run_revision_loop")
def test_writer_critic_node_writes_final_report(mock_run_revision_loop):
    draft = DraftReport(
        title="Report", executive_summary="S", introduction="I",
        findings="F", analysis="A", limitations="L", conclusion="C",
    )
    critique = Critique(status=CriticStatus.PASS, score=9.0)

    mock_run_revision_loop.return_value = {
        "final_report": draft,
        "final_critique": critique,
        "revision_count": 0,
        "quality_status": "passed",
    }

    state = create_initial_state("Research AI")
    result = writer_critic_node(state)

    assert result["final_report"].title == "Report"
    assert result["critique"].status == CriticStatus.PASS
    assert result["revision_count"] == 0


@patch("app.graph.nodes.run_revision_loop")
def test_writer_critic_node_handles_total_failure(mock_run_revision_loop):
    from app.agents.orchestrator import RevisionLoopError

    mock_run_revision_loop.side_effect = RevisionLoopError("no draft possible")

    state = create_initial_state("Research AI")
    result = writer_critic_node(state)

    assert len(result["errors"]) == 1


# ---------------------------------------------------------------------------
# Workflow compilation test
# ---------------------------------------------------------------------------

def test_workflow_compiles_without_errors():
    """
    Just verifies the graph structure is valid and compiles - this
    catches typos in node/edge names without needing real LLM calls.
    """
    workflow = build_workflow()
    assert workflow is not None
    