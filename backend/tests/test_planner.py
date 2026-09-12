"""
Tests for the Planner agent.

We mock llm_client.generate_json so these tests run instantly and free,
without calling the real Groq API.
"""

from unittest.mock import patch

import pytest

from app.agents.planner import run_planner, PlannerError
from app.graph.state import Priority
from app.llm.client import LLMClientError


@patch("app.agents.planner.llm_client")
def test_run_planner_returns_tasks(mock_llm_client):
    mock_llm_client.generate_json.return_value = {
        "tasks": [
            {"id": 1, "description": "Research AI adoption", "priority": "high"},
            {"id": 2, "description": "Analyze productivity impact", "priority": "medium"},
        ]
    }

    tasks = run_planner("Research the impact of AI on jobs")

    assert len(tasks) == 2
    assert tasks[0].description == "Research AI adoption"
    assert tasks[0].priority == Priority.HIGH
    assert tasks[1].priority == Priority.MEDIUM


@patch("app.agents.planner.llm_client")
def test_run_planner_deduplicates_tasks(mock_llm_client):
    mock_llm_client.generate_json.return_value = {
        "tasks": [
            {"id": 1, "description": "Research AI adoption", "priority": "high"},
            {"id": 2, "description": "research ai adoption", "priority": "low"},  # dup
        ]
    }

    tasks = run_planner("Research AI")

    assert len(tasks) == 1


@patch("app.agents.planner.llm_client")
def test_run_planner_defaults_unknown_priority_to_medium(mock_llm_client):
    mock_llm_client.generate_json.return_value = {
        "tasks": [{"id": 1, "description": "Research something", "priority": "urgent!!"}]
    }

    tasks = run_planner("Research something")

    assert tasks[0].priority == Priority.MEDIUM


@patch("app.agents.planner.llm_client")
def test_run_planner_raises_on_missing_tasks_key(mock_llm_client):
    mock_llm_client.generate_json.return_value = {"oops": "no tasks here"}

    with pytest.raises(PlannerError):
        run_planner("Research something")


@patch("app.agents.planner.llm_client")
def test_run_planner_raises_on_llm_failure(mock_llm_client):
    mock_llm_client.generate_json.side_effect = LLMClientError("timeout")

    with pytest.raises(PlannerError):
        run_planner("Research something")


def test_run_planner_raises_on_empty_goal():
    with pytest.raises(PlannerError):
        run_planner("")

    with pytest.raises(PlannerError):
        run_planner("   ")


@patch("app.agents.planner.llm_client")
def test_run_planner_skips_malformed_tasks(mock_llm_client):
    mock_llm_client.generate_json.return_value = {
        "tasks": [
            {"id": 1, "description": "", "priority": "high"},  # empty description
            {"id": 2, "description": "Valid task", "priority": "high"},
        ]
    }

    tasks = run_planner("Research something")

    assert len(tasks) == 1
    assert tasks[0].description == "Valid task"