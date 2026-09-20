import pytest
from app.graph.state import Evidence, Source
from app.utils.citation_engine import (
    assign_citation_numbers,
    create_source,
    deduplicate_sources,
    extract_domain,
    format_source_catalog_for_prompt,
    map_evidence_to_sources,
    normalize_url,
    validate_citations_in_text,
)


def test_normalize_url_trailing_slashes_and_fragments():
    url1 = "https://example.com/article/"
    url2 = "https://example.com/article"
    url3 = "https://example.com/article#section-1"
    url4 = "HTTPS://EXAMPLE.COM/article?utm_source=twitter"

    assert normalize_url(url1) == "https://example.com/article"
    assert normalize_url(url2) == "https://example.com/article"
    assert normalize_url(url3) == "https://example.com/article"
    assert normalize_url(url4) == "https://example.com/article"


def test_normalize_url_preserves_query_params():
    yt_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&utm_medium=email"
    normalized = normalize_url(yt_url)
    assert "v=dQw4w9WgXcQ" in normalized
    assert "utm_medium" not in normalized


def test_normalize_url_handles_edge_cases():
    assert normalize_url("") is None
    assert normalize_url(None) is None
    assert normalize_url("   ") is None
    assert normalize_url("not-a-url") == "not-a-url"


def test_extract_domain():
    assert extract_domain("https://www.example.com/article/test") == "example.com"
    assert extract_domain("https://sub.domain.org/page") == "sub.domain.org"
    assert extract_domain("http://localhost:8000/api") == "localhost"
    assert extract_domain("www.techcrunch.com/post") == "techcrunch.com"
    assert extract_domain("") is None
    assert extract_domain(None) is None


def test_create_source_fallbacks():
    # Completely empty raw item
    src1 = create_source({}, source_type="web")
    assert src1.title == "Untitled Source"
    assert src1.url is None
    assert src1.source_type == "web"

    # Minimal item with url
    src2 = create_source({"url": "https://ai.google/research/"}, source_type="web")
    assert src2.domain == "ai.google"
    assert src2.url == "https://ai.google/research"

    # Full item
    src3 = create_source(
        {
            "title": "Quantum AI",
            "url": "https://example.com/quantum#intro",
            "snippet": "Exciting breakthrough in quantum computing...",
            "published_date": "2026-09-01",
            "author": "Dr. Smith",
        },
        source_type="web",
    )
    assert src3.title == "Quantum AI"
    assert src3.snippet.startswith("Exciting breakthrough")
    assert src3.published_date == "2026-09-01"
    assert src3.author == "Dr. Smith"


def test_deduplicate_sources_and_merge():
    src1 = create_source(
        {"title": "AI Paper", "url": "https://arxiv.org/abs/12345/"},
        source_type="web",
    )
    src2 = create_source(
        {
            "title": "AI Paper",
            "url": "https://arxiv.org/abs/12345#full",
            "snippet": "A comprehensive study on neural networks.",
            "author": "Alice",
        },
        source_type="web",
    )
    src3 = create_source(
        {"title": "Different Article", "url": "https://nature.com/articles/456"},
        source_type="web",
    )

    deduped = deduplicate_sources([src1, src2, src3])
    assert len(deduped) == 2
    assert deduped[0].snippet == "A comprehensive study on neural networks."
    assert deduped[0].author == "Alice"
    assert deduped[1].title == "Different Article"


def test_assign_citation_numbers():
    sources = [
        create_source({"title": "First", "url": "https://a.com"}),
        create_source({"title": "Second", "url": "https://b.com"}),
        create_source({"title": "Third", "url": "https://c.com"}),
    ]
    numbered = assign_citation_numbers(sources)

    assert numbered[0].citation_num == 1
    assert numbered[0].citation == "[1]"
    assert numbered[0].source_id == "source_1"

    assert numbered[1].citation_num == 2
    assert numbered[1].citation == "[2]"
    assert numbered[1].source_id == "source_2"

    assert numbered[2].citation_num == 3
    assert numbered[2].citation == "[3]"
    assert numbered[2].source_id == "source_3"


def test_map_evidence_to_sources():
    sources = assign_citation_numbers([
        create_source({"title": "Attention Is All You Need", "url": "https://arxiv.org/abs/1706.03762"}),
        create_source({"title": "BERT: Pre-training", "url": "https://arxiv.org/abs/1810.04805"}),
    ])

    evidence = [
        Evidence(
            task_id=1,
            claim="Transformers use self-attention mechanism.",
            source_title="Attention Is All You Need",
            source_url="https://arxiv.org/abs/1706.03762/",
        ),
        Evidence(
            task_id=2,
            claim="BERT utilizes masked language modeling.",
            source_title="BERT: Pre-training",
            source_url=None,
        ),
        Evidence(
            task_id=3,
            claim="Unrelated claim with no matching source.",
            source_title="Nonexistent Source",
            source_url="https://nowhere.org",
        ),
    ]

    mapped = map_evidence_to_sources(evidence, sources)

    assert mapped[0].source_id == "source_1"
    assert mapped[0].citation_num == 1

    assert mapped[1].source_id == "source_2"
    assert mapped[1].citation_num == 2

    assert mapped[2].source_id is None
    assert mapped[2].citation_num is None


def test_format_source_catalog_for_prompt():
    sources = assign_citation_numbers([
        create_source({
            "title": "AgentIQ Guide",
            "url": "https://agentiq.dev",
            "snippet": "Framework for multi-agent workflows.",
        }),
    ])

    catalog = format_source_catalog_for_prompt(sources)
    assert "[1] AgentIQ Guide" in catalog
    assert "agentiq.dev" in catalog
    assert "Framework for multi-agent workflows" in catalog


def test_validate_citations_in_text():
    text = (
        "AI models have improved productivity [1]. "
        "Further studies corroborate these findings [2][3]. "
        "However, some claims cite an invalid reference [99]."
    )

    valid_nums = {1, 2, 3}
    report = validate_citations_in_text(text, valid_nums)

    assert report["total_citations_found"] == 4
    assert set(report["valid_citations"]) == {1, 2, 3}
    assert report["invalid_citations"] == [99]
    assert report["is_valid"] is False

    # All valid test
    valid_text = "Adoption is growing [1][2]."
    valid_report = validate_citations_in_text(valid_text, {1, 2, 3})
    assert valid_report["is_valid"] is True
    assert valid_report["invalid_citations"] == []
