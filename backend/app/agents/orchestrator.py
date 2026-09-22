"""
Self-critique revision loop.

Wires the Writer and Critic together: after the first draft, if the
Critic says "revise", the Writer gets another attempt informed by the
Critic's specific feedback. This repeats until either the Critic passes
the draft, or MAX_REVISIONS is reached.

This is plain Python (not yet a LangGraph node) so the loop logic can
be tested in isolation before Module 12 wraps it into the full graph.
"""

from __future__ import annotations

from typing import Optional

from app.agents.critic import run_critic, CriticError
from app.agents.writer import run_writer, WriterError
from app.graph.state import CriticStatus, DraftReport, Evidence, Source, Task, MAX_REVISIONS
from app.llm.client import llm_client, LLMClientError
from app.llm.prompts import WRITER_SYSTEM_PROMPT, writer_revision_prompt
from app.utils.citation_engine import format_source_catalog_for_prompt
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RevisionLoopError(Exception):
    """Raised when the revision loop cannot produce any usable report at all."""


def _revise_draft(
    user_goal: str,
    tasks: list[Task],
    evidence: list[Evidence],
    previous_draft: DraftReport,
    issues: list[str],
    suggestions: list[str],
    sources: Optional[list] = None,
) -> DraftReport:
    """
    Run one revision pass of the Writer, informed by Critic feedback.

    Reuses the same response validation as run_writer() by calling the
    LLM directly with the revision-specific prompt, then applying the
    same parsing rules.
    """
    from app.agents.writer import REQUIRED_SECTIONS, _parse_references, _sources_to_pydantic, select_evidence_for_writer

    tasks_dicts = [{"description": t.description} for t in tasks]

    # Trim evidence for the revision prompt, same as the initial draft.
    prompt_evidence = select_evidence_for_writer(evidence)
    evidence_dicts = [
        {
            "claim": e.claim,
            "source_title": e.source_title,
            "type": e.type.value,
            "confidence": e.confidence.value,
        }
        for e in prompt_evidence
    ]

    source_objects = _sources_to_pydantic(sources or [])
    source_catalog = format_source_catalog_for_prompt(source_objects) if source_objects else ""

    try:
        raw_response = llm_client.generate_json(
            prompt=writer_revision_prompt(
                user_goal=user_goal,
                tasks=tasks_dicts,
                evidence=evidence_dicts,
                previous_draft=previous_draft.model_dump(),
                critique_issues=issues,
                critique_suggestions=suggestions,
                source_catalog=source_catalog,
            ),
            system=WRITER_SYSTEM_PROMPT,
        )
    except LLMClientError as exc:
        raise WriterError(f"Writer revision failed: {exc}") from exc

    missing_sections = [s for s in REQUIRED_SECTIONS if not raw_response.get(s)]
    if missing_sections:
        raise WriterError(f"Writer revision missing required sections: {missing_sections}")

    # Use real sources as references when available
    if source_objects:
        references = source_objects
    else:
        references = _parse_references(raw_response.get("references", []))

    from app.utils.section_normalizer import clean_section_title

    return DraftReport(
        title=clean_section_title(raw_response["title"]),
        executive_summary=raw_response["executive_summary"],
        introduction=raw_response["introduction"],
        findings=raw_response["findings"],
        analysis=raw_response["analysis"],
        limitations=raw_response["limitations"],
        conclusion=raw_response["conclusion"],
        references=references,
    )


def run_revision_loop(
    user_goal: str,
    tasks: list[Task],
    evidence: list[Evidence],
    sources: Optional[list] = None,
) -> dict:
    """
    Run the full Writer -> Critic -> (revise?) loop.

    Returns:
        A dict with:
            - final_report: the best DraftReport produced
            - final_critique: the Critique for that report
            - revision_count: how many revisions were performed
            - quality_status: "passed" or "max_revisions_reached"

    Raises:
        RevisionLoopError: if even the FIRST draft cannot be produced.
                            Once we have at least one draft, we always
                            return something rather than raising.
    """
    logger.info(f"Revision loop started for goal: {user_goal!r}")

    try:
        draft = run_writer(user_goal, tasks, evidence, sources=sources)
    except WriterError as exc:
        raise RevisionLoopError(f"Could not produce an initial draft: {exc}") from exc

    revision_count = 0

    while True:
        try:
            critique = run_critic(user_goal, evidence, draft, sources=sources)
        except CriticError as exc:
            # If the Critic itself fails, we can't safely judge the draft.
            # Return what we have rather than crashing the whole pipeline.
            logger.error(f"Critic failed during revision loop: {exc}")
            return {
                "final_report": draft,
                "final_critique": None,
                "revision_count": revision_count,
                "quality_status": "critic_unavailable",
            }

        if critique.status == CriticStatus.PASS:
            logger.info(f"Revision loop passed after {revision_count} revision(s)")
            return {
                "final_report": draft,
                "final_critique": critique,
                "revision_count": revision_count,
                "quality_status": "passed",
            }

        if revision_count >= MAX_REVISIONS:
            logger.warning(
                f"Max revisions ({MAX_REVISIONS}) reached without passing; "
                "returning best available draft."
            )
            return {
                "final_report": draft,
                "final_critique": critique,
                "revision_count": revision_count,
                "quality_status": "max_revisions_reached",
            }

        # Attempt a revision informed by the Critic's feedback.
        revision_count += 1
        logger.info(f"Starting revision {revision_count}/{MAX_REVISIONS}")

        try:
            draft = _revise_draft(
                user_goal, tasks, evidence, draft, critique.issues, critique.suggestions,
                sources=sources,
            )
        except WriterError as exc:
            # Revision attempt failed - keep the previous draft and stop,
            # rather than losing everything.
            logger.error(f"Revision {revision_count} failed: {exc}")
            return {
                "final_report": draft,
                "final_critique": critique,
                "revision_count": revision_count,
                "quality_status": "revision_failed",
            }