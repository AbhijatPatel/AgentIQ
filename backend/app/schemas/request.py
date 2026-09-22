"""
Request schemas for the AgentIQ API.

Pydantic models validate incoming request bodies automatically.
FastAPI rejects malformed requests before they reach our code.
"""

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    """Body for POST /api/research."""

    goal: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="The high-level research goal to investigate.",
        examples=[
            "Impact of generative AI on developer productivity"
        ],
    )


class RenameSessionRequest(BaseModel):
    """Body for PATCH /api/research/{research_id}."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="The new title for the research session.",
    )