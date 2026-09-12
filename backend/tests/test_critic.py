"""
Tests for the Critic agent.

The LLM client is mocked so these tests run instantly and free.
"""

from unittest.mock import patch

import pytest

from app.agents.critic import run_critic, CriticError
from app.graph.state import (
    ConfidenceLevel,
    CriticStatus,
    DraftReport,
    Evidence,
    EvidenceType,
)
from app.llm.client import LLMClientError


def _make_evidence():
    return [
        Evidence(
            task_id=1,
            claim="AI adoption grew 40%",
            source_title="TechReport",
            type=EvidenceType.EVIDENCE,
            confidence=ConfidenceLevel.HIGH,
        )
    ]


def _make_draft():
    return DraftReport(
        title="AI Adoption Report",
        executive_summary="Summary.",
        introduction="Intro.",
        findings="Findings.",
        analysis="Analysis.",
        limitations="None noted.",
        conclusion="Conclusion.",
    )


@patch("app.agents.critic.llm_client")
def test_run_critic_returns_pass_status(mock_llm_client):
    mock_llm_client.generate_json.return_value = {
        "status": "pass",
        "score": 8.5,
        "issues": [],
        "suggestions": [],
    }

    critique = run_critic("Research AI adoption", _make_evidence(), _make_draft())

    assert critique.status == CriticStatus.PASS
    assert critique.score == 8.5


@patch("app.agents.critic.llm_client")
def test_run_critic_returns_revise_status_with_issues(mock_llm_client):
    mock_llm_client.generate_json.return_value = {
        "status": "revise",
        "score": 4.0,
        "issues": ["Claim lacks sufficient evidence"],
        "suggestions": ["Add a stronger source"],
    }

    critique = run_critic("Research AI adoption", _make_evidence(), _make_draft())

    assert critique.status == CriticStatus.REVISE
    assert "Claim lacks sufficient evidence" in critique.issues
    assert "Add a stronger source" in critique.suggestions


@patch("app.agents.critic.llm_client")
def test_run_critic_overrides_pass_when_score_too_low(mock_llm_client):
    """Safety net: even if LLM says 'pass', a low score should force 'revise'."""
    mock_llm_client.generate_json.return_value = {
        "status": "pass",
        "score": 3.0,
        "issues": [],
        "suggestions": [],
    }

    critique = run_critic("Research AI adoption", _make_evidence(), _make_draft())

    assert critique.status == CriticStatus.REVISE


@patch("app.agents.critic.llm_client")
def test_run_critic_clamps_out_of_range_score(mock_llm_client):
    mock_llm_client.generate_json.return_value = {
        "status": "revise",
        "score": 15.0,
        "issues": [],
        "suggestions": [],
    }

    critique = run_critic("Research AI adoption", _make_evidence(), _make_draft())

    assert critique.score == 10.0


@patch("app.agents.critic.llm_client")
def test_run_critic_defaults_invalid_status_to_revise(mock_llm_client):
    mock_llm_client.generate_json.return_value = {
        "status": "maybe??",
        "score": 7.0,
        "issues": [],
        "suggestions": [],
    }

    critique = run_critic("Research AI adoption", _make_evidence(), _make_draft())

    assert critique.status == CriticStatus.REVISE


@patch("app.agents.critic.llm_client")
def test_run_critic_raises_on_llm_failure(mock_llm_client):
    mock_llm_client.generate_json.side_effect = LLMClientError("timeout")

    with pytest.raises(CriticError):
        run_critic("Research AI adoption", _make_evidence(), _make_draft())


@patch("app.agents.critic.llm_client")
def test_run_critic_handles_missing_score(mock_llm_client):
    mock_llm_client.generate_json.return_value = {
        "status": "revise",
        "issues": [],
        "suggestions": [],
    }

    critique = run_critic("Research AI adoption", _make_evidence(), _make_draft())

    assert critique.score == 0.0