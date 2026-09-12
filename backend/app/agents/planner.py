"""
Planner Agent.

Takes a high-level user goal and produces a structured, deduplicated,
prioritized list of research tasks using the LLM.

This is the first node in the AgentIQ pipeline:
    user_goal -> Planner -> tasks -> Researcher -> ...
"""

from __future__ import annotations

from app.graph.state import Priority, Task
from app.llm.client import llm_client, LLMClientError
from app.llm.prompts import PLANNER_SYSTEM_PROMPT, planner_user_prompt
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PlannerError(Exception):
    """Raised when the Planner agent cannot produce a valid task list."""


def _normalize_priority(value: str) -> Priority:
    """
    Convert whatever priority string the LLM returned into a valid Priority
    enum value, defaulting to MEDIUM if it's something unexpected.
    """
    try:
        return Priority(value.lower().strip())
    except (ValueError, AttributeError):
        logger.warning(f"Unrecognized priority '{value}', defaulting to medium")
        return Priority.MEDIUM


def _deduplicate_tasks(raw_tasks: list[dict]) -> list[dict]:
    """
    Remove tasks with near-identical descriptions.

    We do a simple case-insensitive exact-match dedup here. The prompt
    already instructs the LLM not to duplicate tasks, but models
    occasionally slip up, so this is a safety net.
    """
    seen: set[str] = set()
    deduplicated: list[dict] = []

    for task in raw_tasks:
        key = task.get("description", "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduplicated.append(task)

    return deduplicated


def run_planner(user_goal: str) -> list[Task]:
    """
    Run the Planner agent on a user goal.

    Args:
        user_goal: The high-level research goal from the user.

    Returns:
        A list of validated Task objects.

    Raises:
        PlannerError: if the goal is empty, or the LLM fails to produce
                      a usable task list.
    """
    if not user_goal or not user_goal.strip():
        raise PlannerError("User goal cannot be empty.")

    logger.info(f"Planner started for goal: {user_goal!r}")

    try:
        raw_response = llm_client.generate_json(
            prompt=planner_user_prompt(user_goal),
            system=PLANNER_SYSTEM_PROMPT,
        )
    except LLMClientError as exc:
        logger.error(f"Planner LLM call failed: {exc}")
        raise PlannerError(f"Planner failed to generate tasks: {exc}") from exc

    raw_tasks = raw_response.get("tasks")
    if not raw_tasks or not isinstance(raw_tasks, list):
        raise PlannerError("Planner LLM response did not contain a valid 'tasks' list.")

    deduplicated = _deduplicate_tasks(raw_tasks)
    if not deduplicated:
        raise PlannerError("Planner produced no usable tasks after deduplication.")

    tasks: list[Task] = []
    for i, raw_task in enumerate(deduplicated, start=1):
        description = raw_task.get("description", "").strip()
        if not description:
            continue  # skip malformed entries rather than failing the whole run

        tasks.append(
            Task(
                id=raw_task.get("id", i),
                description=description,
                priority=_normalize_priority(raw_task.get("priority", "medium")),
            )
        )

    if not tasks:
        raise PlannerError("Planner produced no valid tasks.")

    logger.info(f"Planner completed with {len(tasks)} tasks")
    return tasks