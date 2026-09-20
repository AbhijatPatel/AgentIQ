"""
LangGraph nodes for the AgentIQ workflow.

Each node is a function that takes the current AgentState, does its
work, and returns a dict of state updates. LangGraph merges these
updates into the shared state automatically.

Nodes are thin wrappers around the agent functions built in Modules
5, 8, and 11 - the actual logic lives there. Nodes also emit
AgentEvents (Module 13) so the pipeline's progress can later be
streamed to the frontend via SSE (Module 15).
"""

from __future__ import annotations

from app.agents.orchestrator import run_revision_loop, RevisionLoopError
from app.agents.planner import run_planner, PlannerError
from app.agents.researcher import run_researcher, ResearcherError
from app.graph.events import append_event
from app.graph.state import AgentState
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.utils.citation_engine import (
    assign_citation_numbers,
    create_source,
    deduplicate_sources,
    map_evidence_to_sources,
)
from app.utils.observability import timed_stage
from app.utils.logger import get_logger

logger = get_logger(__name__)


def planner_node(state: AgentState) -> dict:
    """
    Run the Planner agent on the user's goal.
    Writes 'tasks' to state, or 'errors' if planning fails.
    """
    logger.info("[Graph] Entering planner_node")
    events = state.get("agent_events", [])
    events = append_event(events, "planner", "started", "Planning research tasks...")

    with timed_stage("planner"):
        try:
            tasks = run_planner(state["user_goal"])
            events = append_event(
                events, "planner", "completed", f"Produced {len(tasks)} tasks", status="success"
            )
            return {"tasks": tasks, "agent_events": events}
        except PlannerError as exc:
            logger.error(f"[Graph] planner_node failed: {exc}")
            events = append_event(events, "planner", "failed", str(exc), status="error")
            return {
                "tasks": [],
                "agent_events": events,
                "errors": state.get("errors", []) + [f"Planner failed: {exc}"],
            }


def researcher_node(state: AgentState) -> dict:
    """
    Run the Researcher agent on all tasks in parallel.
    Writes combined evidence, images, and videos to state.
    """
    logger.info("[Graph] Entering researcher_node")
    events = state.get("agent_events", [])

    tasks = state.get("tasks", [])
    if not tasks:
        logger.warning("[Graph] No tasks available for researcher_node; skipping.")
        events = append_event(
            events, "researcher", "completed", "No tasks to research", status="success"
        )
        return {"evidence": [], "images": [], "videos": [], "agent_events": events}

    events = append_event(
        events, "researcher", "started", f"Researching {len(tasks)} tasks in parallel..."
    )

    all_evidence = []
    all_images = []
    all_videos = []
    errors = list(state.get("errors", []))

    def research_task(task):
        logger.info(f"[Graph] Starting research for task {task.id}: {task.description}")
        return task, run_researcher(task)

    all_web_results = []
    max_workers = min(len(tasks), 5)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {
            executor.submit(research_task, task): task
            for task in tasks
        }

        for future in as_completed(future_to_task):
            task = future_to_task[future]

            try:
                _, (evidence, images, videos, web_results) = future.result()

                all_evidence.extend(evidence)
                all_images.extend(images)
                all_videos.extend(videos)
                all_web_results.extend(web_results)

                events = append_event(
                    events,
                    "researcher",
                    "tool_result",
                    f"Found {len(evidence)} evidence items for task {task.id}",
                    status="success",
                )

            except ResearcherError as exc:
                logger.error(
                    f"[Graph] Researcher failed on task {task.id}: {exc}"
                )

                errors.append(
                    f"Researcher failed on task {task.id}: {exc}"
                )

                events = append_event(
                    events,
                    "researcher",
                    "failed",
                    f"Task {task.id} failed: {exc}",
                    status="error",
                )

            except Exception as exc:
                logger.exception(
                    f"[Graph] Unexpected researcher error on task {task.id}: {exc}"
                )

                errors.append(
                    f"Researcher failed on task {task.id}: {exc}"
                )

                events = append_event(
                    events,
                    "researcher",
                    "failed",
                    f"Task {task.id} failed unexpectedly: {exc}",
                    status="error",
                )

    events = append_event(
        events,
        "researcher",
        "completed",
        f"Gathered {len(all_evidence)} total evidence items",
        status="success",
    )

    logger.info(
        f"[Graph] Researcher completed: "
        f"{len(all_evidence)} evidence, "
        f"{len(all_images)} images, "
        f"{len(all_videos)} videos"
    )

    # ---------------------------------------------------------
    # Citation engine: create, dedup, number sources; map evidence
    # ---------------------------------------------------------
    raw_sources = []
    for wr in all_web_results:
        raw_sources.append(create_source(wr, source_type="web"))
    for img in all_images:
        raw_sources.append(create_source(img, source_type="image"))
    for vid in all_videos:
        raw_sources.append(create_source(vid, source_type="video"))

    sources = deduplicate_sources(raw_sources)
    sources = assign_citation_numbers(sources)
    all_evidence = map_evidence_to_sources(all_evidence, sources)

    logger.info(
        f"[Graph] Citation engine: "
        f"{len(sources)} unique sources, "
        f"{sum(1 for e in all_evidence if e.citation_num is not None)} mapped claims"
    )

    return {
        "evidence": all_evidence,
        "sources": [s.model_dump() for s in sources],
        "images": all_images,
        "videos": all_videos,
        "errors": errors,
        "agent_events": events,
    }

def writer_critic_node(state: AgentState) -> dict:
    """
    Run the full Writer <-> Critic self-critique revision loop
    (from Module 11) on the collected evidence.
    """
    logger.info("[Graph] Entering writer_critic_node")
    events = state.get("agent_events", [])
    events = append_event(events, "writer", "started", "Writing draft report...")

    try:
        result = run_revision_loop(
            user_goal=state["user_goal"],
            tasks=state.get("tasks", []),
            evidence=state.get("evidence", []),
            sources=state.get("sources", []),
        )

        events = append_event(
            events, "writer", "draft_created", f"Draft created: {result['final_report'].title}",
            status="success",
        )

        if result["revision_count"] > 0:
            events = append_event(
                events,
                "critic",
                "revision_started",
                f"{result['revision_count']} revision(s) were needed",
            )

        if result["final_critique"]:
            events = append_event(
                events,
                "critic",
                "critique_created",
                f"Final score: {result['final_critique'].score} "
                f"({result['final_critique'].status.value})",
                status="success",
            )

        events = append_event(
            events, "critic", "completed", f"Quality status: {result['quality_status']}",
            status="success",
        )

        return {
            "final_report": result["final_report"],
            "critique": result["final_critique"],
            "revision_count": result["revision_count"],
            "agent_events": events,
        }
    except RevisionLoopError as exc:
        logger.error(f"[Graph] writer_critic_node failed completely: {exc}")
        events = append_event(events, "writer", "failed", str(exc), status="error")
        return {
            "errors": state.get("errors", []) + [f"Writer/Critic loop failed: {exc}"],
            "agent_events": events,
        }