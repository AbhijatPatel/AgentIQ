"""
Tests for the image search tool (built on Tavily's include_images option).
"""

from unittest.mock import MagicMock, patch

import pytest

from app.tools.web_search import image_search, WebSearchError


@patch("app.tools.web_search._get_client")
def test_image_search_returns_formatted_results(mock_get_client):
    mock_client = MagicMock()
    mock_client.search.return_value = {
        "images": [
            {"url": "https://example.com/diagram.png", "description": "Architecture diagram"},
            {"url": "https://example.com/chart.png", "description": "Growth chart"},
        ]
    }
    mock_get_client.return_value = mock_client

    results = image_search("AI agent architecture")

    assert len(results) == 2
    assert results[0]["url"] == "https://example.com/diagram.png"
    assert results[0]["description"] == "Architecture diagram"


@patch("app.tools.web_search._get_client")
def test_image_search_returns_empty_list_when_no_images(mock_get_client):
    mock_client = MagicMock()
    mock_client.search.return_value = {"images": []}
    mock_get_client.return_value = mock_client

    results = image_search("an extremely obscure query")

    assert results == []


def test_image_search_returns_empty_list_for_empty_query():
    assert image_search("") == []
    assert image_search("   ") == []


@patch("app.tools.web_search._get_client")
def test_image_search_skips_images_without_url(mock_get_client):
    mock_client = MagicMock()
    mock_client.search.return_value = {
        "images": [
            {"url": None, "description": "Broken entry"},
            {"url": "https://example.com/valid.png", "description": "Valid image"},
        ]
    }
    mock_get_client.return_value = mock_client

    results = image_search("some query")

    assert len(results) == 1
    assert results[0]["url"] == "https://example.com/valid.png"


@patch("app.tools.web_search._get_client")
def test_image_search_raises_on_unexpected_error(mock_get_client):
    mock_client = MagicMock()
    mock_client.search.side_effect = RuntimeError("connection reset")
    mock_get_client.return_value = mock_client

    with pytest.raises(WebSearchError):
        image_search("some query")


@patch("app.tools.web_search._get_client")
def test_image_search_handles_missing_description(mock_get_client):
    mock_client = MagicMock()
    mock_client.search.return_value = {
        "images": [{"url": "https://example.com/img.png"}]
    }
    mock_get_client.return_value = mock_client

    results = image_search("some query")

    assert results[0]["description"] == ""