
"""
Web search tools.

Wraps the Tavily API so the Researcher agent has access to
real-time web search.

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

