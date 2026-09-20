"""
Citation Engine & Source Normalization for AgentIQ (Module 29).

Provides:
- URL normalization (stripping fragments, trailing slashes, tracking parameters)
- Domain extraction (cleaning 'www.', port, safe fallback)
- Source normalization & metadata fallback
- Deterministic duplicate source detection & merging
- Deterministic 1-based citation numbering ([1], [2], ...)
- Claim-to-source mapping
- Programmatic citation reference validation
"""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from app.graph.state import Evidence, Source
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Query parameters commonly used for tracking that can be safely stripped
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
    "_hsenc",
    "_hsmi",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
}

# Regex to match citation patterns like [1], [2], [1][2], [1, 2]
CITATION_PATTERN = re.compile(r"\[(\d+)\]")


def normalize_url(url: Optional[str]) -> Optional[str]:
    """
    Safely normalize a URL for comparison and deduplication:
    - Strips whitespace
    - Lowercases scheme and netloc/hostname
    - Strips URL fragments (#...)
    - Strips common marketing/tracking query parameters
    - Normalizes trailing slashes (preserves single slash on domain root)
    - Returns None if URL is empty or unparseable
    """
    if not url or not isinstance(url, str):
        return None

    cleaned = url.strip()
    if not cleaned:
        return None

    # Handle protocol-relative or missing scheme (case-insensitive)
    lower_prefix = cleaned.lower()
    if lower_prefix.startswith("//"):
        cleaned = "https:" + cleaned
    elif not (lower_prefix.startswith("http://") or lower_prefix.startswith("https://")):
        # If it looks like a domain or path, don't crash
        if "." in cleaned and "/" not in cleaned.split(".")[0]:
            cleaned = "https://" + cleaned
        else:
            return cleaned.rstrip("/")

    try:
        parsed = urlparse(cleaned)
    except Exception as exc:
        logger.debug(f"URL parsing failed for {url!r}: {exc}")
        return cleaned.rstrip("/")

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Normalize default ports (http:80, https:443)
    if scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    elif scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]

    # Clean path: remove duplicate slashes, strip trailing slash unless path is just '/'
    path = re.sub(r"/+", "/", parsed.path)
    if path.endswith("/") and len(path) > 1:
        path = path.rstrip("/")

    # Strip tracking query params, keeping meaningful params like 'v' for YouTube
    filtered_query_params = []
    if parsed.query:
        try:
            query_dict = parse_qs(parsed.query, keep_blank_values=True)
            cleaned_params = {
                k: v for k, v in query_dict.items() if k.lower() not in TRACKING_PARAMS
            }
            filtered_query_params = [
                (k, val) for k, vals in cleaned_params.items() for val in vals
            ]
        except Exception:
            filtered_query_params = []

    clean_query = urlencode(filtered_query_params, doseq=True) if filtered_query_params else ""

    # Reconstruct without fragment
    normalized = urlunparse((
        scheme,
        netloc,
        path,
        "",  # params
        clean_query,
        "",  # fragment (removed)
    ))

    return normalized


def extract_domain(url: Optional[str]) -> Optional[str]:
    """
    Extract clean domain (e.g., 'example.com') from a URL:
    - Strips 'www.'
    - Strips port numbers
    - Returns None if URL is missing or domain cannot be parsed
    """
    if not url or not isinstance(url, str):
        return None

    cleaned = url.strip()
    if not cleaned:
        return None

    if not (cleaned.startswith("http://") or cleaned.startswith("https://") or cleaned.startswith("//")):
        cleaned = "https://" + cleaned

    try:
        parsed = urlparse(cleaned)
        netloc = parsed.netloc or parsed.path.split("/")[0]
        # Remove port if present
        host = netloc.split(":")[0].lower()
        if host.startswith("www."):
            host = host[4:]
        return host if host else None
    except Exception:
        return None


def create_source(
    raw_item: dict,
    source_type: str = "web",
    query: Optional[str] = None,
) -> Source:
    """
    Create a robust, normalized Source object from arbitrary raw search or tool data.
    Gracefully handles missing or malformed attributes.
    """
    if not isinstance(raw_item, dict):
        raw_item = {}

    raw_url = raw_item.get("url") or raw_item.get("link") or raw_item.get("source_url")
    normalized_url_val = normalize_url(raw_url) if raw_url else None

    # Title extraction with fallbacks
    title = (
        raw_item.get("title")
        or raw_item.get("name")
        or raw_item.get("filename")
        or (extract_domain(normalized_url_val) if normalized_url_val else None)
        or "Untitled Source"
    )
    title = str(title).strip() or "Untitled Source"

    # Domain extraction
    domain = raw_item.get("domain") or extract_domain(normalized_url_val)

    # Snippet / content
    snippet = raw_item.get("snippet") or raw_item.get("content") or raw_item.get("description")
    if snippet:
        snippet = str(snippet).strip()
        if len(snippet) > 400:
            snippet = snippet[:400] + "..."

    # Dates and author
    published_date = raw_item.get("published_date") or raw_item.get("date") or raw_item.get("published_at")
    author = raw_item.get("author") or raw_item.get("channel") or raw_item.get("uploader") or raw_item.get("photographer")

    return Source(
        title=title,
        url=normalized_url_val,
        domain=domain,
        source_type=source_type,
        snippet=snippet,
        published_date=str(published_date) if published_date else None,
        author=str(author) if author else None,
        query=query,
        metadata={
            k: v for k, v in raw_item.items()
            if k not in {"title", "url", "domain", "snippet", "content", "description"}
        },
    )


def deduplicate_sources(sources: list[Source]) -> list[Source]:
    """
    Deduplicate a list of sources:
    - Merges sources pointing to equivalent URLs or identical titles when URLs are missing.
    - Preserves first occurrence order.
    - Merges missing metadata (snippets, dates, authors) into the kept source.
    """
    unique_sources: list[Source] = []
    seen_keys: dict[str, int] = {}  # key -> index in unique_sources

    for src in sources:
        # Determine uniqueness key
        if src.url:
            norm = normalize_url(src.url)
            key = f"url:{norm.lower()}" if norm else f"title:{src.title.lower().strip()}"
        else:
            key = f"title:{src.title.lower().strip()}"

        if key in seen_keys:
            existing_idx = seen_keys[key]
            existing = unique_sources[existing_idx]
            # Merge richer metadata if existing lacks it
            if not existing.snippet and src.snippet:
                existing.snippet = src.snippet
            if not existing.published_date and src.published_date:
                existing.published_date = src.published_date
            if not existing.author and src.author:
                existing.author = src.author
            if not existing.domain and src.domain:
                existing.domain = src.domain
            if existing.metadata is not None and src.metadata:
                for mk, mv in src.metadata.items():
                    if mk not in existing.metadata:
                        existing.metadata[mk] = mv
            continue

        seen_keys[key] = len(unique_sources)
        unique_sources.append(src)

    return unique_sources


def assign_citation_numbers(sources: list[Source]) -> list[Source]:
    """
    Assign deterministic 1-based citation numbering ([1], [2], ...)
    and source_id ('source_1', 'source_2', ...) to all sources.
    """
    for idx, src in enumerate(sources, start=1):
        src.citation_num = idx
        src.citation = f"[{idx}]"
        src.source_id = f"source_{idx}"
    return sources


def map_evidence_to_sources(
    evidence_list: list[Evidence],
    sources: list[Source],
) -> list[Evidence]:
    """
    Map each evidence claim to its supporting canonical Source:
    - Matches by normalized URL first, then by matching normalized title.
    - Sets evidence.source_id and evidence.citation_num.
    """
    # URL lookup map
    url_to_source: dict[str, Source] = {}
    title_to_source: dict[str, Source] = {}

    for src in sources:
        if src.url:
            norm_url = normalize_url(src.url)
            if norm_url:
                url_to_source[norm_url.lower()] = src
        if src.title:
            clean_title = src.title.lower().strip()
            if clean_title and clean_title not in title_to_source:
                title_to_source[clean_title] = src

    for ev in evidence_list:
        matched: Optional[Source] = None

        if ev.source_url:
            norm_ev_url = normalize_url(ev.source_url)
            if norm_ev_url and norm_ev_url.lower() in url_to_source:
                matched = url_to_source[norm_ev_url.lower()]

        if not matched and ev.source_title:
            clean_ev_title = ev.source_title.lower().strip()
            if clean_ev_title in title_to_source:
                matched = title_to_source[clean_ev_title]

        if matched:
            ev.source_id = matched.source_id
            ev.citation_num = matched.citation_num

    return evidence_list


def format_source_catalog_for_prompt(sources: list[Source]) -> str:
    """
    Format collected sources into a clean markdown reference list
    to provide directly to the Writer Agent.
    """
    if not sources:
        return "(no sources collected)"

    lines = []
    for src in sources:
        num = src.citation_num or 1
        label = src.citation or f"[{num}]"
        domain_part = f" — {src.domain}" if src.domain else ""
        url_part = f" ({src.url})" if src.url else ""
        snippet_part = f"\n    Summary: {src.snippet}" if src.snippet else ""
        lines.append(f"{label} {src.title}{domain_part}{url_part}{snippet_part}")

    return "\n".join(lines)


def validate_citations_in_text(
    text: str,
    valid_citation_nums: set[int],
) -> dict:
    """
    Validate citation numbers referenced in report text:
    - Finds all [N] occurrences.
    - Checks whether each N belongs to valid_citation_nums.
    - Returns structured summary.
    """
    found_citations = [int(m) for m in CITATION_PATTERN.findall(text)]
    unique_found = sorted(set(found_citations))

    valid_refs = [n for n in unique_found if n in valid_citation_nums]
    invalid_refs = [n for n in unique_found if n not in valid_citation_nums]

    return {
        "total_citations_found": len(found_citations),
        "unique_citations_found": unique_found,
        "valid_citations": valid_refs,
        "invalid_citations": invalid_refs,
        "is_valid": len(invalid_refs) == 0,
    }
