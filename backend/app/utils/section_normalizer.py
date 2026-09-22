"""
Section normalizer utility.

Normalizes section titles by stripping LLM-generated numeric prefixes,
Roman numerals, and markdown heading markers.
Ensures that the report renderer remains the single source of truth
for canonical, sequential section numbering (preventing '1. 1.' double numbering).
"""

from __future__ import annotations

import re
from typing import Any


def clean_section_title(raw_title: str) -> str:
    """
    Clean a section title by stripping markdown headers, leading digits,
    and punctuation prefixes to yield a clean semantic title.

    Examples:
        '## 1. Executive Summary' -> 'Executive Summary'
        '1.2 Technical Architecture' -> 'Technical Architecture'
        '1.1 - Technical Deep Dive' -> 'Technical Deep Dive'
        'Section 3: Market Analysis' -> 'Market Analysis'
        '2) Market Dynamics' -> 'Market Dynamics'
    """
    if not raw_title or not isinstance(raw_title, str):
        return ""

    cleaned = raw_title.strip()

    for _ in range(3):
        prev = cleaned
        # 1. Strip markdown header hashes & bullets: "## ", "* ", "- "
        cleaned = re.sub(r"^[\#\*\-\•\:\.\s]+", "", cleaned)
        # 2. Strip "Section 1:", "Part 2 -", "Chapter 3."
        cleaned = re.sub(r"^(?:section|part|chapter)\s+\d+[\.\:\-\s]*\s*", "", cleaned, flags=re.IGNORECASE)
        # 3. Strip numbers, decimals, Roman numerals with trailing delimiters
        cleaned = re.sub(r"^(?:(?:\d+(?:\.\d+)*|[IVXLCDM]+)[\.\)\:\-\s]+)+", "", cleaned, flags=re.IGNORECASE)
        if cleaned == prev:
            break

    cleaned = cleaned.strip(" .:-")

    return cleaned if cleaned else raw_title.strip()


def normalize_report_dict(report_data: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively clean section titles in a serialized FinalReport dictionary.
    """
    if not isinstance(report_data, dict):
        return report_data

    # Clean top-level title
    if "title" in report_data and isinstance(report_data["title"], str):
        report_data["title"] = clean_section_title(report_data["title"])

    # Clean sections
    sections = report_data.get("sections")
    if isinstance(sections, list):
        for sec in sections:
            if isinstance(sec, dict) and "title" in sec:
                sec["title"] = clean_section_title(sec["title"])

    return report_data
