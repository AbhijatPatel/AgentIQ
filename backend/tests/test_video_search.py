"""
Tests for YouTube Data API v3 video search.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.tools.youtube_search import youtube_search, YouTubeSearchError


def _mock_yt_response(items):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"items": items}
    return mock_resp


@patch("app.tools.youtube_search.settings")
@patch("app.tools.youtube_search.requests.get")
def test_youtube_search_returns_formatted_results(mock_get, mock_settings):
    mock_settings.YOUTUBE_API_KEY = "valid-api-key"
    mock_get.return_value = _mock_yt_response(
        [
            {
                "id": {"videoId": "dQw4w9WgXcQ"},
                "snippet": {
                    "title": "Quantum Computing Explained",
                    "description": "A deep dive into quantum mechanics and algorithms.",
                    "channelTitle": "Physics Hub",
                    "publishedAt": "2024-01-01T00:00:00Z",
                    "thumbnails": {
                        "high": {"url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"}
                    },
                },
            }
        ]
    )

    results = youtube_search("quantum computing")

    assert len(results) == 1
    assert results[0]["title"] == "Quantum Computing Explained"
    assert results[0]["channel"] == "Physics Hub"
    assert results[0]["source"] == "youtube"
    assert results[0]["url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert results[0]["embed_url"] == "https://www.youtube.com/embed/dQw4w9WgXcQ"


@patch("app.tools.youtube_search.settings")
def test_youtube_search_returns_empty_when_no_api_key(mock_settings):
    mock_settings.YOUTUBE_API_KEY = ""
    results = youtube_search("some topic")
    assert results == []


def test_youtube_search_returns_empty_for_blank_query():
    assert youtube_search("") == []
    assert youtube_search("   ") == []


@patch("app.tools.youtube_search.settings")
@patch("app.tools.youtube_search.requests.get")
def test_youtube_search_handles_quota_exceeded(mock_get, mock_settings):
    mock_settings.YOUTUBE_API_KEY = "valid-api-key"
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.json.return_value = {
        "error": {
            "errors": [{"reason": "quotaExceeded"}],
            "message": "Quota exceeded",
        }
    }
    mock_get.return_value = mock_resp

    results = youtube_search("some topic")
    assert results == []