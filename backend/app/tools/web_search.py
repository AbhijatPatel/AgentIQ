"""
Web search tool.

Wraps the Tavily API so the Researcher agent has a second information
source alongside RAG. Tavily is built for AI agents - it returns
clean, structured results instead of raw HTML.
"""

from __future__ import annotations

import requests

from tavily import TavilyClient
from tavily.errors import (
    BadRequestError,
    UsageLimitExceededError,
)

from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WebSearchError(Exception):
    """Raised when the web search tool fails to return usable results."""


def _get_client() -> TavilyClient:
    if not settings.TAVILY_API_KEY:
        raise WebSearchError(
            "TAVILY_API_KEY is not set. Add it to your .env file."
        )
    return TavilyClient(api_key=settings.TAVILY_API_KEY)


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web for a query and return structured results.

    Args:
        query: The research query to search for.
        max_results: Maximum number of results to return.

    Returns:
        A list of dicts, each with:
            - title: page title
            - url: page URL
            - content: snippet/extracted content
            - source: domain the result came from
            - published_date: ISO date string, or None if unavailable

        Returns an empty list if the query is empty or no results are found.
        Never fabricates results - if Tavily returns nothing, we return nothing.

    Raises:
        WebSearchError: on auth failure, rate limiting, or unexpected errors.
    """
    if not query or not query.strip():
        logger.warning("Empty query passed to web_search(); returning no results.")
        return []

    logger.info(f"Web search: {query!r}")

    try:
        client = _get_client()
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",
        )
    except UsageLimitExceededError as exc:
        logger.error(f"Tavily rate/usage limit exceeded: {exc}")
        raise WebSearchError("Web search rate limit reached. Please wait and retry.") from exc
    except BadRequestError as exc:
        logger.error(f"Tavily bad request: {exc}")
        raise WebSearchError(f"Web search request was invalid: {exc}") from exc
    except WebSearchError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Unexpected web search error: {exc}")
        raise WebSearchError(f"Web search failed: {exc}") from exc

    raw_results = response.get("results", [])
    if not raw_results:
        logger.info(f"No web results found for query: {query!r}")
        return []

    formatted = [
        {
            "title": item.get("title", "Untitled"),
            "url": item.get("url"),
            "content": item.get("content", ""),
            "source": _extract_domain(item.get("url")),
            "published_date": item.get("published_date"),
        }
        for item in raw_results
    ]

    logger.info(f"Web search returned {len(formatted)} results for: {query!r}")
    return formatted


def _extract_domain(url: str | None) -> str | None:
    """Extract a readable domain from a URL, e.g. 'https://x.com/a' -> 'x.com'."""
    if not url:
        return None
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc or None
    except Exception:  # noqa: BLE001
        return None

def image_search(query: str, max_results: int = 6) -> list[dict]:
    """
    Search for images related to a query using Tavily's include_images option.

    Returns a list of dicts, each with:
        - url: direct image URL
        - description: short description of the image, if available
        - source_query: the query that found it (useful for grouping)

    Returns an empty list if the query is empty or no images are found.
    Never fabricates image URLs - only returns what Tavily actually found.

    Raises:
        WebSearchError: on auth failure, rate limiting, or unexpected errors.
    """
    if not query or not query.strip():
        logger.warning("Empty query passed to image_search(); returning no results.")
        return []

    logger.info(f"Image search: {query!r}")

    try:
        client = _get_client()
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",
            include_images=True,
            include_image_descriptions=True,
        )
    except UsageLimitExceededError as exc:
        logger.error(f"Tavily rate/usage limit exceeded: {exc}")
        raise WebSearchError("Image search rate limit reached. Please wait and retry.") from exc
    except BadRequestError as exc:
        logger.error(f"Tavily bad request: {exc}")
        raise WebSearchError(f"Image search request was invalid: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Unexpected image search error: {exc}")
        raise WebSearchError(f"Image search failed: {exc}") from exc

    raw_images = response.get("images", [])
    if not raw_images:
        logger.info(f"No images found for query: {query!r}")
        return []

    formatted = [
        {
            "url": img.get("url"),
            "description": img.get("description") or "",
        }
        for img in raw_images
        if img.get("url")
    ]

    logger.info(f"Image search returned {len(formatted)} images for: {query!r}")
    return formatted

PEXELS_VIDEO_SEARCH_URL = "https://api.pexels.com/videos/search"


def video_search(query: str, max_results: int = 4) -> list[dict]:
    """
    Search for videos related to a query using the Pexels Video API.

    Note: Pexels provides stock/b-roll footage, not topical educational
    content - results are keyword-matched generic video clips, useful
    as visual accompaniment rather than direct topical relevance.

    Returns a list of dicts, each with:
        - title: a generated label (Pexels videos have no titles, so
          we use the photographer/user name as attribution)
        - url: link to the video page on Pexels
        - thumbnail: preview image URL
        - preview_video_url: direct playable video file URL (small size)

    Returns an empty list if the query is empty, no API key is set,
    or no videos are found.

    Raises:
        WebSearchError: on auth failure, rate limiting, or unexpected errors.
    """
    if not query or not query.strip():
        logger.warning("Empty query passed to video_search(); returning no results.")
        return []

    if not settings.PEXELS_API_KEY:
        logger.warning("PEXELS_API_KEY is not set; skipping video search.")
        return []

    logger.info(f"Video search: {query!r}")

    try:
        response = requests.get(
            PEXELS_VIDEO_SEARCH_URL,
            headers={"Authorization": settings.PEXELS_API_KEY},
            params={"query": query, "per_page": max_results},
            timeout=10,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        if response.status_code == 429:
            logger.error(f"Pexels rate limit exceeded: {exc}")
            raise WebSearchError("Video search rate limit reached. Please wait and retry.") from exc
        logger.error(f"Pexels API HTTP error: {exc}")
        raise WebSearchError(f"Video search request failed: {exc}") from exc
    except requests.exceptions.RequestException as exc:
        logger.error(f"Unexpected video search error: {exc}")
        raise WebSearchError(f"Video search failed: {exc}") from exc

    data = response.json()
    videos = data.get("videos", [])

    if not videos:
        logger.info(f"No videos found for query: {query!r}")
        return []

    formatted = []
    for video in videos:
        video_files = video.get("video_files", [])
        small_file = next((f for f in video_files if f.get("quality") == "sd"), None)
        preview_url = small_file.get("link") if small_file else (
            video_files[0].get("link") if video_files else None
        )
        formatted.append(
            {
                "title": f"Video by {video.get('user', {}).get('name', 'Pexels')}",
                "url": video.get("url"),
                "thumbnail": video.get("image"),
                "preview_video_url": preview_url,
            }
        )

    logger.info(f"Video search returned {len(formatted)} videos for: {query!r}")
    return formatted