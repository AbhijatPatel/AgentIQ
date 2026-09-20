
"""
YouTube video search (no API key required).

Uses the ``youtube-search-python`` library which scrapes YouTube's
public search interface.  This keeps the project free from any
YouTube API quota concerns.

Temporary network failures are automatically retried with
exponential back-off (via the shared ``retry_with_backoff`` helper).
"""

from __future__ import annotations

try:
    from youtubesearchpython import VideosSearch
except ImportError:
    VideosSearch = None

from app.utils.logger import get_logger
from app.utils.retry import retry_with_backoff

logger = get_logger(__name__)


class YouTubeSearchError(Exception):
    """Raised when a YouTube search fails to return usable results."""


@retry_with_backoff(
    max_retries=2,
    initial_delay=1.0,
)
def youtube_search(
    query: str,
    max_results: int = 4,
) -> list[dict]:
    """
    Search YouTube for videos matching *query*.

    No API key is required — the library scrapes YouTube's public
    search page.

    Returns:
        A list of dictionaries, each containing:
            - title         (str)  : video title
            - url           (str)  : full YouTube watch URL
            - thumbnail     (str)  : high-res thumbnail URL
            - channel       (str)  : channel / uploader name
            - duration      (str)  : human-readable duration (e.g. "12:34")
            - views         (str)  : view count text (e.g. "1.2M views")
            - published     (str)  : relative publish time (e.g. "3 days ago")
            - video_id      (str)  : YouTube video ID (for embedding)
            - embed_url     (str)  : iframe-ready embed URL
            - source        (str)  : always "youtube"

    Raises:
        YouTubeSearchError: on final failure after retries.
    """
    if not query or not query.strip():
        logger.warning(
            "Empty query passed to youtube_search(); "
            "returning no results."
        )
        return []

    if VideosSearch is None:
        logger.warning("youtubesearchpython is not installed; returning no YouTube results.")
        return []

    logger.info(f"YouTube search: {query!r}")

    try:
        search = VideosSearch(query, limit=max_results)
        response = search.result()
    except Exception as exc:
        logger.error(f"YouTube search failed: {exc}")
        raise YouTubeSearchError(
            f"YouTube search failed: {exc}"
        ) from exc

    raw_videos = response.get("result", [])

    if not raw_videos:
        logger.info(f"No YouTube results for query: {query!r}")
        return []

    formatted: list[dict] = []

    for video in raw_videos:
        video_id = video.get("id", "")

        # Pick the best available thumbnail
        thumbnails = video.get("thumbnails", [])
        thumbnail_url = (
            thumbnails[-1].get("url") if thumbnails else ""
        )

        formatted.append(
            {
                "title": video.get("title", "Untitled"),
                "url": video.get("link", f"https://www.youtube.com/watch?v={video_id}"),
                "thumbnail": thumbnail_url,
                "channel": (
                    video.get("channel", {}).get("name", "Unknown")
                ),
                "duration": video.get("duration", ""),
                "views": (
                    video.get("viewCount", {}).get("short", "")
                    if isinstance(video.get("viewCount"), dict)
                    else str(video.get("viewCount", ""))
                ),
                "published": video.get("publishedTime", ""),
                "video_id": video_id,
                "embed_url": f"https://www.youtube.com/embed/{video_id}",
                "source": "youtube",
            }
        )

    logger.info(
        f"YouTube search returned "
        f"{len(formatted)} videos for: {query!r}"
    )

    return formatted
