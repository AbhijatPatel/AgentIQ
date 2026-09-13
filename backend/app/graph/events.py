"""
Agent event emission helpers.

Every meaningful step an agent takes (starting, completing, calling a
tool, failing) gets recorded as an AgentEvent. These accumulate in
state["agent_events"] and will later be streamed to the React
dashboard in real time via SSE (Module 15).

For now, nodes call these helpers to build up the events list that
gets merged back into state.
"""

from __future__ import annotations

from app.graph.state import AgentEvent
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Standardized event names, so the frontend can rely on a known set
# instead of arbitrary strings.
EVENT_STARTED = "started"
EVENT_COMPLETED = "completed"
EVENT_FAILED = "failed"
EVENT_TOOL_CALL = "tool_call"
EVENT_TOOL_RESULT = "tool_result"
EVENT_DRAFT_CREATED = "draft_created"
EVENT_CRITIQUE_CREATED = "critique_created"
EVENT_REVISION_STARTED = "revision_started"


def make_event(agent: str, event: str, message: str, status: str = "running") -> AgentEvent:
    """
    Build a single AgentEvent.

    Args:
        agent: which agent emitted this ("planner", "researcher", etc.)
        event: one of the EVENT_* constants above (or a custom string)
        message: human-readable description, shown in the UI
        status: "running", "success", or "error"
    """
    return AgentEvent(agent=agent, event=event, message=message, status=status)


def append_event(
    existing_events: list[AgentEvent],
    agent: str,
    event: str,
    message: str,
    status: str = "running",
) -> list[AgentEvent]:
    """
    Return a NEW list with one more event appended.

    We return a new list (rather than mutating in place) because
    LangGraph state updates work best as fresh values - this avoids
    subtle bugs where the same list object is shared across state
    snapshots.
    """
    new_event = make_event(agent, event, message, status)
    logger.info(f"[Event] {agent} | {event} | {message}")
    return existing_events + [new_event]