"""
Tests for section_normalizer utility.
"""

from app.utils.section_normalizer import clean_section_title, normalize_report_dict


def test_clean_section_title_strips_numeric_and_markdown_prefixes():
    cases = [
        ("1. Executive Summary", "Executive Summary"),
        ("## 1. Executive Summary", "Executive Summary"),
        ("### 2) Key Findings & Evidence", "Key Findings & Evidence"),
        ("1.1 - Technical Deep Dive", "Technical Deep Dive"),
        ("Section 3: Market Analysis", "Market Analysis"),
        ("IV. Strategic Conclusion", "Strategic Conclusion"),
        ("* 4. Recommendations", "Recommendations"),
        ("Pure Semantic Title", "Pure Semantic Title"),
    ]

    for raw, expected in cases:
        assert clean_section_title(raw) == expected


def test_normalize_report_dict_cleans_titles():
    report = {
        "title": "## 1. Comprehensive AI Study",
        "sections": [
            {"title": "1. Executive Summary", "content": "..."},
            {"title": "2. Key Findings", "content": "..."},
        ],
    }

    cleaned = normalize_report_dict(report)
    assert cleaned["title"] == "Comprehensive AI Study"
    assert cleaned["sections"][0]["title"] == "Executive Summary"
    assert cleaned["sections"][1]["title"] == "Key Findings"
