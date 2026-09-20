"""
Tests for the Writer agent.

The LLM client is mocked so these tests run instantly and free.

Includes tests for:
- Basic happy path
- Missing sections / LLM failure
- No evidence
- Malformed references
- Evidence-count truncation (below limit, above limit)
- Citation/source mapping after truncation
- Configuration override via MAX_EVIDENCE_FOR_WRITER
"""

from unittest.mock import patch

import pytest

from app.agents.writer import run_writer, select_evidence_for_writer, WriterError
from app.graph.state import ConfidenceLevel, Evidence, EvidenceType, Source, Task
from app.llm.client import LLMClientError


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_tasks():
    return [Task(id=1, description="Find AI adoption statistics")]


def _make_evidence_list(n: int = 1, confidence: ConfidenceLevel = ConfidenceLevel.HIGH) -> list:
    """Build *n* evidence items with the given confidence level."""
    return [
        Evidence(
            task_id=1,
            claim=f"Claim number {i}",
            source_title=f"Source {i}",
            source_url=f"https://example.com/source/{i}",
            source_id=f"source_{i}",
            citation_num=i,
            type=EvidenceType.EVIDENCE,
            confidence=confidence,
        )
        for i in range(1, n + 1)
    ]


def _make_evidence():
    return [
        Evidence(
            task_id=1,
            claim="AI adoption grew 40% in 2026",
            source_title="TechReport",
            type=EvidenceType.EVIDENCE,
            confidence=ConfidenceLevel.HIGH,
        )
    ]


def _valid_llm_response(**overrides):
    base = {
        "title": "AI Adoption Report",
        "executive_summary": "Summary text.",
        "introduction": "Intro text.",
        "findings": "Findings text.",
        "analysis": "Analysis text.",
        "limitations": "No major limitations.",
        "conclusion": "Conclusion text.",
        "references": [{"title": "TechReport", "url": "https://example.com"}],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Original tests (unchanged behaviour)
# ---------------------------------------------------------------------------

@patch("app.agents.writer.llm_client")
def test_run_writer_returns_valid_draft(mock_llm_client):
    mock_llm_client.generate_json.return_value = _valid_llm_response()

    draft = run_writer("Research AI adoption", _make_tasks(), _make_evidence())

    assert draft.title == "AI Adoption Report"
    assert draft.executive_summary == "Summary text."
    assert len(draft.references) == 1
    assert draft.references[0].title == "TechReport"


@patch("app.agents.writer.llm_client")
def test_run_writer_raises_on_missing_sections(mock_llm_client):
    incomplete = _valid_llm_response()
    del incomplete["conclusion"]
    mock_llm_client.generate_json.return_value = incomplete

    with pytest.raises(WriterError):
        run_writer("Research AI adoption", _make_tasks(), _make_evidence())


@patch("app.agents.writer.llm_client")
def test_run_writer_raises_on_llm_failure(mock_llm_client):
    mock_llm_client.generate_json.side_effect = LLMClientError("timeout")

    with pytest.raises(WriterError):
        run_writer("Research AI adoption", _make_tasks(), _make_evidence())


@patch("app.agents.writer.llm_client")
def test_run_writer_works_with_no_evidence(mock_llm_client):
    mock_llm_client.generate_json.return_value = _valid_llm_response(
        limitations="No evidence was found for this goal; findings are inconclusive."
    )

    draft = run_writer("Research an obscure topic", [], [])

    assert "inconclusive" in draft.limitations.lower() or "no evidence" in draft.limitations.lower()


@patch("app.agents.writer.llm_client")
def test_run_writer_skips_malformed_references(mock_llm_client):
    mock_llm_client.generate_json.return_value = _valid_llm_response(
        references=[
            {"title": "", "url": "https://example.com"},  # missing title
            {"title": "Valid Source", "url": None},
            "not even a dict",
        ]
    )

    draft = run_writer("Research AI adoption", _make_tasks(), _make_evidence())

    assert len(draft.references) == 1
    assert draft.references[0].title == "Valid Source"


@patch("app.agents.writer.llm_client")
def test_run_writer_handles_missing_references_key(mock_llm_client):
    response = _valid_llm_response()
    del response["references"]
    mock_llm_client.generate_json.return_value = response

    draft = run_writer("Research AI adoption", _make_tasks(), _make_evidence())

    assert draft.references == []


# ---------------------------------------------------------------------------
# Evidence-count truncation: select_evidence_for_writer() unit tests
# ---------------------------------------------------------------------------

# --- Requirement 13a: evidence count BELOW the limit ---

def test_select_evidence_below_limit_returns_all():
    """When evidence count <= max, all items are returned unchanged."""
    evidence = _make_evidence_list(5)
    selected = select_evidence_for_writer(evidence, max_items=10)

    assert len(selected) == 5
    for orig, sel in zip(evidence, selected):
        assert orig is sel  # same objects, not copies


def test_select_evidence_exactly_at_limit_returns_all():
    """Exactly at the limit must not truncate."""
    evidence = _make_evidence_list(10)
    selected = select_evidence_for_writer(evidence, max_items=10)
    assert len(selected) == 10


# --- Requirement 13b: evidence count ABOVE the limit ---

def test_select_evidence_above_limit_truncates_to_max():
    """When evidence exceeds the limit, at most max_items are returned."""
    evidence = _make_evidence_list(35)
    selected = select_evidence_for_writer(evidence, max_items=20)
    assert len(selected) == 20


def test_select_evidence_prefers_high_confidence():
    """High-confidence items are kept over low-confidence items."""
    low_evidence = _make_evidence_list(5, confidence=ConfidenceLevel.LOW)
    high_evidence = _make_evidence_list(5, confidence=ConfidenceLevel.HIGH)
    combined = low_evidence + high_evidence

    selected = select_evidence_for_writer(combined, max_items=5)

    assert len(selected) == 5
    for ev in selected:
        assert ev.confidence == ConfidenceLevel.HIGH


def test_select_evidence_stable_order_within_confidence_band():
    """Within the same confidence band, original order is preserved."""
    evidence = _make_evidence_list(10, confidence=ConfidenceLevel.MEDIUM)
    selected = select_evidence_for_writer(evidence, max_items=5)

    assert len(selected) == 5
    expected_claims = [f"Claim number {i}" for i in range(1, 6)]
    actual_claims = [ev.claim for ev in selected]
    assert actual_claims == expected_claims


def test_select_evidence_does_not_mutate_original_list():
    """select_evidence_for_writer() must never modify the original list."""
    evidence = _make_evidence_list(35)
    original_len = len(evidence)
    original_ids = [id(ev) for ev in evidence]

    _ = select_evidence_for_writer(evidence, max_items=10)

    assert len(evidence) == original_len
    assert [id(ev) for ev in evidence] == original_ids


# --- Requirement 13c: citation/source mapping after truncation ---

def test_citation_metadata_preserved_after_truncation():
    """
    source_id and citation_num on selected Evidence objects must survive
    truncation so the Writer/citation system can resolve references.
    """
    evidence = _make_evidence_list(30)
    selected = select_evidence_for_writer(evidence, max_items=10)

    assert len(selected) == 10
    for ev in selected:
        assert ev.source_id, "source_id should be set after truncation"
        assert ev.citation_num is not None, "citation_num should survive truncation"
        assert ev.source_url is not None, "source_url should survive truncation"


def test_truncated_items_are_evidence_objects():
    """Selected items are real Evidence objects, not stripped dicts."""
    evidence = _make_evidence_list(25)
    selected = select_evidence_for_writer(evidence, max_items=10)

    for ev in selected:
        assert isinstance(ev, Evidence)


# --- Requirement 13d: configuration override ---

def test_configuration_override_via_max_items_arg():
    """Passing max_items directly overrides the settings value."""
    evidence = _make_evidence_list(35)
    selected = select_evidence_for_writer(evidence, max_items=5)
    assert len(selected) == 5


def test_uses_settings_default_when_max_items_is_none():
    """When max_items=None, falls back to settings.MAX_EVIDENCE_FOR_WRITER."""
    evidence = _make_evidence_list(5)
    with patch("app.agents.writer.settings") as mock_settings:
        mock_settings.MAX_EVIDENCE_FOR_WRITER = 3
        selected = select_evidence_for_writer(evidence, max_items=None)

    assert len(selected) == 3


# ---------------------------------------------------------------------------
# Integration: run_writer respects truncation (mocked LLM)
# ---------------------------------------------------------------------------

@patch("app.agents.writer.llm_client")
def test_run_writer_truncates_large_evidence_list(mock_llm_client):
    """
    With 35 evidence items and a cap of 20, the Writer LLM is called
    with at most 20 items in its prompt (preventing HTTP 413).
    The original list is untouched.
    """
    mock_llm_client.generate_json.return_value = _valid_llm_response()
    evidence = _make_evidence_list(35)

    with patch("app.agents.writer.settings") as mock_settings:
        mock_settings.MAX_EVIDENCE_FOR_WRITER = 20
        run_writer("Research AI adoption", _make_tasks(), evidence)

    # Original evidence is unmodified
    assert len(evidence) == 35

    # At most 20 items should appear in the LLM prompt
    call_kwargs = mock_llm_client.generate_json.call_args
    prompt_text = call_kwargs.kwargs.get("prompt") or (
        call_kwargs.args[0] if call_kwargs.args else ""
    )
    claim_count = prompt_text.count("Claim number")
    assert claim_count <= 20


@patch("app.agents.writer.llm_client")
def test_run_writer_settings_override_reflected_in_prompt(mock_llm_client):
    """
    Patching settings.MAX_EVIDENCE_FOR_WRITER limits evidence in the LLM prompt.
    """
    evidence = _make_evidence_list(35)
    mock_llm_client.generate_json.return_value = _valid_llm_response()

    with patch("app.agents.writer.settings") as mock_settings:
        mock_settings.MAX_EVIDENCE_FOR_WRITER = 10
        run_writer("Research AI adoption", _make_tasks(), evidence)

    call_kwargs = mock_llm_client.generate_json.call_args
    prompt_text = call_kwargs.kwargs.get("prompt") or (
        call_kwargs.args[0] if call_kwargs.args else ""
    )
    claim_count = prompt_text.count("Claim number")
    assert claim_count <= 10, (
        f"Expected at most 10 evidence items in prompt, found {claim_count}"
    )


@patch("app.agents.writer.llm_client")
def test_run_writer_sources_preserved_after_truncation(mock_llm_client):
    """
    Sources provided to run_writer are passed through to the draft report
    even when evidence is truncated, preserving the citation catalog.
    """
    mock_llm_client.generate_json.return_value = _valid_llm_response()
    evidence = _make_evidence_list(35)
    sources = [
        Source(
            source_id="source_1",
            citation_num=1,
            citation="[1]",
            title="Important Source",
            url="https://example.com/important",
        )
    ]

    with patch("app.agents.writer.settings") as mock_settings:
        mock_settings.MAX_EVIDENCE_FOR_WRITER = 5
        draft = run_writer("Research AI adoption", _make_tasks(), evidence, sources=sources)

    # Real sources should be used as references (not LLM-generated ones)
    assert len(draft.references) == 1
    assert draft.references[0].title == "Important Source"