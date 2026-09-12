"""
Tests for the Researcher agent.

RAG, web search, and the LLM client are all mocked so these tests run
instantly, free, and deterministically.
"""

from unittest.mock import patch

import pytest

from app.agents.researcher import run_researcher, ResearcherError
from app.graph.state import ConfidenceLevel, EvidenceType, Task
from app.llm.client import LLMClientError
from app.tools.web_search import WebSearchError


def _make_task():
    return Task(id=1, description="Find AI adoption statistics")


@patch("app.agents.researcher.llm_client")
@patch("app.agents.researcher.web_search")
@patch("app.agents.researcher.retrieve")
def test_run_researcher_returns_evidence(mock_retrieve, mock_web_search, mock_llm_client):
    mock_retrieve.return_value = [
        {"filename": "report.txt", "content": "AI adoption grew 40% in 2026."}
    ]
    mock_web_search.return_value = [
        {"title": "Tech News", "url": "https://example.com", "content": "More AI growth data."}
    ]
    mock_llm_client.generate_json.return_value = {
        "evidence": [
            {
                "claim": "AI adoption grew 40% in 2026",
                "source_title": "report.txt",
                "source_url": None,
                "type": "evidence",
                "confidence": "high",
            }
        ],
        "gaps": [],
    }

    evidence = run_researcher(_make_task())

    assert len(evidence) == 1
    assert evidence[0].claim == "AI adoption grew 40% in 2026"
    assert evidence[0].type == EvidenceType.EVIDENCE
    assert evidence[0].confidence == ConfidenceLevel.HIGH
    assert evidence[0].task_id == 1


@patch("app.agents.researcher.web_search")
@patch("app.agents.researcher.retrieve")
def test_run_researcher_returns_empty_when_no_material_found(mock_retrieve, mock_web_search):
    mock_retrieve.return_value = []
    mock_web_search.return_value = []

    evidence = run_researcher(_make_task())

    assert evidence == []


@patch("app.agents.researcher.llm_client")
@patch("app.agents.researcher.web_search")
@patch("app.agents.researcher.retrieve")
def test_run_researcher_continues_when_web_search_fails(
    mock_retrieve, mock_web_search, mock_llm_client
):
    mock_retrieve.return_value = [{"filename": "doc.txt", "content": "Some content"}]
    mock_web_search.side_effect = WebSearchError("rate limited")
    mock_llm_client.generate_json.return_value = {
        "evidence": [
            {
                "claim": "Some claim",
                "source_title": "doc.txt",
                "type": "evidence",
                "confidence": "medium",
            }
        ],
        "gaps": [],
    }

    evidence = run_researcher(_make_task())

    assert len(evidence) == 1  # RAG results alone were enough


@patch("app.agents.researcher.llm_client")
@patch("app.agents.researcher.web_search")
@patch("app.agents.researcher.retrieve")
def test_run_researcher_raises_on_llm_failure(mock_retrieve, mock_web_search, mock_llm_client):
    mock_retrieve.return_value = [{"filename": "doc.txt", "content": "Some content"}]
    mock_web_search.return_value = []
    mock_llm_client.generate_json.side_effect = LLMClientError("timeout")

    with pytest.raises(ResearcherError):
        run_researcher(_make_task())


@patch("app.agents.researcher.llm_client")
@patch("app.agents.researcher.web_search")
@patch("app.agents.researcher.retrieve")
def test_run_researcher_skips_malformed_evidence(mock_retrieve, mock_web_search, mock_llm_client):
    mock_retrieve.return_value = [{"filename": "doc.txt", "content": "Some content"}]
    mock_web_search.return_value = []
    mock_llm_client.generate_json.return_value = {
        "evidence": [
            {"claim": "", "source_title": "doc.txt"},  # missing claim
            {"claim": "Valid claim", "source_title": "doc.txt", "type": "evidence", "confidence": "high"},
        ],
        "gaps": [],
    }

    evidence = run_researcher(_make_task())

    assert len(evidence) == 1
    assert evidence[0].claim == "Valid claim"


@patch("app.agents.researcher.llm_client")
@patch("app.agents.researcher.web_search")
@patch("app.agents.researcher.retrieve")
def test_run_researcher_defaults_unknown_type_to_assumption(
    mock_retrieve, mock_web_search, mock_llm_client
):
    mock_retrieve.return_value = [{"filename": "doc.txt", "content": "Some content"}]
    mock_web_search.return_value = []
    mock_llm_client.generate_json.return_value = {
        "evidence": [
            {
                "claim": "Unclear claim",
                "source_title": "doc.txt",
                "type": "weird_value",
                "confidence": "medium",
            }
        ],
        "gaps": [],
    }

    evidence = run_researcher(_make_task())

    assert evidence[0].type == EvidenceType.ASSUMPTION