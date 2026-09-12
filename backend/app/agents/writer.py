"""
Writer Agent.

Takes the user's goal, the Planner's tasks, and the Researcher's
evidence, and produces a structured research report.

The Writer must primarily use the collected evidence and must not
invent citations - if evidence is thin, it says so explicitly in the
"limitations" section instead of fabricating.
"""

from __future__ import annotations

from app.graph.state import DraftReport, Evidence, Source, Task
from app.llm.client import llm_client, LLMClientError
from app.llm.prompts import WRITER_SYSTEM_PROMPT, writer_user_prompt
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


def run_writer(user_goal: str, tasks: list[Task], evidence: list[Evidence]) -> DraftReport:
    """
    Run the Writer agent to produce a draft report.

    Args:
        user_goal: The original high-level user goal.
        tasks: List of Task objects from the Planner.
        evidence: List of Evidence objects from the Researcher.

    Returns:
        A validated DraftReport.

    Raises:
        WriterError: if the LLM call fails or returns an unusable response.
    """
    logger.info(f"Writer started for goal: {user_goal!r} with {len(evidence)} evidence items")

    if not evidence:
        logger.warning(
            "Writer running with NO evidence - report will need to state this "
            "as a limitation rather than inventing content."
        )

    try:
        raw_response = llm_client.generate_json(
            prompt=writer_user_prompt(
                user_goal=user_goal,
                tasks=_tasks_to_dicts(tasks),
                evidence=_evidence_to_dicts(evidence),
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

    references = _parse_references(raw_response.get("references", []))

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