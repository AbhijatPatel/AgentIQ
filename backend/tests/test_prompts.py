"""
Tests for prompt templates.

These tests don't call the LLM - they just verify that our prompt-building
functions produce valid strings containing the expected content, and that
system prompts mention the required structure.
"""

from app.llm.prompts import (
    PLANNER_SYSTEM_PROMPT,
    RESEARCHER_SYSTEM_PROMPT,
    WRITER_SYSTEM_PROMPT,
    CRITIC_SYSTEM_PROMPT,
    planner_user_prompt,
    researcher_user_prompt,
    writer_user_prompt,
    critic_user_prompt,
)


def test_planner_system_prompt_mentions_json_and_tasks():
    assert "JSON" in PLANNER_SYSTEM_PROMPT
    assert "tasks" in PLANNER_SYSTEM_PROMPT


def test_planner_user_prompt_includes_goal():
    prompt = planner_user_prompt("Research AI in healthcare")
    assert "Research AI in healthcare" in prompt


def test_researcher_system_prompt_forbids_fabrication():
    assert "NEVER invent" in RESEARCHER_SYSTEM_PROMPT


def test_researcher_user_prompt_includes_task_and_material():
    prompt = researcher_user_prompt("Find adoption stats", "Some raw search results")
    assert "Find adoption stats" in prompt
    assert "Some raw search results" in prompt


def test_writer_system_prompt_forbids_fabricated_citations():
    assert "fabricate" in WRITER_SYSTEM_PROMPT.lower()


def test_writer_user_prompt_includes_goal_tasks_and_evidence():
    prompt = writer_user_prompt(
        user_goal="Research AI in healthcare",
        tasks=[{"description": "Find adoption stats"}],
        evidence=[
            {
                "claim": "AI adoption grew 40%",
                "source_title": "TechReport",
                "type": "evidence",
                "confidence": "high",
            }
        ],
    )
    assert "Research AI in healthcare" in prompt
    assert "Find adoption stats" in prompt
    assert "AI adoption grew 40%" in prompt
    assert "TechReport" in prompt


def test_writer_user_prompt_handles_empty_evidence():
    prompt = writer_user_prompt(
        user_goal="Research AI in healthcare", tasks=[], evidence=[]
    )
    assert "no evidence was collected" in prompt


def test_critic_system_prompt_defines_pass_revise_status():
    assert '"pass|revise"' in CRITIC_SYSTEM_PROMPT


def test_critic_user_prompt_includes_goal_and_evidence():
    prompt = critic_user_prompt(
        user_goal="Research AI in healthcare",
        evidence=[{"claim": "AI adoption grew 40%", "source_title": "TechReport"}],
        draft_report={"title": "AI in Healthcare"},
    )
    assert "Research AI in healthcare" in prompt
    assert "AI adoption grew 40%" in prompt
    assert "AI in Healthcare" in prompt