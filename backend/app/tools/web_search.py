
"""
Web search tools.

Wraps the Tavily and Pexels APIs so the Researcher agent has access to
web, image, and video search.

Temporary external API failures are automatically retried with
exponential backoff.
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
from app.utils.retry import retry_with_backoff


logger = get_logger(__name__)


PEXELS_VIDEO_SEARCH_URL = "https://api.pexels.com/videos/search"


class WebSearchError(Exception):
    """Raised when a search tool fails to return usable results."""


def _get_client() -> TavilyClient:
    if not settings.TAVILY_API_KEY:
        raise WebSearchError(
            "TAVILY_API_KEY is not set. Add it to your .env file."
        )

    return TavilyClient(
        api_key=settings.TAVILY_API_KEY
    )


@retry_with_backoff(
    max_retries=2,
    initial_delay=1.0,
)
def web_search(
    query: str,
    max_results: int = 5,
) -> list[dict]:
    """
    Search the web using Tavily.

    Temporary unexpected failures are retried automatically.

    Returns:
        A list of dictionaries containing title, URL, content,
        source domain, and publication date.

    Raises:
        WebSearchError:
            When authentication, rate limiting, invalid requests,
            or final unexpected failures occur.
    """
    if not query or not query.strip():
        logger.warning(
            "Empty query passed to web_search(); "
            "returning no results."
        )
        return []

    logger.info(
        f"Web search: {query!r}"
    )

    try:
        client = _get_client()

        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",
        )

    except UsageLimitExceededError as exc:
        logger.error(
            f"Tavily rate/usage limit exceeded: {exc}"
        )

        raise WebSearchError(
            "Web search rate limit reached. "
            "Please wait and retry."
        ) from exc

    except BadRequestError as exc:
        logger.error(
            f"Tavily bad request: {exc}"
        )

        raise WebSearchError(
            f"Web search request was invalid: {exc}"
        ) from exc

    except WebSearchError:
        raise

    except Exception as exc:
        logger.error(
            f"Unexpected web search error: {exc}"
        )

        raise WebSearchError(
            f"Web search failed: {exc}"
        ) from exc

    raw_results = response.get(
        "results",
        [],
    )

    if not raw_results:
        logger.info(
            f"No web results found for query: {query!r}"
        )
        return []

    formatted = [
        {
            "title": item.get(
                "title",
                "Untitled",
            ),
            "url": item.get("url"),
            "content": item.get(
                "content",
                "",
            ),
            "source": _extract_domain(
                item.get("url")
            ),
            "published_date": item.get(
                "published_date"
            ),
        }
        for item in raw_results
    ]

    logger.info(
        f"Web search returned "
        f"{len(formatted)} results for: {query!r}"
    )

    return formatted


def _extract_domain(
    url: str | None,
) -> str | None:
    """
    Extract a readable domain from a URL.

    Example:
        https://example.com/page
        -> example.com
    """
    if not url:
        return None

    try:
        from urllib.parse import urlparse

        return urlparse(url).netloc or None

    except Exception:
        return None


@retry_with_backoff(
    max_retries=2,
    initial_delay=1.0,
)
def image_search(
    query: str,
    max_results: int = 6,
) -> list[dict]:
    """
    Search for images using Tavily.

    Temporary unexpected failures are retried automatically.

    Returns:
        A list of dictionaries containing image URLs and descriptions.

    Raises:
        WebSearchError:
            When authentication, rate limiting, invalid requests,
            or final unexpected failures occur.
    """
    if not query or not query.strip():
        logger.warning(
            "Empty query passed to image_search(); "
            "returning no results."
        )
        return []

    logger.info(
        f"Image search: {query!r}"
    )

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
        logger.error(
            f"Tavily rate/usage limit exceeded: {exc}"
        )

        raise WebSearchError(
            "Image search rate limit reached. "
            "Please wait and retry."
        ) from exc

    except BadRequestError as exc:
        logger.error(
            f"Tavily bad request: {exc}"
        )

        raise WebSearchError(
            f"Image search request was invalid: {exc}"
        ) from exc

    except WebSearchError:
        raise

    except Exception as exc:
        logger.error(
            f"Unexpected image search error: {exc}"
        )

        raise WebSearchError(
            f"Image search failed: {exc}"
        ) from exc

    raw_images = response.get(
        "images",
        [],
    )

    if not raw_images:
        logger.info(
            f"No images found for query: {query!r}"
        )
        return []

    formatted = [
        {
            "url": img.get("url"),
            "description": img.get(
                "description"
            ) or "",
        }
        for img in raw_images
        if img.get("url")
    ]

    logger.info(
        f"Image search returned "
        f"{len(formatted)} images for: {query!r}"
    )

    return formatted


@retry_with_backoff(
    max_retries=2,
    initial_delay=1.0,
)
def video_search(
    query: str,
    max_results: int = 4,
) -> list[dict]:
    """
    Search for videos using the Pexels Video API.

    Temporary network/API failures are retried automatically.

    Returns:
        A list of dictionaries containing title, URL, thumbnail,
        and playable preview video URL.

    Raises:
        WebSearchError:
            When the API request fails after retries.
    """
    if not query or not query.strip():
        logger.warning(
            "Empty query passed to video_search(); "
            "returning no results."
        )
        return []

    if not settings.PEXELS_API_KEY:
        logger.warning(
            "PEXELS_API_KEY is not set; "
            "skipping video search."
        )
        return []

    logger.info(
        f"Video search: {query!r}"
    )

    try:
        response = requests.get(
            PEXELS_VIDEO_SEARCH_URL,
            headers={
                "Authorization": settings.PEXELS_API_KEY
            },
            params={
                "query": query,
                "per_page": max_results,
            },
            timeout=10,
        )

        response.raise_for_status()

    except requests.exceptions.HTTPError as exc:
        if response.status_code == 429:
            logger.error(
                f"Pexels rate limit exceeded: {exc}"
            )

            raise WebSearchError(
                "Video search rate limit reached. "
                "Please wait and retry."
            ) from exc

        logger.error(
            f"Pexels API HTTP error: {exc}"
        )

        raise WebSearchError(
            f"Video search request failed: {exc}"
        ) from exc

    except requests.exceptions.RequestException as exc:
        logger.error(
            f"Unexpected video search error: {exc}"
        )

        raise WebSearchError(
            f"Video search failed: {exc}"
        ) from exc

    data = response.json()

    videos = data.get(
        "videos",
        [],
    )

    if not videos:
        logger.info(
            f"No videos found for query: {query!r}"
        )
        return []

    formatted = []

    for video in videos:
        video_files = video.get(
            "video_files",
            []
        )

        audio_file = next(
            (
                f
                for f in video_files
                if f.get("quality") == "sd"
                and f.get("has_audio") is True
            ),
            None,
        )

        small_file = next(
            (
                f
                for f in video_files
                if f.get("quality") == "sd"
            ),
            None,
        )

        preview_url = (
            audio_file.get("link")
            if audio_file
            else small_file.get("link")
            if small_file
            else video_files[0].get("link")
            if video_files
            else None
        )

        formatted.append(
            {
                "title": (
                    f"Video by "
                    f"{video.get('user', {}).get('name', 'Pexels')}"
                ),
                "url": video.get("url"),
                "thumbnail": video.get("image"),
                "preview_video_url": preview_url,
            }
        )

    logger.info(
        f"Video search returned "
        f"{len(formatted)} videos for: {query!r}"
    )

    return formatted

