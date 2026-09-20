
"""
Researcher Agent.

Given a single task from the Planner, gathers raw material from both
RAG (your own documents) and web search, then asks the LLM to extract
clean, well-sourced evidence from that material.

The Researcher never invents facts - it only asks the LLM to summarize
and cite from material we actually retrieved.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.graph.state import ConfidenceLevel, Evidence, EvidenceType, Task
from app.llm.client import llm_client, LLMClientError
from app.llm.prompts import RESEARCHER_SYSTEM_PROMPT, researcher_user_prompt
from app.rag.retriever import retrieve
from app.tools.web_search import (
    web_search,
    image_search,
    video_search,
    WebSearchError,
)
from app.tools.youtube_search import (
    youtube_search,
    YouTubeSearchError,
)
from app.utils.validators import sanitize_retrieved_content
from app.utils.cache import ResearchCache
from app.utils.deduplication import (
    deduplicate_web_results,
    deduplicate_image_results,
    deduplicate_video_results,
)
from app.utils.evidence_quality import filter_valid_evidence
from app.utils.logger import get_logger

logger = get_logger(__name__)

RAG_TOP_K = 3
WEB_MAX_RESULTS = 3
IMAGE_MAX_RESULTS = 4
VIDEO_MAX_RESULTS = 3
YOUTUBE_MAX_RESULTS = 4

MAX_PARALLEL_RESEARCH_TASKS = 4

# Keep LLM prompts small enough to avoid provider token limits.
MAX_RAW_MATERIAL_CHARS = 12000

research_cache = ResearchCache(ttl_seconds=3600)


class ResearcherError(Exception):
    """Raised when the Researcher agent cannot produce usable evidence."""


def _format_raw_material(
    rag_results: list[dict],
    web_results: list[dict],
) -> str:
    sections: list[str] = []

    if rag_results:
        sections.append("=== INTERNAL DOCUMENTS (RAG) ===")

        for i, r in enumerate(rag_results, start=1):
            content = sanitize_retrieved_content(
                r.get("content", ""),
                source_label=r.get("filename", "unknown"),
            )

            sections.append(
                f"[Doc {i}] Source: {r.get('filename', 'unknown')}\n"
                f"{content}"
            )

    if web_results:
        sections.append("\n=== WEB SEARCH RESULTS ===")

        for i, r in enumerate(web_results, start=1):
            content = sanitize_retrieved_content(
                r.get("content", ""),
                source_label=r.get("url", "unknown"),
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
        return EvidenceType.ASSUMPTION


def _normalize_confidence(value: str) -> ConfidenceLevel:
    try:
        return ConfidenceLevel(value.lower().strip())
    except (ValueError, AttributeError):
        return ConfidenceLevel.LOW


def _run_rag(task: Task) -> tuple[list[dict], float]:
    start = time.perf_counter()

    try:
        results = retrieve(
            task.description,
            top_k=RAG_TOP_K,
        )
    except Exception as exc:
        logger.warning(
            f"RAG retrieval failed for task {task.id}: {exc}"
        )
        results = []

    elapsed = time.perf_counter() - start

    logger.info(
        f"RAG completed for task {task.id} "
        f"in {elapsed:.2f}s with {len(results)} results"
    )

    return results, elapsed


def _clean_query_for_media(text: str) -> str:
    """
    Extract clean keywords from multilingual/conversational task descriptions
    so that visual media search engines (Pexels and stock image engines) return optimal results.
    """
    if not text:
        return ""

    # Common conversational / question stop-words across English, Hinglish, Spanish, etc.
    stop_words = {
        "ka", "ki", "ke", "ko", "se", "me", "mein", "par", "kahan", "kyun", "kaise",
        "kya", "hai", "hain", "tha", "the", "thi", "hoga", "hogi", "hote", "hota",
        "hoti", "liye", "aur", "ya", "bhi", "toh", "exact", "exactly", "use", "kare",
        "karna", "karein", "de", "do", "karo", "please", "batao", "bataye", "bataiye",
        "investigate", "overview", "study", "research", "what", "is", "are", "how",
        "why", "where", "when", "the", "a", "an", "in", "on", "at", "for", "de",
        "la", "el", "los", "las", "un", "una", "en", "por", "para", "como", "que"
    }

    words = text.split()
    filtered = [w for w in words if w.lower().strip("?,.!;:\"'()[]{}") not in stop_words]
    cleaned = " ".join(filtered).strip("?,.!;:\"'()[]{} ")

    return cleaned if len(cleaned) >= 3 else text


def _run_image_search(task: Task) -> tuple[list[dict], float]:
    start = time.perf_counter()

    try:
        # First try full task description
        results = image_search(
            task.description,
            max_results=IMAGE_MAX_RESULTS,
        )
        # If no results and query has conversational/multilingual terms, retry with cleaned keywords
        if not results:
            cleaned = _clean_query_for_media(task.description)
            if cleaned != task.description:
                logger.info(f"Retrying image search with cleaned keywords: {cleaned!r}")
                results = image_search(cleaned, max_results=IMAGE_MAX_RESULTS)
    except WebSearchError as exc:
        logger.warning(
            f"Image search failed for task {task.id}: {exc}"
        )
        results = []

    elapsed = time.perf_counter() - start

    logger.info(
        f"Image search completed for task {task.id} "
        f"in {elapsed:.2f}s with {len(results)} results"
    )

    return results, elapsed


def _run_video_search(task: Task) -> tuple[list[dict], float]:
    """Fetch videos from both YouTube and Pexels, merging the results."""
    start = time.perf_counter()

    # --- YouTube (supports all languages natively, no API key needed) ---
    youtube_results: list[dict] = []
    try:
        youtube_results = youtube_search(
            task.description,
            max_results=YOUTUBE_MAX_RESULTS,
        )
    except YouTubeSearchError as exc:
        logger.warning(
            f"YouTube search failed for task {task.id}: {exc}"
        )

    # --- Pexels (supplemental stock footage; cleaned keywords work best) ---
    pexels_results: list[dict] = []
    try:
        pexels_query = _clean_query_for_media(task.description)
        pexels_results = video_search(
            pexels_query,
            max_results=VIDEO_MAX_RESULTS,
        )
    except WebSearchError as exc:
        logger.warning(
            f"Pexels video search failed for task {task.id}: {exc}"
        )

    # Merge: YouTube first, then Pexels
    results = youtube_results + pexels_results

    elapsed = time.perf_counter() - start

    logger.info(
        f"Video search completed for task {task.id} "
        f"in {elapsed:.2f}s with {len(results)} results "
        f"(YouTube: {len(youtube_results)}, Pexels: {len(pexels_results)})"
    )

    return results, elapsed


def _run_web_search(task: Task) -> tuple[list[dict], float]:
    start = time.perf_counter()

    try:
        results = web_search(
            task.description,
            max_results=WEB_MAX_RESULTS,
        )
    except WebSearchError as exc:
        logger.warning(
            f"Web search failed for task {task.id}: {exc}"
        )
        results = []

    elapsed = time.perf_counter() - start

    logger.info(
        f"Web search completed for task {task.id} "
        f"in {elapsed:.2f}s with {len(results)} results"
    )

    return results, elapsed


def run_researcher(
    task: Task,
) -> tuple[list[Evidence], list[dict], list[dict], list[dict]]:
    total_start = time.perf_counter()

    logger.info(
        f"Researcher started for task {task.id}: "
        f"{task.description!r}"
    )

    cached_result = research_cache.get(task.description)

    if cached_result is not None:
        total_time = time.perf_counter() - total_start

        logger.info(
            f"Researcher cache HIT for task {task.id} "
            f"in {total_time:.2f}s"
        )

        return cached_result

    logger.info(
        f"Researcher cache MISS for task {task.id}"
    )

    rag_results: list[dict] = []
    images: list[dict] = []
    videos: list[dict] = []
    web_results: list[dict] = []

    timing: dict[str, float] = {}

    parallel_start = time.perf_counter()

    research_functions = {
        "rag": _run_rag,
        "images": _run_image_search,
        "videos": _run_video_search,
        "web": _run_web_search,
    }

    with ThreadPoolExecutor(
        max_workers=MAX_PARALLEL_RESEARCH_TASKS
    ) as executor:

        futures = {
            executor.submit(function, task): name
            for name, function in research_functions.items()
        }

        for future in as_completed(futures):
            name = futures[future]

            try:
                results, elapsed = future.result()

                timing[name] = elapsed

                if name == "rag":
                    rag_results = results

                elif name == "images":
                    images = results

                elif name == "videos":
                    videos = results

                elif name == "web":
                    web_results = results

            except Exception as exc:
                logger.error(
                    f"Parallel research operation "
                    f"'{name}' failed for task {task.id}: {exc}"
                )

                timing[name] = 0.0

    parallel_time = time.perf_counter() - parallel_start

    logger.info(
        f"Parallel research operations completed "
        f"for task {task.id} in {parallel_time:.2f}s"
    )

    # ---------------------------------------------------------
    # Module 34: Research result deduplication
    # ---------------------------------------------------------

    web_results = deduplicate_web_results(web_results)

    images = deduplicate_image_results(images)

    videos = deduplicate_video_results(videos)

    logger.info(
        f"Research results after deduplication "
        f"for task {task.id}: "
        f"Web={len(web_results)}, "
        f"Images={len(images)}, "
        f"Videos={len(videos)}"
    )

    # ---------------------------------------------------------
    # No usable research material
    # ---------------------------------------------------------

    if not rag_results and not web_results:
        total_time = time.perf_counter() - total_start

        logger.warning(
            f"No material found for task {task.id}; "
            f"returning no evidence. "
            f"Total time: {total_time:.2f}s"
        )

        return [], images, videos, web_results

    raw_material = _format_raw_material(
    rag_results,
    web_results,
)

    if len(raw_material) > MAX_RAW_MATERIAL_CHARS:
     logger.warning(
        f"Researcher raw material exceeds limit for task {task.id}. "
        f"Truncating from {len(raw_material)} to "
        f"{MAX_RAW_MATERIAL_CHARS} characters."
    )

    raw_material = raw_material[:MAX_RAW_MATERIAL_CHARS]
    logger.info(
        f"Researcher raw material size for task {task.id}: "
        f"{len(raw_material)} characters"
    )

    # ---------------------------------------------------------
    # LLM evidence extraction
    # ---------------------------------------------------------

    llm_start = time.perf_counter()

    try:
        raw_response = llm_client.generate_json(
            prompt=researcher_user_prompt(
                task.description,
                raw_material,
            ),
            system=RESEARCHER_SYSTEM_PROMPT,
        )

    except LLMClientError as exc:
        llm_time = time.perf_counter() - llm_start

        logger.error(
            f"Researcher LLM call failed for task {task.id} "
            f"after {llm_time:.2f}s: {exc}"
        )

        raise ResearcherError(
            f"Researcher failed to extract evidence: {exc}"
        ) from exc

    llm_time = time.perf_counter() - llm_start

    logger.info(
        f"LLM completed for task {task.id} "
        f"in {llm_time:.2f}s"
    )

    # ---------------------------------------------------------
    # Convert LLM response into Evidence objects
    # ---------------------------------------------------------

    raw_evidence = raw_response.get(
        "evidence",
        [],
    )

    if not isinstance(raw_evidence, list):
        raw_evidence = []

    evidence_list: list[Evidence] = []

    for item in raw_evidence:

        if not isinstance(item, dict):
            continue

        claim = item.get(
            "claim",
            "",
        ).strip()

        source_title = item.get(
            "source_title",
            "",
        ).strip()

        if not claim or not source_title:
            continue

        evidence_list.append(
            Evidence(
                task_id=task.id,
                claim=claim,
                source_title=source_title,
                source_url=item.get("source_url"),
                type=_normalize_evidence_type(
                    item.get(
                        "type",
                        "evidence",
                    )
                ),
                confidence=_normalize_confidence(
                    item.get(
                        "confidence",
                        "medium",
                    )
                ),
            )
        )

    # ---------------------------------------------------------
    # Module 34: Evidence quality filtering
    # ---------------------------------------------------------

    evidence_list = filter_valid_evidence(
        evidence_list
    )

    gaps = raw_response.get(
        "gaps",
        [],
    )

    if gaps:
        logger.info(
            f"Researcher noted gaps for task "
            f"{task.id}: {gaps}"
        )

    # ---------------------------------------------------------
    # Final timing information
    # ---------------------------------------------------------

    total_time = time.perf_counter() - total_start

    logger.info(
        f"Researcher completed task {task.id} "
        f"with {len(evidence_list)} evidence items "
        f"in {total_time:.2f}s"
    )

    logger.info(
        f"Researcher timing breakdown for task {task.id}: "
        f"RAG={timing.get('rag', 0.0):.2f}s, "
        f"Images={timing.get('images', 0.0):.2f}s, "
        f"Videos={timing.get('videos', 0.0):.2f}s, "
        f"Web={timing.get('web', 0.0):.2f}s, "
        f"Parallel={parallel_time:.2f}s, "
        f"LLM={llm_time:.2f}s, "
        f"Total={total_time:.2f}s"
    )

    result = (
        evidence_list,
        images,
        videos,
        web_results,
    )

    research_cache.set(
        task.description,
        result,
    )

    logger.info(
        f"Researcher result cached for task {task.id}"
    )

    return result

