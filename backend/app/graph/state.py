"""
Shared state for the AgentIQ LangGraph workflow.

Why this file exists:
LangGraph passes a single state object between every node (Planner,
Researcher, Writer, Critic). Using typed Pydantic models instead of raw
dicts means:
- IDE autocomplete works everywhere
- typos in field names are caught immediately, not at runtime
- every agent knows exactly what shape of data to expect

This file defines that shared state and the smaller structures it's built from.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, TypedDict

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EvidenceType(str, Enum):
    EVIDENCE = "evidence"
    ASSUMPTION = "assumption"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CriticStatus(str, Enum):
    PASS = "pass"
    REVISE = "revise"


# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------

class Task(BaseModel):
    """A single research task produced by the Planner agent."""
    id: int
    description: str
    priority: Priority = Priority.MEDIUM
    completed: bool = False


class Source(BaseModel):
    """A single source used somewhere in the research process."""
    source_id: str = ""
    citation: Optional[str] = None
    citation_num: Optional[int] = None
    title: str = "Untitled Source"
    url: Optional[str] = None
    domain: Optional[str] = None
    source_type: str = "web"
    snippet: Optional[str] = None
    published_date: Optional[str] = None
    author: Optional[str] = None
    query: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class Evidence(BaseModel):
    """A single extracted, sourced claim produced by the Researcher agent."""
    task_id: int
    claim: str
    source_title: str
    source_url: Optional[str] = None
    source_id: Optional[str] = None
    citation_num: Optional[int] = None
    type: EvidenceType = EvidenceType.EVIDENCE
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class DraftReport(BaseModel):
    """The report produced by the Writer agent."""
    title: str
    executive_summary: str
    introduction: str
    findings: str
    analysis: str
    limitations: str
    conclusion: str
    references: list[Source] = Field(default_factory=list)


class Critique(BaseModel):
    """The evaluation produced by the Critic agent."""
    status: CriticStatus
    score: float
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class AgentEvent(BaseModel):
    """A single event emitted by an agent, for observability / SSE streaming."""
    agent: str
    event: str
    message: str
    status: str = "running"
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# Shared graph state
# ---------------------------------------------------------------------------

MAX_REVISIONS = 3


class AgentState(TypedDict, total=False):
    """
    The single shared state object passed between every LangGraph node.

    We use TypedDict (not BaseModel) here because LangGraph expects a
    dict-like state object that it can merge updates into between node
    calls. The individual fields still use our Pydantic models above for
    structure and validation.

    total=False means no field is required to be present at all times -
    the state grows as it flows through the graph (e.g. 'tasks' doesn't
    exist until after the Planner node runs).
    """

    # Input & Session Scope
    user_goal: str
    session_id: str
    user_id: str

    # Planner output
    tasks: list[Task]

    # Researcher output
    evidence: list[Evidence]
    sources: list[Source]
    images: list[dict]
    videos: list[dict]

    # Writer output
    draft: DraftReport

    # Critic output
    critique: Critique
    revision_count: int

    # Final output
    final_report: DraftReport

    # Observability / error handling
    agent_events: list[AgentEvent]
    errors: list[str]


def create_initial_state(
    user_goal: str,
    session_id: str = "",
    user_id: str = "",
) -> AgentState:
    return AgentState(
        user_goal=user_goal,
        session_id=session_id,
        user_id=user_id,
        tasks=[],
        evidence=[],
        sources=[],
        images=[],
        videos=[],
        revision_count=0,
        agent_events=[],
        errors=[],
    )