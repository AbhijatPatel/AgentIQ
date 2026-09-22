"""
YouTube video search using official YouTube Data API v3 direct HTTP requests.

Features:
- Official YouTube Data API v3 (no scraper dependency, eliminating proxies/httpx errors)
- Strict non-blocking execution: YouTube errors, quotas, or missing keys never fail the research pipeline
- API key masking: Never logs or exposes the YouTube API key
- Clean schema output matching frontend VideoGallery component
"""

from __future__ import annotations

import requests

from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


class YouTubeSearchError(Exception):
    """Raised when a YouTube search fails unexpectedly."""


def youtube_search(
    query: str,
    max_results: int = 3,
) -> list[dict]:
    """
    Search YouTube for relevant educational/technical videos using YouTube Data API v3.

    Returns:
        List of video dicts containing:
        - title
        - url
        - thumbnail
        - channel
        - description
        - published
        - video_id
        - embed_url
        - source ("youtube")
    """
    clean_query = (query or "").strip()
    if not clean_query:
        return []

    api_key = settings.YOUTUBE_API_KEY.strip()
    if not api_key:
        logger.info("YOUTUBE_API_KEY is not configured; skipping YouTube search.")
        return []

    logger.info("Executing YouTube Data API v3 search for query: %s", clean_query[:50])

    try:
        params = {
            "part": "snippet",
            "q": clean_query,
            "maxResults": max_results,
            "type": "video",
            "key": api_key,
        }

        response = requests.get(
            YOUTUBE_SEARCH_URL,
            params=params,
            timeout=8.0,
        )

        if response.status_code == 403:
            logger.warning("YouTube Data API quota reached or key restricted (status 403). Skipping video search.")
            return []

        if response.status_code != 200:
            logger.warning("YouTube Data API returned status %d. Skipping video search.", response.status_code)
            return []

        data = response.json()
        items = data.get("items", [])
        if not items:
            logger.info("No YouTube videos found for query: %s", clean_query[:50])
            return []

        formatted: list[dict] = []
        for item in items:
            id_info = item.get("id", {})
            video_id = id_info.get("videoId")
            if not video_id:
                continue

            snippet = item.get("snippet", {})
            thumbnails = snippet.get("thumbnails", {})
            thumb_url = (
                thumbnails.get("high", {}).get("url")
                or thumbnails.get("medium", {}).get("url")
                or thumbnails.get("default", {}).get("url")
                or ""
            )

            title = snippet.get("title", "YouTube Video")
            channel = snippet.get("channelTitle", "YouTube")
            description = snippet.get("description", "")
            published = snippet.get("publishedAt", "")

            formatted.append({
                "title": title,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "embed_url": f"https://www.youtube.com/embed/{video_id}",
                "thumbnail": thumb_url,
                "channel": channel,
                "description": description,
                "published": published,
                "video_id": video_id,
                "source": "youtube",
            })

        logger.info("YouTube search returned %d videos for query: %s", len(formatted), clean_query[:50])
        return formatted

    except requests.exceptions.Timeout:
        logger.warning("YouTube search timed out for query: %s", clean_query[:50])
        return []
    except Exception as exc:
        logger.warning("YouTube search non-blocking error: %s", exc)
        return []
