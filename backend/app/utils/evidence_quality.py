
"""
Evidence quality utilities.

Filters invalid evidence items before they are passed to
downstream research and writing agents.
"""

from __future__ import annotations

from app.graph.state import Evidence
from app.utils.logger import get_logger

logger = get_logger(__name__)


def filter_valid_evidence(
    evidence: list[Evidence],
) -> list[Evidence]:
    """
    Keep only evidence items containing meaningful required fields.

    An evidence item is considered valid when it has:
        - a non-empty claim
        - a non-empty source title
        - a valid confidence value
    """
    valid: list[Evidence] = []

    for item in evidence:
        claim = item.claim.strip() if item.claim else ""
        source_title = (
            item.source_title.strip()
            if item.source_title
            else ""
        )

        if not claim:
            logger.warning(
                "Discarding evidence item with empty claim."
            )
            continue

        if not source_title:
            logger.warning(
                "Discarding evidence item with empty source title."
            )
            continue

        valid.append(item)

    removed_count = len(evidence) - len(valid)

    if removed_count > 0:
        logger.info(
            f"Evidence quality filter removed "
            f"{removed_count} invalid evidence items"
        )

    return valid

