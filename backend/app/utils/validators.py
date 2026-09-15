"""
Input validation and prompt-injection defense utilities.

Centralizes the security-relevant checks your master plan calls for:
- upload validation (already partially in documents.py, formalized here)
- basic prompt-injection pattern detection in retrieved content
- goal input sanitization
"""

from __future__ import annotations

import re

from app.utils.logger import get_logger

logger = get_logger(__name__)

INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"disregard (all )?(previous|prior|above) instructions",
    r"you are now",
    r"new instructions?:",
    r"system prompt:",
    r"\[system\]",
    r"act as (if )?you (are|were)",
    r"forget (everything|all) (you|that)",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def detect_injection_attempt(text: str) -> bool:
    """
    Returns True if text contains patterns commonly associated with
    prompt injection attempts. This is a heuristic, not a guarantee -
    used to flag/log suspicious content, not to silently rewrite it.
    """
    if not text:
        return False
    return any(pattern.search(text) for pattern in _COMPILED_PATTERNS)


def sanitize_retrieved_content(text: str, source_label: str = "unknown") -> str:
    """
    Checks retrieved content (web search results, RAG chunks) for
    injection attempts before it's included in an LLM prompt. Logs a
    warning if detected, but does NOT strip content - the Researcher
    prompt (Module 3) already instructs the LLM to treat this as data.
    This function's job is observability: knowing when it happens.
    """
    if detect_injection_attempt(text):
        logger.warning(
            f"Potential prompt injection pattern detected in content from '{source_label}'. "
            "Content is passed to the LLM as labeled untrusted data per prompt design."
        )
    return text


def validate_goal_input(goal: str) -> tuple[bool, str | None]:
    """
    Basic validation for user-submitted research goals, beyond
    Pydantic's length constraints (already enforced in schemas/request.py).

    Returns (is_valid, error_message).
    """
    if not goal or not goal.strip():
        return False, "Goal cannot be empty."

    if detect_injection_attempt(goal):
        logger.warning(f"Potential prompt injection pattern detected in user goal: {goal!r}")

    return True, None