"""
Research endpoints.

POST /api/research               -> start a new research session (runs in background)
GET  /api/research/{id}          -> check status / get final result
GET  /api/research/{id}/events   -> see agent progress events so far
"""

from __future__ import annotations

import asyncio
import json

from fastapi.responses import StreamingResponse


from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.dependencies import create_session, get_session, update_session
from app.graph.workflow import run_agentiq
from app.schemas.request import ResearchRequest
from app.schemas.response import (
    ResearchEventsResponse,
    ResearchStartedResponse,
    ResearchStatusResponse,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


def _run_research_pipeline(research_id: str, user_goal: str) -> None:
    """
    Runs the full AgentIQ pipeline and updates the session when done.
    This runs in a FastAPI BackgroundTask - the HTTP request has already
    returned to the client by the time this executes.
    """
    try:
        final_state = run_agentiq(user_goal)

        update_session(
            research_id,
            status="completed",
            tasks=final_state.get("tasks", []),
            evidence=final_state.get("evidence", []),
            evidence_count=len(final_state.get("evidence", [])),
            revision_count=final_state.get("revision_count", 0),
            final_report=final_state.get("final_report"),
            critique=final_state.get("critique"),
            errors=final_state.get("errors", []),
            agent_events=final_state.get("agent_events", []),
        )
        logger.info(f"Research session {research_id} completed")
    except Exception as exc:  # noqa: BLE001 - background task must never crash silently
        logger.error(f"Research session {research_id} failed completely: {exc}")
        update_session(
            research_id,
            status="failed",
            errors=[f"Pipeline crashed: {exc}"],
        )


@router.post("/research", response_model=ResearchStartedResponse, status_code=202)
def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    """
    Start a new research session. Returns immediately with a research_id;
    the actual pipeline runs in the background (it takes 1-3 minutes).
    """
    research_id = create_session(request.goal)
    background_tasks.add_task(_run_research_pipeline, research_id, request.goal)

    return ResearchStartedResponse(research_id=research_id, status="running")


@router.get("/research/{research_id}", response_model=ResearchStatusResponse)
def get_research_status(research_id: str):
    """Get the current status and (if completed) the final report."""
    session = get_session(research_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Research session not found")

    return ResearchStatusResponse(**session)


@router.get("/research/{research_id}/events", response_model=ResearchEventsResponse)
def get_research_events(research_id: str):
    """Get all agent events emitted so far for this session."""
    session = get_session(research_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Research session not found")

    return ResearchEventsResponse(
        research_id=research_id, events=session.get("agent_events", [])
    )
async def _event_stream(research_id: str):
    """
    Async generator that yields new AgentEvents as Server-Sent Events.

    Polls the session's agent_events list every 500ms and streams only
    events that haven't been sent yet. Stops when the session reaches
    a terminal status (completed/failed) and all events have been sent.
    """
    sent_count = 0

    while True:
        session = get_session(research_id)
        if session is None:
            yield f"data: {json.dumps({'event': 'error', 'message': 'Session not found'})}\n\n"
            return

        events = session.get("agent_events", [])

        # Stream any events we haven't sent yet
        while sent_count < len(events):
            event = events[sent_count]
            payload = event.model_dump() if hasattr(event, "model_dump") else event
            yield f"data: {json.dumps(payload, default=str)}\n\n"
            sent_count += 1

        status = session.get("status")
        if status in ("completed", "failed") and sent_count >= len(events):
            yield f"data: {json.dumps({'event': 'done', 'status': status})}\n\n"
            return

        await asyncio.sleep(0.5)


@router.get("/research/{research_id}/stream")
async def stream_research_events(research_id: str):
    """
    Stream agent events live via Server-Sent Events (SSE) as the
    research pipeline runs, instead of requiring the frontend to poll.
    """
    session = get_session(research_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Research session not found")

    return StreamingResponse(
        _event_stream(research_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disables proxy buffering, keeps stream live
        },
    )