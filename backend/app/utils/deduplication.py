
"""
Research result deduplication utilities.

Removes duplicate web, image, and video results while preserving
the original order of the results.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TypeVar

from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def deduplicate_by_key(
    items: Iterable[T],
    key_func: Callable[[T], object],
) -> list[T]:
    """
    Remove duplicate items using a key function.

    The first occurrence of each unique key is preserved.

    Args:
        items: Iterable of items to deduplicate.
        key_func: Function that returns a comparison key.

    Returns:
        Deduplicated list preserving original order.
    """
    items_list = list(items)

    seen: set[str] = set()
    unique_items: list[T] = []

    for item in items_list:
        key = key_func(item)

        if not key:
            unique_items.append(item)
            continue

        normalized_key = str(key).strip().lower()

        if normalized_key in seen:
            continue

        seen.add(normalized_key)
        unique_items.append(item)

    removed_count = len(items_list) - len(unique_items)

    if removed_count > 0:
        logger.info(
            f"Deduplication removed {removed_count} duplicate results"
        )

    return unique_items


def deduplicate_web_results(
    results: list[dict],
) -> list[dict]:
    """
    Remove duplicate web results using their URL.
    """
    return deduplicate_by_key(
        results,
        lambda item: item.get("url"),
    )


def deduplicate_image_results(
    results: list[dict],
) -> list[dict]:
    """
    Remove duplicate image results using their image URL.
    """
    return deduplicate_by_key(
        results,
        lambda item: item.get("url"),
    )


def deduplicate_video_results(
    results: list[dict],
) -> list[dict]:
    """
    Remove duplicate video results using their video page URL.
    """
    return deduplicate_by_key(
        results,
        lambda item: item.get("url"),
    )
