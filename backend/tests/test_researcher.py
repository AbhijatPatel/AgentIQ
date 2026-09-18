
"""
Tests for the Researcher agent.

RAG, web search, image search, video search, and the LLM client are
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

    The production researcher uses a shared in-memory cache, so every
    test must start and finish with an empty cache.
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
@patch("app.agents.researcher.video_search")
@patch("app.agents.researcher.image_search")
@patch("app.agents.researcher.web_search")
@patch("app.agents.researcher.retrieve")
def test_run_researcher_returns_evidence(
    mock_retrieve,
    mock_web_search,
    mock_image_search,
    mock_video_search,
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

    mock_image_search.return_value = []
    mock_video_search.return_value = []

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

    evidence, images, videos = run_researcher(_make_task())

    assert len(evidence) == 1
    assert evidence[0].claim == "AI adoption grew 40% in 2026"
    assert evidence[0].type == EvidenceType.EVIDENCE
    assert evidence[0].confidence == ConfidenceLevel.HIGH
    assert evidence[0].task_id == 1
    assert images == []
    assert videos == []


@patch("app.agents.researcher.video_search")
@patch("app.agents.researcher.image_search")
@patch("app.agents.researcher.web_search")
@patch("app.agents.researcher.retrieve")
def test_run_researcher_returns_empty_when_no_material_found(
    mock_retrieve,
    mock_web_search,
    mock_image_search,
    mock_video_search,
):
    mock_retrieve.return_value = []
    mock_web_search.return_value = []
    mock_image_search.return_value = []
    mock_video_search.return_value = []

    evidence, images, videos = run_researcher(_make_task())

    assert evidence == []
    assert images == []
    assert videos == []


@patch("app.agents.researcher.llm_client")
@patch("app.agents.researcher.video_search")
@patch("app.agents.researcher.image_search")
@patch("app.agents.researcher.web_search")
@patch("app.agents.researcher.retrieve")
def test_run_researcher_continues_when_web_search_fails(
    mock_retrieve,
    mock_web_search,
    mock_image_search,
    mock_video_search,
    mock_llm_client,
):
    mock_retrieve.return_value = [
        {
            "filename": "doc.txt",
            "content": "Some content",
        }
    ]

    mock_web_search.side_effect = WebSearchError(
        "rate limited"
    )

    mock_image_search.return_value = []
    mock_video_search.return_value = []

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

    evidence, images, videos = run_researcher(
        _make_task()
    )

    assert len(evidence) == 1


@patch("app.agents.researcher.llm_client")
@patch("app.agents.researcher.video_search")
@patch("app.agents.researcher.image_search")
@patch("app.agents.researcher.web_search")
@patch("app.agents.researcher.retrieve")
def test_run_researcher_raises_on_llm_failure(
    mock_retrieve,
    mock_web_search,
    mock_image_search,
    mock_video_search,
    mock_llm_client,
):
    mock_retrieve.return_value = [
        {
            "filename": "doc.txt",
            "content": "Some content",
        }
    ]

    mock_web_search.return_value = []
    mock_image_search.return_value = []
    mock_video_search.return_value = []

    mock_llm_client.generate_json.side_effect = (
        LLMClientError("timeout")
    )

    with pytest.raises(ResearcherError):
        run_researcher(_make_task())


@patch("app.agents.researcher.llm_client")
@patch("app.agents.researcher.video_search")
@patch("app.agents.researcher.image_search")
@patch("app.agents.researcher.web_search")
@patch("app.agents.researcher.retrieve")
def test_run_researcher_skips_malformed_evidence(
    mock_retrieve,
    mock_web_search,
    mock_image_search,
    mock_video_search,
    mock_llm_client,
):
    mock_retrieve.return_value = [
        {
            "filename": "doc.txt",
            "content": "Some content",
        }
    ]

    mock_web_search.return_value = []
    mock_image_search.return_value = []
    mock_video_search.return_value = []

    mock_llm_client.generate_json.return_value = {
        "evidence": [
            {
                "claim": "",
                "source_title": "doc.txt",
            },
            {
                "claim": "Valid claim",
                "source_title": "doc.txt",
                "type": "evidence",
                "confidence": "high",
            },
        ],
        "gaps": [],
    }

    evidence, images, videos = run_researcher(
        _make_task()
    )

    assert len(evidence) == 1
    assert evidence[0].claim == "Valid claim"


@patch("app.agents.researcher.llm_client")
@patch("app.agents.researcher.video_search")
@patch("app.agents.researcher.image_search")
@patch("app.agents.researcher.web_search")
@patch("app.agents.researcher.retrieve")
def test_run_researcher_defaults_unknown_type_to_assumption(
    mock_retrieve,
    mock_web_search,
    mock_image_search,
    mock_video_search,
    mock_llm_client,
):
    mock_retrieve.return_value = [
        {
            "filename": "doc.txt",
            "content": "Some content",
        }
    ]

    mock_web_search.return_value = []
    mock_image_search.return_value = []
    mock_video_search.return_value = []

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

    evidence, images, videos = run_researcher(
        _make_task()
    )

    assert evidence[0].type == EvidenceType.ASSUMPTION


@patch("app.agents.researcher.llm_client")
@patch("app.agents.researcher.video_search")
@patch("app.agents.researcher.image_search")
@patch("app.agents.researcher.web_search")
@patch("app.agents.researcher.retrieve")
def test_run_researcher_returns_images(
    mock_retrieve,
    mock_web_search,
    mock_image_search,
    mock_video_search,
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

    mock_image_search.return_value = [
        {
            "url": "https://example.com/img.png",
            "description": "An image",
        }
    ]

    mock_video_search.return_value = []

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

    evidence, images, videos = run_researcher(
        _make_task()
    )

    assert len(images) == 1
    assert images[0]["url"] == (
        "https://example.com/img.png"
    )


@patch("app.agents.researcher.llm_client")
@patch("app.agents.researcher.video_search")
@patch("app.agents.researcher.image_search")
@patch("app.agents.researcher.web_search")
@patch("app.agents.researcher.retrieve")
def test_run_researcher_returns_videos(
    mock_retrieve,
    mock_web_search,
    mock_image_search,
    mock_video_search,
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

    mock_image_search.return_value = []

    mock_video_search.return_value = [
        {
            "title": "Video by Jane",
            "url": "https://pexels.com/video/1",
            "preview_video_url": (
                "https://videos.pexels.com/1.mp4"
            ),
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

    evidence, images, videos = run_researcher(
        _make_task()
    )

    assert len(videos) == 1
    assert videos[0]["title"] == "Video by Jane"
