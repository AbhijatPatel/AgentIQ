"""
Tests for the Writer <-> Critic self-critique revision loop.

Writer and Critic internals are mocked at the LLM level so we can
control exactly how many revisions happen and verify MAX_REVISIONS
is respected.
"""

from unittest.mock import patch

import pytest

from app.agents.orchestrator import run_revision_loop, RevisionLoopError
from app.graph.state import MAX_REVISIONS, Task


def _make_tasks():
    return [Task(id=1, description="Find AI adoption statistics")]


def _valid_draft_response(**overrides):
    base = {
        "title": "AI Adoption Report",
        "executive_summary": "Summary.",
        "introduction": "Intro.",
        "findings": "Findings.",
        "analysis": "Analysis.",
        "limitations": "None noted.",
        "conclusion": "Conclusion.",
        "references": [],
    }
    base.update(overrides)
    return base


@patch("app.agents.orchestrator.run_critic")
@patch("app.agents.orchestrator.run_writer")
def test_loop_passes_on_first_try(mock_run_writer, mock_run_critic):
    from app.graph.state import DraftReport, Critique, CriticStatus

    mock_run_writer.return_value = DraftReport(**_valid_draft_response())
    mock_run_critic.return_value = Critique(status=CriticStatus.PASS, score=9.0)

    result = run_revision_loop("Research AI adoption", _make_tasks(), [])

    assert result["quality_status"] == "passed"
    assert result["revision_count"] == 0
    mock_run_writer.assert_called_once()


@patch("app.agents.orchestrator.llm_client")
@patch("app.agents.orchestrator.run_critic")
@patch("app.agents.orchestrator.run_writer")
def test_loop_revises_once_then_passes(mock_run_writer, mock_run_critic, mock_llm_client):
    from app.graph.state import DraftReport, Critique, CriticStatus

    mock_run_writer.return_value = DraftReport(**_valid_draft_response())
    mock_run_critic.side_effect = [
        Critique(status=CriticStatus.REVISE, score=4.0, issues=["Needs more sources"]),
        Critique(status=CriticStatus.PASS, score=8.0),
    ]
    mock_llm_client.generate_json.return_value = _valid_draft_response(
        title="AI Adoption Report (Revised)"
    )

    result = run_revision_loop("Research AI adoption", _make_tasks(), [])

    assert result["quality_status"] == "passed"
    assert result["revision_count"] == 1
    assert result["final_report"].title == "AI Adoption Report (Revised)"


@patch("app.agents.orchestrator.llm_client")
@patch("app.agents.orchestrator.run_critic")
@patch("app.agents.orchestrator.run_writer")
def test_loop_stops_at_max_revisions(mock_run_writer, mock_run_critic, mock_llm_client):
    from app.graph.state import DraftReport, Critique, CriticStatus

    mock_run_writer.return_value = DraftReport(**_valid_draft_response())
    # Critic ALWAYS says revise - loop must not run forever
    mock_run_critic.return_value = Critique(
        status=CriticStatus.REVISE, score=3.0, issues=["Still not good enough"]
    )
    mock_llm_client.generate_json.return_value = _valid_draft_response()

    result = run_revision_loop("Research AI adoption", _make_tasks(), [])

    assert result["quality_status"] == "max_revisions_reached"
    assert result["revision_count"] == MAX_REVISIONS
    # Critic should be called MAX_REVISIONS + 1 times (initial + after each revision)
    assert mock_run_critic.call_count == MAX_REVISIONS + 1


@patch("app.agents.orchestrator.run_writer")
def test_loop_raises_when_initial_draft_fails(mock_run_writer):
    from app.agents.writer import WriterError

    mock_run_writer.side_effect = WriterError("LLM timeout")

    with pytest.raises(RevisionLoopError):
        run_revision_loop("Research AI adoption", _make_tasks(), [])


@patch("app.agents.orchestrator.run_critic")
@patch("app.agents.orchestrator.run_writer")
def test_loop_handles_critic_failure_gracefully(mock_run_writer, mock_run_critic):
    from app.graph.state import DraftReport
    from app.agents.critic import CriticError

    mock_run_writer.return_value = DraftReport(**_valid_draft_response())
    mock_run_critic.side_effect = CriticError("LLM timeout")

    result = run_revision_loop("Research AI adoption", _make_tasks(), [])

    assert result["quality_status"] == "critic_unavailable"
    assert result["final_critique"] is None
    assert result["final_report"] is not None  # we still return the draft we have


@patch("app.agents.orchestrator.llm_client")
@patch("app.agents.orchestrator.run_critic")
@patch("app.agents.orchestrator.run_writer")
def test_loop_handles_revision_failure_gracefully(mock_run_writer, mock_run_critic, mock_llm_client):
    from app.graph.state import DraftReport, Critique, CriticStatus
    from app.llm.client import LLMClientError

    mock_run_writer.return_value = DraftReport(**_valid_draft_response())
    mock_run_critic.return_value = Critique(status=CriticStatus.REVISE, score=4.0)
    mock_llm_client.generate_json.side_effect = LLMClientError("timeout during revision")

    result = run_revision_loop("Research AI adoption", _make_tasks(), [])

    assert result["quality_status"] == "revision_failed"
    assert result["final_report"] is not None  # previous draft preserved