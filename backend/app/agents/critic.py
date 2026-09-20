"""
Critic Agent.

Evaluates a Writer's draft report against the evidence it should be
grounded in. This is the quality gate before a report either passes
to the user or goes back to the Writer for revision.
"""

from __future__ import annotations

from typing import Optional

from app.graph.state import Critique, CriticStatus, DraftReport, Evidence, Source
from app.llm.client import llm_client, LLMClientError
from app.llm.prompts import CRITIC_SYSTEM_PROMPT, critic_user_prompt
from app.utils.citation_engine import validate_citations_in_text
from app.utils.logger import get_logger

logger = get_logger(__name__)

MIN_PASS_SCORE = 6.0


class CriticError(Exception):
    """Raised when the Critic agent cannot produce a valid evaluation."""


def _evidence_to_dicts(evidence: list[Evidence]) -> list[dict]:
    return [
        {"claim": e.claim, "source_title": e.source_title, "type": e.type.value}
        for e in evidence
    ]


def _normalize_status(value: str, score: float) -> CriticStatus:
    """
    Trust the LLM's status if it's valid, but as a safety net, never let
    a low score pass through as "pass" even if the LLM says so.
    """
    try:
        status = CriticStatus(value.lower().strip())
    except (ValueError, AttributeError):
        status = CriticStatus.REVISE  # unclear status defaults to the safer option

    if status == CriticStatus.PASS and score < MIN_PASS_SCORE:
        logger.warning(
            f"LLM marked status=pass but score={score} is below {MIN_PASS_SCORE}; "
            "overriding to revise."
        )
        return CriticStatus.REVISE

    return status


def _clamp_score(value) -> float:
    """Ensure score is a float between 0.0 and 10.0, defaulting to 0.0 if invalid."""
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(10.0, score))


def run_critic(
    user_goal: str,
    evidence: list[Evidence],
    draft: DraftReport,
    sources: Optional[list] = None,
) -> Critique:
    """
    Run the Critic agent to evaluate a draft report.

    Args:
        user_goal: The original high-level user goal.
        evidence: List of Evidence objects the report should be grounded in.
        draft: The Writer's draft report.
        sources: Optional list of Source objects/dicts for citation validation.

    Returns:
        A validated Critique with status, score, issues, and suggestions.

    Raises:
        CriticError: if the LLM call fails.
    """
    logger.info(f"Critic started for draft: {draft.title!r}")

    try:
        raw_response = llm_client.generate_json(
            prompt=critic_user_prompt(
                user_goal=user_goal,
                evidence=_evidence_to_dicts(evidence),
                draft_report=draft.model_dump(),
            ),
            system=CRITIC_SYSTEM_PROMPT,
        )
    except LLMClientError as exc:
        logger.error(f"Critic LLM call failed: {exc}")
        raise CriticError(f"Critic failed to evaluate draft: {exc}") from exc

    score = _clamp_score(raw_response.get("score"))
    status = _normalize_status(raw_response.get("status", "revise"), score)

    issues = raw_response.get("issues", [])
    suggestions = raw_response.get("suggestions", [])

    issues_list = [str(i) for i in issues] if isinstance(issues, list) else []
    suggestions_list = [str(s) for s in suggestions] if isinstance(suggestions, list) else []

    # ---------------------------------------------------------
    # Citation validation: check that [N] numbers in the report
    # text actually map to real sources
    # ---------------------------------------------------------
    if sources:
        valid_nums = set()
        for s in sources:
            if isinstance(s, dict):
                cn = s.get("citation_num")
            elif isinstance(s, Source):
                cn = s.citation_num
            else:
                cn = None
            if cn is not None:
                valid_nums.add(int(cn))

        if valid_nums:
            # Check all prose sections for invalid citation numbers
            all_text = " ".join([
                draft.executive_summary or "",
                draft.introduction or "",
                draft.findings or "",
                draft.analysis or "",
                draft.limitations or "",
                draft.conclusion or "",
            ])
            citation_report = validate_citations_in_text(all_text, valid_nums)

            if not citation_report["is_valid"]:
                invalid = citation_report["invalid_citations"]
                issues_list.append(
                    f"Report contains invalid citation numbers {invalid} "
                    f"that do not map to any collected source."
                )
                logger.warning(
                    f"Critic found invalid citations in draft: {invalid}"
                )

    critique = Critique(
        status=status,
        score=score,
        issues=issues_list,
        suggestions=suggestions_list,
    )

    logger.info(f"Critic completed: status={critique.status.value}, score={critique.score}")
    return critique