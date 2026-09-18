
"""
Prompt injection detection utilities.

Detects common attempts to override system instructions or manipulate
the AgentIQ research pipeline through user-provided prompts.
"""

from __future__ import annotations

import re

from app.utils.logger import get_logger

logger = get_logger(__name__)


class PromptInjectionError(ValueError):
    """Raised when a prompt contains a suspected injection pattern."""


PROMPT_INJECTION_PATTERNS = [
    r"\bignore\s+(all\s+)?previous\s+instructions\b",
    r"\bignore\s+(all\s+)?prior\s+instructions\b",
    r"\bignore\s+the\s+system\s+prompt\b",
    r"\bdisregard\s+(all\s+)?previous\s+instructions\b",
    r"\bdisregard\s+(all\s+)?prior\s+instructions\b",
    r"\bforget\s+(all\s+)?previous\s+instructions\b",
    r"\breveal\s+(the\s+)?system\s+prompt\b",
    r"\bshow\s+(me\s+)?(the\s+)?system\s+prompt\b",
    r"\bprint\s+(the\s+)?system\s+prompt\b",
    r"\bact\s+as\s+(a\s+)?system\b",
    r"\byou\s+are\s+now\s+(the\s+)?system\b",
    r"\bbypass\s+(the\s+)?instructions\b",
    r"\boverride\s+(the\s+)?instructions\b",
    r"\bdo\s+not\s+follow\s+(the\s+)?instructions\b",
]


_COMPILED_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in PROMPT_INJECTION_PATTERNS
]


def detect_prompt_injection(text: str) -> bool:
    """
    Detect common prompt injection patterns.

    Args:
        text: User-provided text.

    Returns:
        True if a suspicious instruction pattern is detected.
        False otherwise.
    """
    if not isinstance(text, str):
        return False

    normalized = " ".join(text.split())

    for pattern in _COMPILED_PATTERNS:
        if pattern.search(normalized):
            logger.warning(
                "Potential prompt injection detected in user input."
            )
            return True

    return False


def validate_prompt_safety(text: str) -> str:
    """
    Validate that user-provided text does not contain
    a known prompt injection pattern.

    Args:
        text: User-provided text.

    Returns:
        The original text when considered safe.

    Raises:
        PromptInjectionError:
            If a known injection pattern is detected.
    """
    if not isinstance(text, str):
        raise PromptInjectionError(
            "Prompt input must be a string."
        )

    if detect_prompt_injection(text):
        raise PromptInjectionError(
            "Potential prompt injection detected."
        )

    return text