"""
Researcher Agent.

Given a single task from the Planner, gathers raw material from both
RAG (your own documents) and web search, then asks the LLM to extract
clean, well-sourced evidence from that material.

The Researcher never invents facts - it only asks the LLM to summarize
and cite from material we actually retrieved.
"""

from __future__ import annotations

from app.graph.state import ConfidenceLevel, Evidence, EvidenceType, Task
from app.llm.client import llm_client, LLMClientError
from app.llm.prompts import RESEARCHER_SYSTEM_PROMPT, researcher_user_prompt
from app.rag.retriever import retrieve
from app.tools.web_search import web_search, WebSearchError
from app.utils.validators import sanitize_retrieved_content
from app.utils.logger import get_logger

logger = get_logger(__name__)

RAG_TOP_K = 4
WEB_MAX_RESULTS = 4


class ResearcherError(Exception):
    """Raised when the Researcher agent cannot produce usable evidence."""


def _format_raw_material(rag_results: list[dict], web_results: list[dict]) -> str:
    """
    Combine RAG and web search results into one text block for the LLM,
    with clear source labels so the LLM can cite them correctly.
    """
    sections: list[str] = []

    if rag_results:
        sections.append("=== INTERNAL DOCUMENTS (RAG) ===")
        for i, r in enumerate(rag_results, start=1):
            content = sanitize_retrieved_content(
                r.get("content", ""), source_label=r.get("filename", "unknown")
            )
            sections.append(f"[Doc {i}] Source: {r.get('filename', 'unknown')}\n{content}")

    if web_results:
        sections.append("\n=== WEB SEARCH RESULTS ===")
        for i, r in enumerate(web_results, start=1):
            content = sanitize_retrieved_content(
                r.get("content", ""), source_label=r.get("url", "unknown")
            )
            sections.append(
                f"[Web {i}] Title: {r.get('title', 'Untitled')}\n"
                f"URL: {r.get('url', 'unknown')}\n"
                f"Content: {content}"
            )

    return "\n\n".join(sections)


def _normalize_evidence_type(value: str) -> EvidenceType:
    try:
        return EvidenceType(value.lower().strip())
    except (ValueError, AttributeError):
        return EvidenceType.ASSUMPTION  # safer default: treat unclear items as assumptions


def _normalize_confidence(value: str) -> ConfidenceLevel:
    try:
        return ConfidenceLevel(value.lower().strip())
    except (ValueError, AttributeError):
        return ConfidenceLevel.LOW  # safer default: treat unclear confidence as low


def run_researcher(task: Task) -> list[Evidence]:
    """
    Run the Researcher agent on a single task.

    Args:
        task: A Task object from the Planner.

    Returns:
        A list of validated Evidence objects. May be empty if no
        material was found or no valid claims could be extracted -
        this is a valid outcome, not an error, per Rule 7 (never fabricate).

    Raises:
        ResearcherError: if the LLM call itself fails.
    """
    logger.info(f"Researcher started for task {task.id}: {task.description!r}")

    # Gather raw material from both sources. Failures in ONE source
    # should not block the other (graceful degradation, Module 20).
    rag_results: list[dict] = []
    try:
        rag_results = retrieve(task.description, top_k=RAG_TOP_K)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"RAG retrieval failed for task {task.id}: {exc}")

    web_results: list[dict] = []
    try:
        web_results = web_search(task.description, max_results=WEB_MAX_RESULTS)
    except WebSearchError as exc:
        logger.warning(f"Web search failed for task {task.id}: {exc}")

    if not rag_results and not web_results:
        logger.warning(f"No material found for task {task.id}; returning no evidence.")
        return []

    raw_material = _format_raw_material(rag_results, web_results)

    try:
        raw_response = llm_client.generate_json(
            prompt=researcher_user_prompt(task.description, raw_material),
            system=RESEARCHER_SYSTEM_PROMPT,
        )
    except LLMClientError as exc:
        logger.error(f"Researcher LLM call failed for task {task.id}: {exc}")
        raise ResearcherError(f"Researcher failed to extract evidence: {exc}") from exc

    raw_evidence = raw_response.get("evidence", [])
    if not isinstance(raw_evidence, list):
        raw_evidence = []

    evidence_list: list[Evidence] = []
    for item in raw_evidence:
        claim = item.get("claim", "").strip()
        source_title = item.get("source_title", "").strip()

        if not claim or not source_title:
            continue  # skip malformed entries rather than failing the whole task

        evidence_list.append(
            Evidence(
                task_id=task.id,
                claim=claim,
                source_title=source_title,
                source_url=item.get("source_url"),
                type=_normalize_evidence_type(item.get("type", "evidence")),
                confidence=_normalize_confidence(item.get("confidence", "medium")),
            )
        )

    gaps = raw_response.get("gaps", [])
    if gaps:
        logger.info(f"Researcher noted gaps for task {task.id}: {gaps}")

    logger.info(f"Researcher completed task {task.id} with {len(evidence_list)} evidence items")
    return evidence_list