"""Evidence extraction and confidence scoring service."""
from __future__ import annotations

from typing import Any

from .source_validator import (
    classify_source_type,
    compute_content_hash,
    compute_evidence_confidence,
    validate_source_url,
)
from .tavily_client import SearchResult


def extract_and_score_evidence(
    results: list[SearchResult],
    query: str,
) -> list[dict[str, Any]]:
    """Convert raw SearchResult list into validated, scored evidence items."""
    evidence_items: list[dict[str, Any]] = []

    for res in results:
        if not validate_source_url(res.url):
            continue

        stype = classify_source_type(res.url, res.publisher)
        relevance = float(res.score) if res.score is not None else 0.75
        conf_score, vstatus = compute_evidence_confidence(stype, relevance)

        chash = compute_content_hash(f"{res.url}:{res.content[:200]}")

        evidence_items.append(
            {
                "title": res.title,
                "url": res.url,
                "publisher": res.publisher or "Web Source",
                "published_at": res.published_at or "",
                "source_type": stype,
                "content_excerpt": res.content,
                "content_hash": chash,
                "confidence_score": conf_score,
                "verification_status": vstatus,
            }
        )

    return evidence_items
