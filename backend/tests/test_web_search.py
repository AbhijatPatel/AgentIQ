"""
Tests for the web search tool.

We mock the TavilyClient so these tests run instantly and free,
without using real API credits.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.tools.web_search import web_search, WebSearchError


@patch("app.tools.web_search._get_client")
def test_web_search_returns_formatted_results(mock_get_client):
    mock_client = MagicMock()
    mock_client.search.return_value = {
        "results": [
            {
                "title": "AI Adoption Report",
                "url": "https://example.com/ai-report",
                "content": "AI adoption grew significantly in 2026.",
                "published_date": "2026-01-15",
            }
        ]
    }
    mock_get_client.return_value = mock_client

    results = web_search("AI adoption statistics")

    assert len(results) == 1
    assert results[0]["title"] == "AI Adoption Report"
    assert results[0]["source"] == "example.com"
    assert results[0]["published_date"] == "2026-01-15"


@patch("app.tools.web_search._get_client")
def test_web_search_returns_empty_list_when_no_results(mock_get_client):
    mock_client = MagicMock()
    mock_client.search.return_value = {"results": []}
    mock_get_client.return_value = mock_client

    results = web_search("an extremely obscure query with no matches")

    assert results == []


def test_web_search_returns_empty_list_for_empty_query():
    assert web_search("") == []
    assert web_search("   ") == []


@patch("app.tools.web_search._get_client")
def test_web_search_raises_on_unexpected_error(mock_get_client):
    mock_client = MagicMock()
    mock_client.search.side_effect = RuntimeError("connection reset")
    mock_get_client.return_value = mock_client

    with pytest.raises(WebSearchError):
        web_search("some query")


@patch("app.tools.web_search.settings")
def test_get_client_raises_when_api_key_missing(mock_settings):
    mock_settings.TAVILY_API_KEY = ""

    with pytest.raises(WebSearchError):
        web_search("some query")


@patch("app.tools.web_search._get_client")
def test_web_search_handles_missing_optional_fields(mock_get_client):
    mock_client = MagicMock()
    mock_client.search.return_value = {
        "results": [{"title": "No date result", "url": "https://noDate.com"}]
    }
    mock_get_client.return_value = mock_client

    results = web_search("some query")

    assert results[0]["published_date"] is None
    assert results[0]["content"] == ""