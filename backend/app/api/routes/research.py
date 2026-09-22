from __future__ import annotations

import asyncio
import json
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Depends
from fastapi import Request as FastAPIRequest
from fastapi.responses import StreamingResponse

from typing import Optional

from app.api.dependencies import (
    create_session,
    delete_session,
    get_session,
    update_session,
    get_current_user,
)
from app.database.repository import list_sessions
from app.graph.workflow import agentiq_workflow, run_agentiq
from app.graph.state import create_initial_state
from app.schemas.request import ResearchRequest
from app.schemas.response import (
    ResearchEventsResponse,
    ResearchHistoryResponse,
    ResearchStartedResponse,
    ResearchStatusResponse,
)
from app.utils.logger import get_logger
from app.utils.prompt_security import (
    PromptInjectionError,
    validate_prompt_safety,
)
from app.utils.rate_limit import limiter

logger = get_logger(__name__)

router = APIRouter()


def _run_research_pipeline(research_id: str, user_goal: str) -> None:
    try:
        final_state = run_agentiq(user_goal)

        has_final_report = bool(final_state.get("final_report"))
        final_errors = list(final_state.get("errors", []))

        if final_errors and not has_final_report:
            final_status = "failed"
            logger.warning(f"Research session {research_id} finished without report (status=failed). Errors: {final_errors}")
        else:
            final_status = "completed"
            logger.info(f"Research session {research_id} completed (has_report={has_final_report}).")

        update_session(
            research_id,
            status=final_status,
            tasks=final_state.get("tasks", []),
            evidence=final_state.get("evidence", []),
            evidence_count=len(final_state.get("evidence", [])),
            images=final_state.get("images", []),
            videos=final_state.get("videos", []),
            revision_count=final_state.get("revision_count", 0),
            final_report=final_state.get("final_report"),
            critique=final_state.get("critique"),
            errors=final_errors,
            agent_events=final_state.get("agent_events", []),
        )

    except Exception as exc:
        logger.error(f"Research session {research_id} failed completely: {exc}")
        update_session(
            research_id,
            status="failed",
            errors=[f"Pipeline crashed: {exc}"],
        )


@router.get("/research", response_model=ResearchHistoryResponse)
def get_research_history(
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of research sessions to return."),
    search: Optional[str] = Query(default=None, description="Search term to filter sessions by user goal."),
):
    sessions = list_sessions(limit=limit, search=search)
    return ResearchHistoryResponse(sessions=sessions)


@router.delete("/research/{research_id}")
def delete_research_session(research_id: str):
    success = delete_session(research_id)
    if not success:
        raise HTTPException(status_code=404, detail="Research session not found")
    return {"status": "deleted", "research_id": research_id}


@router.post("/research", response_model=ResearchStartedResponse, status_code=202)
@limiter.limit("100/minute")
def start_research(
    request: FastAPIRequest,
    body: ResearchRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
):
    try:
        safe_goal = validate_prompt_safety(body.goal)
    except PromptInjectionError as exc:
        logger.warning(f"Blocked potentially unsafe research prompt: {exc}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    research_id = create_session(safe_goal)
    background_tasks.add_task(_run_research_pipeline, research_id, safe_goal)

    return ResearchStartedResponse(research_id=research_id, status="running")


@router.get("/research/{research_id}", response_model=ResearchStatusResponse)
def get_research_status(research_id: str):
    session = get_session(research_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Research session not found")
    return ResearchStatusResponse(**session)


@router.get("/research/{research_id}/events", response_model=ResearchEventsResponse)
def get_research_events(research_id: str):
    session = get_session(research_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Research session not found")
    return ResearchEventsResponse(research_id=research_id, events=session.get("agent_events", []))


async def _event_stream(research_id: str):
    sent_count = 0
    while True:
        session = get_session(research_id)
        if session is None:
            yield f"data: {json.dumps({'event': 'error', 'message': 'Session not found'})}\n\n"
            return

        events = session.get("agent_events", [])
        while sent_count < len(events):
            event = events[sent_count]
            payload = event.model_dump() if hasattr(event, "model_dump") else event
            yield f"data: {json.dumps(payload, default=str)}\n\n"
            sent_count += 1

        status = session.get("status")
        if status in ("completed", "failed") and sent_count >= len(events):
            yield f"data: {json.dumps({'event': 'done', 'status': status})}\n\n"
            return

        await asyncio.sleep(1.0)


@router.get("/research/{research_id}/stream")
async def stream_research_events(research_id: str):
    session = get_session(research_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Research session not found")

    return StreamingResponse(
        _event_stream(research_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
