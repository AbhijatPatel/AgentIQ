
"""
Security and input validation utilities.

Provides reusable validation and sanitization helpers for protecting
AgentIQ from invalid, oversized, and potentially unsafe user input.
"""

from __future__ import annotations

import re

from app.utils.logger import get_logger

logger = get_logger(__name__)

MAX_QUERY_LENGTH = 2000
MIN_QUERY_LENGTH = 1

CONTROL_CHARACTER_PATTERN = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]"
)


class SecurityValidationError(ValueError):
    """Raised when user input fails security validation."""


def sanitize_text(value: str) -> str:
    """
    Remove dangerous control characters and normalize whitespace.

    Args:
        value: Input text.

    Returns:
        Cleaned text.
    """
    if not isinstance(value, str):
        raise SecurityValidationError(
            "Input must be a string."
        )

    cleaned = CONTROL_CHARACTER_PATTERN.sub("", value)
    cleaned = " ".join(cleaned.split())

    return cleaned.strip()


def validate_query(
    query: str,
    max_length: int = MAX_QUERY_LENGTH,
) -> str:
    """
    Validate and sanitize a research query.

    Args:
        query: User-provided research query.
        max_length: Maximum allowed query length.

    Returns:
        Sanitized query.

    Raises:
        SecurityValidationError:
            If the query is invalid or exceeds the size limit.
    """
    if not isinstance(query, str):
        raise SecurityValidationError(
            "Research query must be a string."
        )

    cleaned = sanitize_text(query)

    if len(cleaned) < MIN_QUERY_LENGTH:
        raise SecurityValidationError(
            "Research query cannot be empty."
        )

    if len(cleaned) > max_length:
        raise SecurityValidationError(
            f"Research query cannot exceed "
            f"{max_length} characters."
        )

    return cleaned


def validate_url(url: str) -> str:
    """
    Perform basic URL validation.

    Only HTTP and HTTPS URLs are accepted.

    Args:
        url: URL to validate.

    Returns:
        Sanitized URL.

    Raises:
        SecurityValidationError:
            If the URL is invalid or uses an unsafe scheme.
    """
    if not isinstance(url, str):
        raise SecurityValidationError(
            "URL must be a string."
        )

    cleaned = url.strip()

    if not cleaned:
        raise SecurityValidationError(
            "URL cannot be empty."
        )

    lowered = cleaned.lower()

    if not (
        lowered.startswith("https://")
        or lowered.startswith("http://")
    ):
        raise SecurityValidationError(
            "Only HTTP and HTTPS URLs are allowed."
        )

    if any(char.isspace() for char in cleaned):
        raise SecurityValidationError(
            "URL cannot contain whitespace."
        )

    return cleaned
