"""
Tests for observability utilities: timing and execution summaries.
"""

import time

from app.utils.observability import build_execution_summary, format_summary_text, timed_stage


def test_timed_stage_records_duration():
    with timed_stage("test_stage") as timer:
        time.sleep(0.05)

    assert timer["duration_seconds"] >= 0.05


def test_build_execution_summary_tracks_planner_tasks():
    events = [
        {"agent": "planner", "event": "started", "message": "Planning...", "status": "running"},
        {"agent": "planner", "event": "completed", "message": "Produced 5 tasks", "status": "success"},
    ]

    summary = build_execution_summary(events)

    assert summary["planner"]["status"] == "success"
    assert summary["planner"]["tasks"] == 5


def test_build_execution_summary_tracks_researcher_tool_calls_and_sources():
    events = [
        {"agent": "researcher", "event": "started", "message": "Researching 3 tasks...", "status": "running"},
        {"agent": "researcher", "event": "tool_call", "message": "Researching: task A", "status": "running"},
        {"agent": "researcher", "event": "tool_call", "message": "Researching: task B", "status": "running"},
        {"agent": "researcher", "event": "completed", "message": "Gathered 22 total evidence items", "status": "success"},
    ]

    summary = build_execution_summary(events)

    assert summary["researcher"]["status"] == "success"
    assert summary["researcher"]["tool_calls"] == 2
    assert summary["researcher"]["sources"] == 22


def test_build_execution_summary_tracks_critic_score_and_revisions():
    events = [
        {"agent": "critic", "event": "critique_created", "message": "Final score: 9.2 (pass)", "status": "success"},
    ]

    summary = build_execution_summary(events, revision_count=2)

    assert summary["critic"]["score"] == 9.2
    assert summary["critic"]["revisions"] == 2


def test_build_execution_summary_marks_error_status():
    events = [
        {"agent": "planner", "event": "failed", "message": "LLM timeout", "status": "error"},
    ]

    summary = build_execution_summary(events)

    assert summary["planner"]["status"] == "error"


def test_build_execution_summary_defaults_unused_agents_to_not_run():
    summary = build_execution_summary([])

    assert summary["planner"]["status"] == "not_run"
    assert summary["writer"]["status"] == "not_run"


def test_format_summary_text_produces_readable_output():
    summary = {
        "planner": {"status": "success", "tasks": 5},
    }

    text = format_summary_text(summary)

    assert "Planner" in text
    assert "Status: SUCCESS" in text
    assert "Tasks: 5" in text