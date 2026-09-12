"""
Tests for the Writer agent.

The LLM client is mocked so these tests run instantly and free.
"""

from unittest.mock import patch

import pytest

from app.agents.writer import run_writer, WriterError
from app.graph.state import ConfidenceLevel, Evidence, EvidenceType, Task
from app.llm.client import LLMClientError


def _make_tasks():
    return [Task(id=1, description="Find AI adoption statistics")]


def _make_evidence():
    return [
        Evidence(
            task_id=1,
            claim="AI adoption grew 40% in 2026",
            source_title="TechReport",
            type=EvidenceType.EVIDENCE,
            confidence=ConfidenceLevel.HIGH,
        )
    ]


def _valid_llm_response(**overrides):
    base = {
        "title": "AI Adoption Report",
        "executive_summary": "Summary text.",
        "introduction": "Intro text.",
        "findings": "Findings text.",
        "analysis": "Analysis text.",
        "limitations": "No major limitations.",
        "conclusion": "Conclusion text.",
        "references": [{"title": "TechReport", "url": "https://example.com"}],
    }
    base.update(overrides)
    return base


@patch("app.agents.writer.llm_client")
def test_run_writer_returns_valid_draft(mock_llm_client):
    mock_llm_client.generate_json.return_value = _valid_llm_response()

    draft = run_writer("Research AI adoption", _make_tasks(), _make_evidence())

    assert draft.title == "AI Adoption Report"
    assert draft.executive_summary == "Summary text."
    assert len(draft.references) == 1
    assert draft.references[0].title == "TechReport"


@patch("app.agents.writer.llm_client")
def test_run_writer_raises_on_missing_sections(mock_llm_client):
    incomplete = _valid_llm_response()
    del incomplete["conclusion"]
    mock_llm_client.generate_json.return_value = incomplete

    with pytest.raises(WriterError):
        run_writer("Research AI adoption", _make_tasks(), _make_evidence())


@patch("app.agents.writer.llm_client")
def test_run_writer_raises_on_llm_failure(mock_llm_client):
    mock_llm_client.generate_json.side_effect = LLMClientError("timeout")

    with pytest.raises(WriterError):
        run_writer("Research AI adoption", _make_tasks(), _make_evidence())


@patch("app.agents.writer.llm_client")
def test_run_writer_works_with_no_evidence(mock_llm_client):
    mock_llm_client.generate_json.return_value = _valid_llm_response(
        limitations="No evidence was found for this goal; findings are inconclusive."
    )

    draft = run_writer("Research an obscure topic", [], [])

    assert "inconclusive" in draft.limitations.lower() or "no evidence" in draft.limitations.lower()


@patch("app.agents.writer.llm_client")
def test_run_writer_skips_malformed_references(mock_llm_client):
    mock_llm_client.generate_json.return_value = _valid_llm_response(
        references=[
            {"title": "", "url": "https://example.com"},  # missing title
            {"title": "Valid Source", "url": None},
            "not even a dict",
        ]
    )

    draft = run_writer("Research AI adoption", _make_tasks(), _make_evidence())

    assert len(draft.references) == 1
    assert draft.references[0].title == "Valid Source"


@patch("app.agents.writer.llm_client")
def test_run_writer_handles_missing_references_key(mock_llm_client):
    response = _valid_llm_response()
    del response["references"]
    mock_llm_client.generate_json.return_value = response

    draft = run_writer("Research AI adoption", _make_tasks(), _make_evidence())

    assert draft.references == []