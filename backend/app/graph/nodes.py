"""
LangGraph nodes for the AgentIQ workflow.

Each node is a function that takes the current AgentState, does its
work, and returns a dict of state updates. LangGraph merges these
updates into the shared state automatically.

Nodes are thin wrappers around the agent functions built in Modules
5, 8, and 11 - the actual logic lives there. This keeps nodes easy to
read and the underlying agent functions independently testable.
"""

from __future__ import annotations

from app.agents.orchestrator import run_revision_loop, RevisionLoopError
from app.agents.planner import run_planner, PlannerError
from app.agents.researcher import run_researcher, ResearcherError
from app.graph.state import AgentState
from app.utils.logger import get_logger

logger = get_logger(__name__)


def planner_node(state: AgentState) -> dict:
    """
    Run the Planner agent on the user's goal.
    Writes 'tasks' to state, or 'errors' if planning fails.
    """
    logger.info("[Graph] Entering planner_node")

    try:
        tasks = run_planner(state["user_goal"])
        return {"tasks": tasks}
    except PlannerError as exc:
        logger.error(f"[Graph] planner_node failed: {exc}")
        return {"tasks": [], "errors": state.get("errors", []) + [f"Planner failed: {exc}"]}


def researcher_node(state: AgentState) -> dict:
    """
    Run the Researcher agent on every task produced by the Planner.
    Writes combined 'evidence' to state.

    If research fails for one task, we log it and continue with the
    remaining tasks - one bad task shouldn't block the whole pipeline.
    """
    logger.info("[Graph] Entering researcher_node")

    tasks = state.get("tasks", [])
    if not tasks:
        logger.warning("[Graph] No tasks available for researcher_node; skipping.")
        return {"evidence": []}

    all_evidence = []
    errors = list(state.get("errors", []))

    for task in tasks:
        try:
            evidence = run_researcher(task)
            all_evidence.extend(evidence)
        except ResearcherError as exc:
            logger.error(f"[Graph] Researcher failed on task {task.id}: {exc}")
            errors.append(f"Researcher failed on task {task.id}: {exc}")

    return {"evidence": all_evidence, "errors": errors}


def writer_critic_node(state: AgentState) -> dict:
    """
    Run the full Writer <-> Critic self-critique revision loop
    (from Module 11) on the collected evidence.

    Writes 'final_report', 'critique', and 'revision_count' to state.
    """
    logger.info("[Graph] Entering writer_critic_node")

    try:
        result = run_revision_loop(
            user_goal=state["user_goal"],
            tasks=state.get("tasks", []),
            evidence=state.get("evidence", []),
        )
        return {
            "final_report": result["final_report"],
            "critique": result["final_critique"],
            "revision_count": result["revision_count"],
        }
    except RevisionLoopError as exc:
        logger.error(f"[Graph] writer_critic_node failed completely: {exc}")
        return {
            "errors": state.get("errors", []) + [f"Writer/Critic loop failed: {exc}"],
        }