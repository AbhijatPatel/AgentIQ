"""
End-to-end integration tests for the full AgentIQ pipeline.

Unlike test_graph.py (which tests each node in isolation), these tests
run the FULL compiled workflow (run_agentiq) start to finish, with
mocks only at the outermost boundaries: the LLM client and external
tools (web search, RAG retrieval). This verifies the entire chain -
Planner -> Researcher -> Writer -> Critic - actually wires together
correctly end to end, matching the master plan's required integration
test:

    User Goal -> Planner -> Researcher -> Writer -> Critic -> Final Report

We also test failure scenarios: what happens when the LLM fails
entirely, and when research tools return nothing.
"""

from unittest.mock import patch

from app.graph.workflow import run_agentiq


def _mock_llm_responses():
    """
    Sequence of JSON responses the mocked llm_client.generate_json will
    return, in order: Planner call, Researcher call (once per task),
    Writer call, Critic call.
    """
    planner_response = {
        "tasks": [
            {"id": 1, "description": "Research topic A", "priority": "high"},
            {"id": 2, "description": "Research topic B", "priority": "medium"},
        ]
    }

    researcher_response = {
        "evidence": [
            {
                "claim": "Example claim from evidence",
                "source_title": "Example Source",
                "source_url": "https://example.com",
                "type": "evidence",
                "confidence": "high",
            }
        ],
        "gaps": [],
    }

    writer_response = {
        "title": "Integration Test Report",
        "executive_summary": "Summary text.",
        "introduction": "Intro text.",
        "findings": "Findings text.",
        "analysis": "Analysis text.",
        "limitations": "No major limitations.",
        "conclusion": "Conclusion text.",
        "references": [{"title": "Example Source", "url": "https://example.com"}],
    }

    critic_response = {
        "status": "pass",
        "score": 9.0,
        "issues": [],
        "suggestions": [],
    }

    # Planner (1) + Researcher (2 tasks) + Writer (1) + Critic (1) = 5 calls
    return [planner_response, researcher_response, researcher_response, writer_response, critic_response]


@patch("app.agents.researcher.web_search")
@patch("app.agents.researcher.retrieve")
@patch("app.llm.client.llm_client.generate_json")
def test_full_pipeline_end_to_end_produces_final_report(
    mock_generate_json, mock_retrieve, mock_web_search
):
    mock_generate_json.side_effect = _mock_llm_responses()
    mock_retrieve.return_value = []
    mock_web_search.return_value = [
        {"title": "Web Result", "url": "https://example.com", "content": "Some content", "source": "example.com"}
    ]

    result = run_agentiq("Research the impact of AI on healthcare")

    # Planner ran
    assert len(result["tasks"]) == 2

    # Researcher ran for both tasks
    assert len(result["evidence"]) == 2  # one evidence item per task

    # Writer + Critic ran
    assert result["final_report"] is not None
    assert result["final_report"].title == "Integration Test Report"
    assert result["critique"] is not None
    assert result["critique"].status.value == "pass"
    assert result["critique"].score == 9.0

    # No unexpected errors along the way
    assert result.get("errors", []) == []


@patch("app.llm.client.llm_client.generate_json")
def test_full_pipeline_handles_planner_failure_gracefully(mock_generate_json):
    from app.llm.client import LLMClientError

    # Every LLM call fails
    mock_generate_json.side_effect = LLMClientError("Simulated total LLM outage")

    result = run_agentiq("Research something when the LLM is down")

    # Planner failed, so no tasks
    assert result["tasks"] == []
    # An error should be recorded
    assert len(result.get("errors", [])) >= 1
    # No final report should exist
    assert result.get("final_report") is None


@patch("app.agents.researcher.web_search")
@patch("app.agents.researcher.retrieve")
@patch("app.llm.client.llm_client.generate_json")
def test_full_pipeline_handles_no_research_material_found(
    mock_generate_json, mock_retrieve, mock_web_search
):
    """
    If both RAG and web search return nothing for every task, the
    Researcher should produce zero evidence (not fabricate any), and
    the Writer should still be asked to produce a report noting the
    lack of evidence, without the pipeline crashing.
    """
    planner_response = {
        "tasks": [{"id": 1, "description": "Research an obscure topic", "priority": "high"}]
    }
    writer_response = {
        "title": "Report With No Evidence",
        "executive_summary": "No evidence was found.",
        "introduction": "Intro.",
        "findings": "No findings available.",
        "analysis": "Insufficient data.",
        "limitations": "No evidence was found for this goal.",
        "conclusion": "Inconclusive.",
        "references": [],
    }
    critic_response = {"status": "pass", "score": 7.0, "issues": [], "suggestions": []}

    # Planner (1) + Writer (1) + Critic (1) - Researcher makes NO llm call
    # since there's no material to extract evidence from.
    mock_generate_json.side_effect = [planner_response, writer_response, critic_response]
    mock_retrieve.return_value = []
    mock_web_search.return_value = []

    result = run_agentiq("Research an obscure topic with no available data")

    assert result["evidence"] == []
    assert result["final_report"] is not None
    assert "no evidence" in result["final_report"].limitations.lower()