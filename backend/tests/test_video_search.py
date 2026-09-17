"""
Tests for the video search tool (Pexels Video API).
"""

from unittest.mock import MagicMock, patch

import pytest

from app.tools.web_search import video_search, WebSearchError


def _mock_response(videos):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"videos": videos}
    return mock_resp


@patch("app.tools.web_search.settings")
@patch("app.tools.web_search.requests.get")
def test_video_search_returns_formatted_results(mock_get, mock_settings):
    mock_settings.PEXELS_API_KEY = "fake-key"
    mock_get.return_value = _mock_response(
        [
            {
                "url": "https://pexels.com/video/123",
                "image": "https://images.pexels.com/thumb.jpg",
                "user": {"name": "Jane Doe"},
                "video_files": [{"quality": "sd", "link": "https://videos.pexels.com/123.mp4"}],
            }
        ]
    )

    results = video_search("technology")

    assert len(results) == 1
    assert results[0]["title"] == "Video by Jane Doe"
    assert results[0]["preview_video_url"] == "https://videos.pexels.com/123.mp4"


@patch("app.tools.web_search.settings")
def test_video_search_returns_empty_when_no_api_key(mock_settings):
    mock_settings.PEXELS_API_KEY = ""

    results = video_search("some query")

    assert results == []


def test_video_search_returns_empty_for_empty_query():
    assert video_search("") == []
    assert video_search("   ") == []


@patch("app.tools.web_search.settings")
@patch("app.tools.web_search.requests.get")
def test_video_search_returns_empty_when_no_videos(mock_get, mock_settings):
    mock_settings.PEXELS_API_KEY = "fake-key"
    mock_get.return_value = _mock_response([])

    results = video_search("an extremely obscure query")

    assert results == []


@patch("app.tools.web_search.settings")
@patch("app.tools.web_search.requests.get")
def test_video_search_raises_on_rate_limit(mock_get, mock_settings):
    import requests

    mock_settings.PEXELS_API_KEY = "fake-key"
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_resp)
    mock_get.return_value = mock_resp

    with pytest.raises(WebSearchError):
        video_search("some query")


@patch("app.tools.web_search.settings")
@patch("app.tools.web_search.requests.get")
def test_video_search_falls_back_to_first_file_if_no_sd(mock_get, mock_settings):
    mock_settings.PEXELS_API_KEY = "fake-key"
    mock_get.return_value = _mock_response(
        [
            {
                "url": "https://pexels.com/video/456",
                "image": "https://images.pexels.com/thumb2.jpg",
                "user": {"name": "John Smith"},
                "video_files": [{"quality": "hd", "link": "https://videos.pexels.com/456.mp4"}],
            }
        ]
    )

    results = video_search("some query")

    assert results[0]["preview_video_url"] == "https://videos.pexels.com/456.mp4"