"""
Response schemas for the AgentIQ API.

Keeping response shapes explicit (rather than returning raw internal
state) means we control exactly what the frontend sees and never leak
internal implementation details.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from app.graph.state import AgentEvent, Critique, DraftReport, Evidence, Task


class ResearchStartedResponse(BaseModel):
    """Response for POST /api/research"""
    research_id: str
    status: str


class ResearchStatusResponse(BaseModel):
    """Response for GET /api/research/{id}"""
    research_id: str
    status: str
    user_goal: str
    tasks: list[Task] = []
    evidence: list[Evidence] = []
    evidence_count: int = 0
    revision_count: int = 0
    final_report: Optional[DraftReport] = None
    critique: Optional[Critique] = None
    errors: list[str] = []
    images: list[dict] = []
    videos: list[dict] = []


class ResearchEventsResponse(BaseModel):
    """Response for GET /api/research/{id}/events"""
    research_id: str
    events: list[AgentEvent] = []


class DocumentUploadResponse(BaseModel):
    """Response for POST /api/documents/upload"""
    filename: str
    chunks_added: int
    status: str


class HealthResponse(BaseModel):
    """Response for GET /api/health"""
    status: str

class ResearchHistoryItem(BaseModel):
    """One entry in the research history list."""
    research_id: str
    user_goal: str
    status: str
    created_at: Optional[str] = None
    final_report_title: Optional[str] = None


class ResearchHistoryResponse(BaseModel):
    """Response for GET /api/research (list)"""
    sessions: list[ResearchHistoryItem] = []