"""
Writer Agent.

Takes the user's goal, the Planner's tasks, and the Researcher's
evidence, and produces a structured research report.

The Writer must primarily use the collected evidence and must not
invent citations - if evidence is thin, it says so explicitly in the
"limitations" section instead of fabricating.
"""

from __future__ import annotations

from typing import Optional

from app.config.settings import settings
from app.graph.state import ConfidenceLevel, DraftReport, Evidence, Source, Task
from app.llm.client import llm_client, LLMClientError
from app.llm.prompts import WRITER_SYSTEM_PROMPT, writer_user_prompt
from app.utils.citation_engine import format_source_catalog_for_prompt
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WriterError(Exception):
    """Raised when the Writer agent cannot produce a valid draft report."""


REQUIRED_SECTIONS = [
    "title",
    "executive_summary",
    "introduction",
    "findings",
    "analysis",
    "limitations",
    "conclusion",
]

# Confidence priority used when ranking evidence for truncation.
_CONFIDENCE_RANK: dict[str, int] = {
    ConfidenceLevel.HIGH.value: 0,
    ConfidenceLevel.MEDIUM.value: 1,
    ConfidenceLevel.LOW.value: 2,
}


def select_evidence_for_writer(
    evidence: list[Evidence],
    max_items: int | None = None,
) -> list[Evidence]:
    """
    Select the highest-value evidence items for the Writer prompt.

    Evidence is ranked by confidence (high > medium > low) then by
    original order within the same confidence band, so items from the
    Researcher are stable and predictable.

    Only the *Writer's input copy* is trimmed. The original list stored
    in the session/database is never mutated.

    Args:
        evidence: Full evidence list from the Researcher.
        max_items: Hard cap on items returned. Defaults to
                   ``settings.MAX_EVIDENCE_FOR_WRITER``.

    Returns:
        A (possibly shorter) list of Evidence objects.
    """
    limit = max_items if max_items is not None else settings.MAX_EVIDENCE_FOR_WRITER
    total = len(evidence)

    if total <= limit:
        logger.info(
            "Writer evidence: using all %d item(s) (limit=%d)",
            total,
            limit,
        )
        return list(evidence)

    ranked = sorted(
        enumerate(evidence),
        key=lambda idx_ev: (
            _CONFIDENCE_RANK.get(idx_ev[1].confidence.value, 3),
            idx_ev[0],   # stable tiebreak: preserve original order
        ),
    )
    selected = [ev for _, ev in ranked[:limit]]

    logger.warning(
        "Writer evidence truncated: original=%d  selected=%d  configured_max=%d "
        "(high confidence items prioritised). "
        "Original evidence stored in DB is unchanged.",
        total,
        len(selected),
        limit,
    )
    return selected


def _tasks_to_dicts(tasks: list[Task]) -> list[dict]:
    return [{"description": t.description} for t in tasks]


def _evidence_to_dicts(evidence: list[Evidence]) -> list[dict]:
    return [
        {
            "claim": e.claim,
            "source_title": e.source_title,
            "type": e.type.value,
            "confidence": e.confidence.value,
        }
        for e in evidence
    ]


def _parse_references(raw_references: list) -> list[Source]:
    """
    Convert raw reference dicts from the LLM into validated Source objects.
    Malformed entries (missing title) are skipped rather than failing
    the whole report.
    """
    sources: list[Source] = []
    for ref in raw_references:
        if not isinstance(ref, dict):
            continue
        title = ref.get("title", "").strip() if ref.get("title") else ""
        if not title:
            continue
        sources.append(Source(title=title, url=ref.get("url")))
    return sources


def _sources_to_pydantic(sources_data: list) -> list[Source]:
    """Convert raw source dicts (from state) back into Source objects."""
    result: list[Source] = []
    for s in sources_data:
        if isinstance(s, Source):
            result.append(s)
        elif isinstance(s, dict):
            try:
                result.append(Source(**s))
            except Exception:
                continue
    return result


def run_writer(
    user_goal: str,
    tasks: list[Task],
    evidence: list[Evidence],
    sources: Optional[list] = None,
) -> DraftReport:
    """
    Run the Writer agent to produce a draft report.

    Args:
        user_goal: The original high-level user goal.
        tasks: List of Task objects from the Planner.
        evidence: List of Evidence objects from the Researcher.
        sources: Optional list of Source objects/dicts from the citation engine.

    Returns:
        A validated DraftReport.

    Raises:
        WriterError: if the LLM call fails or returns an unusable response.
    """
    logger.info(f"Writer started for goal: {user_goal!r} with {len(evidence)} evidence items")

    # Trim evidence to the configured limit BEFORE building the LLM prompt
    # to prevent HTTP 413 "request too large" on small-TPM fallback models.
    # The original evidence list (stored in DB / session) is NOT mutated.
    prompt_evidence = select_evidence_for_writer(evidence)

    if not prompt_evidence:
        logger.warning(
            "Writer running with NO evidence - report will need to state this "
            "as a limitation rather than inventing content."
        )

    # Build source catalog for the prompt if real sources are available
    source_objects = _sources_to_pydantic(sources or [])
    source_catalog = format_source_catalog_for_prompt(source_objects) if source_objects else ""

    try:
        raw_response = llm_client.generate_json(
            prompt=writer_user_prompt(
                user_goal=user_goal,
                tasks=_tasks_to_dicts(tasks),
                evidence=_evidence_to_dicts(prompt_evidence),
                source_catalog=source_catalog,
            ),
            system=WRITER_SYSTEM_PROMPT,
        )
    except LLMClientError as exc:
        logger.error(f"Writer LLM call failed: {exc}")
        raise WriterError(f"Writer failed to generate report: {exc}") from exc

    missing_sections = [s for s in REQUIRED_SECTIONS if not raw_response.get(s)]
    if missing_sections:
        raise WriterError(
            f"Writer response is missing required sections: {missing_sections}"
        )

    # Use real numbered sources as references when available,
    # falling back to LLM-generated references otherwise
    if source_objects:
        references = source_objects
        logger.info(f"Writer using {len(references)} real sources as references")
    else:
        references = _parse_references(raw_response.get("references", []))
        logger.info(f"Writer using {len(references)} LLM-generated references (no source catalog)")

    draft = DraftReport(
        title=raw_response["title"],
        executive_summary=raw_response["executive_summary"],
        introduction=raw_response["introduction"],
        findings=raw_response["findings"],
        analysis=raw_response["analysis"],
        limitations=raw_response["limitations"],
        conclusion=raw_response["conclusion"],
        references=references,
    )

    logger.info(f"Writer completed draft: {draft.title!r} with {len(references)} references")
    return draft