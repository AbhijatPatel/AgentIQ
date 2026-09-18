
from app.graph.state import (
    ConfidenceLevel,
    Evidence,
    EvidenceType,
)
from app.utils.evidence_quality import filter_valid_evidence


def create_evidence(
    claim: str,
    source_title: str,
) -> Evidence:
    return Evidence(
        task_id="1",
        claim=claim,
        source_title=source_title,
        source_url="https://example.com",
        type=EvidenceType.EVIDENCE,
        confidence=ConfidenceLevel.HIGH,
    )


def test_valid_evidence_is_preserved():
    evidence = [
        create_evidence(
            "Generative AI can improve developer productivity.",
            "Example Research",
        )
    ]

    result = filter_valid_evidence(evidence)

    assert len(result) == 1
    assert result[0].claim == (
        "Generative AI can improve developer productivity."
    )


def test_empty_claim_is_removed():
    evidence = [
        create_evidence("", "Example Research"),
        create_evidence("Valid claim", "Valid Source"),
    ]

    result = filter_valid_evidence(evidence)

    assert len(result) == 1
    assert result[0].claim == "Valid claim"


def test_empty_source_title_is_removed():
    evidence = [
        create_evidence("Claim without source", ""),
        create_evidence("Valid claim", "Valid Source"),
    ]

    result = filter_valid_evidence(evidence)

    assert len(result) == 1
    assert result[0].source_title == "Valid Source"


def test_whitespace_claim_is_removed():
    evidence = [
        create_evidence("   ", "Example Research"),
        create_evidence("Valid claim", "Valid Source"),
    ]

    result = filter_valid_evidence(evidence)

    assert len(result) == 1
    assert result[0].claim == "Valid claim"


def test_whitespace_source_title_is_removed():
    evidence = [
        create_evidence("Valid claim", "   "),
        create_evidence("Another valid claim", "Valid Source"),
    ]

    result = filter_valid_evidence(evidence)

    assert len(result) == 1
    assert result[0].source_title == "Valid Source"


def test_multiple_invalid_items_are_removed():
    evidence = [
        create_evidence("", "Source A"),
        create_evidence("Claim B", ""),
        create_evidence("   ", "Source C"),
        create_evidence("Valid claim", "Valid Source"),
    ]

    result = filter_valid_evidence(evidence)

    assert len(result) == 1
    assert result[0].claim == "Valid claim"


def test_empty_evidence_list():
    result = filter_valid_evidence([])

    assert result == []