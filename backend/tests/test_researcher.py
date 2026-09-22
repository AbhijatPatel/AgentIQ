"""
Tests for the Researcher agent.

RAG, web search, Pollinations image generation, YouTube search, and the LLM client are
all mocked so these tests run instantly, free, and deterministically -
with zero real network calls.
"""

from unittest.mock import patch

import pytest

from app.agents.researcher import (
    ResearcherError,
    research_cache,
    run_researcher,
)
from app.graph.state import ConfidenceLevel, EvidenceType, Task
from app.llm.client import LLMClientError
from app.tools.web_search import WebSearchError


@pytest.fixture(autouse=True)
def clear_research_cache():
    """
    Keep researcher tests isolated from each other.
    """
    research_cache.clear()
    yield
    research_cache.clear()


def _make_task():
    return Task(
        id=1,
        description="Find AI adoption statistics",
    )


@patch("app.agents.researcher.llm_client")
@patch("app.agents.researcher.youtube_search")
@patch("app.agents.researcher.generate_pollinations_image")
@patch("app.agents.researcher.web_search")
@patch("app.agents.researcher.retrieve")
def test_run_researcher_returns_evidence(
    mock_retrieve,
    mock_web_search,
    mock_image_gen,
    mock_yt_search,
    mock_llm_client,
):
    mock_retrieve.return_value = [
        {
            "filename": "report.txt",
            "content": "AI adoption grew 40% in 2026.",
        }
    ]

    mock_web_search.return_value = [
        {
            "title": "Tech News",
            "url": "https://example.com",
            "content": "More AI growth data.",
        }
    ]

    mock_image_gen.return_value = {
        "url": "https://image.pollinations.ai/prompt/ai-adoption",
        "description": "AI adoption infographic",
        "source": "pollinations",
    }
    mock_yt_search.return_value = []

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

    evidence, images, videos, web_results = run_researcher(_make_task())

    assert len(evidence) == 1
    assert evidence[0].claim == "AI adoption grew 40% in 2026"
    assert evidence[0].type == EvidenceType.EVIDENCE
    assert evidence[0].confidence == ConfidenceLevel.HIGH
    assert evidence[0].task_id == 1
    assert len(images) == 1
    assert videos == []


@patch("app.agents.researcher.youtube_search")
@patch("app.agents.researcher.generate_pollinations_image")
@patch("app.agents.researcher.web_search")
@patch("app.agents.researcher.retrieve")
def test_run_researcher_returns_empty_when_no_material_found(
    mock_retrieve,
    mock_web_search,
    mock_image_gen,
    mock_yt_search,
):
    mock_retrieve.return_value = []
    mock_web_search.return_value = []
    mock_image_gen.return_value = {}
    mock_yt_search.return_value = []

    evidence, images, videos, web_results = run_researcher(_make_task())

    assert evidence == []
    assert videos == []


@patch("app.agents.researcher.llm_client")
@patch("app.agents.researcher.youtube_search")
@patch("app.agents.researcher.generate_pollinations_image")
@patch("app.agents.researcher.web_search")
@patch("app.agents.researcher.retrieve")
def test_run_researcher_continues_when_web_search_fails(
    mock_retrieve,
    mock_web_search,
    mock_image_gen,
    mock_yt_search,
    mock_llm_client,
):
    mock_retrieve.return_value = [
        {
            "filename": "doc.txt",
            "content": "Some content",
        }
    ]

    mock_web_search.side_effect = WebSearchError("rate limited")
    mock_image_gen.return_value = {"url": "https://image.pollinations.ai/prompt/img"}
    mock_yt_search.return_value = []

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

    evidence, images, videos, web_results = run_researcher(_make_task())

    assert len(evidence) == 1


@patch("app.agents.researcher.llm_client")
@patch("app.agents.researcher.youtube_search")
@patch("app.agents.researcher.generate_pollinations_image")
@patch("app.agents.researcher.web_search")
@patch("app.agents.researcher.retrieve")
def test_run_researcher_raises_on_llm_failure(
    mock_retrieve,
    mock_web_search,
    mock_image_gen,
    mock_yt_search,
    mock_llm_client,
):
    mock_retrieve.return_value = [
        {
            "filename": "doc.txt",
            "content": "Some content",
        }
    ]

    mock_web_search.return_value = []
    mock_image_gen.return_value = {}
    mock_yt_search.return_value = []

    mock_llm_client.generate_json.side_effect = LLMClientError("timeout")

    with pytest.raises(ResearcherError):
        run_researcher(_make_task())


@patch("app.agents.researcher.llm_client")
@patch("app.agents.researcher.youtube_search")
@patch("app.agents.researcher.generate_pollinations_image")
@patch("app.agents.researcher.web_search")
@patch("app.agents.researcher.retrieve")
def test_run_researcher_returns_videos(
    mock_retrieve,
    mock_web_search,
    mock_image_gen,
    mock_yt_search,
    mock_llm_client,
):
    mock_retrieve.return_value = []

    mock_web_search.return_value = [
        {
            "title": "Source",
            "url": "https://example.com",
            "content": "Content",
        }
    ]

    mock_image_gen.return_value = {}
    mock_yt_search.return_value = [
        {
            "title": "Quantum AI Overview",
            "url": "https://www.youtube.com/watch?v=abc1234",
            "source": "youtube",
            "embed_url": "https://www.youtube-nocookie.com/embed/abc1234",
        }
    ]

    mock_llm_client.generate_json.return_value = {
        "evidence": [
            {
                "claim": "A claim",
                "source_title": "Source",
                "type": "evidence",
                "confidence": "high",
            }
        ],
        "gaps": [],
    }

    evidence, images, videos, web_results = run_researcher(_make_task())

    assert len(videos) == 1
    assert videos[0]["title"] == "Quantum AI Overview"
    assert videos[0]["source"] == "youtube"
