"""
The complete AgentIQ LangGraph workflow.

Wires the three nodes (planner -> researcher -> writer_critic) into a
single compiled StateGraph that can be invoked with a user goal and
will run the entire pipeline end to end.
"""

from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from app.graph.nodes import planner_node, researcher_node, writer_critic_node
from app.graph.state import AgentState, create_initial_state
from app.utils.logger import get_logger

logger = get_logger(__name__)


def build_workflow():
    """
    Build and compile the AgentIQ graph.

    Returns a compiled LangGraph app with a single .invoke(state) method
    that runs the full pipeline.
    """
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("writer_critic", writer_critic_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "researcher")
    graph.add_edge("researcher", "writer_critic")
    graph.add_edge("writer_critic", END)

    return graph.compile()


# Single compiled instance reused across the app.
agentiq_workflow = build_workflow()


def run_agentiq(
    user_goal: str,
    session_id: str = "",
    user_id: str = "",
) -> AgentState:
    """
    Run the complete AgentIQ pipeline for a user goal within an isolated session and user context.
    """
    logger.info(
        f"AgentIQ workflow starting for goal: {user_goal!r} "
        f"(user: {user_id or 'anon'}, session: {session_id or 'global'})"
    )

    initial_state = create_initial_state(
        user_goal=user_goal,
        session_id=session_id,
        user_id=user_id,
    )
    final_state = agentiq_workflow.invoke(initial_state)

    logger.info("AgentIQ workflow completed")
    return final_state