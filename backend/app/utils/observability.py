"""
Observability utilities: timing decorators and execution summaries.

Builds on the AgentEvent system (Module 13) rather than replacing it -
this module adds duration tracking to nodes and produces a structured
per-agent summary from a completed session's events, matching the
format your master plan specifies:

Planner
- Status: SUCCESS
- Duration: 2.4s
- Tasks: 5
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)


@contextmanager
def timed_stage(stage_name: str):
    """
    Context manager that times a block of code and logs the duration.

    Usage:
        with timed_stage("planner") as timer:
            ... do work ...
        print(timer["duration_seconds"])
    """
    timer: dict[str, Any] = {}
    start = time.perf_counter()
    try:
        yield timer
    finally:
        duration = time.perf_counter() - start
        timer["duration_seconds"] = round(duration, 2)
        logger.info(f"[Timing] {stage_name} took {timer['duration_seconds']}s")


def build_execution_summary(agent_events: list[dict], revision_count: int = 0) -> dict:
    """
    Build a structured per-agent execution summary from a session's
    agent_events list (each event is a dict with agent/event/message/status).

    Returns a dict keyed by agent name, e.g.:
        {
            "planner": {"status": "success", "tasks": 5},
            "researcher": {"status": "success", "rag_calls": 3, "web_searches": 3, "sources": 22},
            "writer": {"status": "success"},
            "critic": {"status": "success", "revisions": 0},
        }
    """
    summary: dict[str, dict] = {
        "planner": {"status": "not_run"},
        "researcher": {"status": "not_run", "tool_calls": 0, "sources": 0},
        "writer": {"status": "not_run"},
        "critic": {"status": "not_run", "revisions": revision_count},
    }

    for event in agent_events:
        agent = event.get("agent")
        event_type = event.get("event")
        status = event.get("status")
        message = event.get("message", "")

        if agent not in summary:
            continue

        if event_type in ("completed", "draft_created", "critique_created"):
            summary[agent]["status"] = "success"
        elif status == "error":
            summary[agent]["status"] = "error"

        if agent == "planner" and event_type == "completed":
            # message looks like "Produced 5 tasks"
            digits = "".join(c for c in message if c.isdigit())
            if digits:
                summary["planner"]["tasks"] = int(digits)

        if agent == "researcher" and event_type == "tool_call":
            summary["researcher"]["tool_calls"] += 1

        if agent == "researcher" and event_type == "completed":
            digits = "".join(c for c in message if c.isdigit())
            if digits:
                summary["researcher"]["sources"] = int(digits)

        if agent == "critic" and event_type == "critique_created":
            # message looks like "Final score: 9.0 (pass)"
            try:
                score_str = message.split("Final score:")[1].split("(")[0].strip()
                summary["critic"]["score"] = float(score_str)
            except (IndexError, ValueError):
                pass

    return summary


def format_summary_text(summary: dict) -> str:
    """
    Render the execution summary as human-readable indented text,
    matching the master plan's example output format.
    """
    lines = []
    for agent_name, stats in summary.items():
        lines.append(agent_name.capitalize())
        stat_items = [(k, v) for k, v in stats.items() if k != "status"]
        lines.append(f"├── Status: {stats.get('status', 'unknown').upper()}")
        for i, (key, value) in enumerate(stat_items):
            prefix = "└──" if i == len(stat_items) - 1 else "├──"
            label = key.replace("_", " ").capitalize()
            lines.append(f"{prefix} {label}: {value}")
        lines.append("")
    return "\n".join(lines)