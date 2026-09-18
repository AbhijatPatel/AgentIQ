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
    max_length=1000,
    description="The high-level research goal to investigate.",
    examples=[
        "Impact of generative AI on developer productivity"
    ],
)