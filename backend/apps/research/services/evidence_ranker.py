"""Evidence ranking and deduplication service."""
from __future__ import annotations

from typing import Any


def rank_and_deduplicate_evidence(
    items: list[dict[str, Any]],
    *,
    max_items: int = 12,
) -> list[dict[str, Any]]:
    """Deduplicate evidence items by content hash / URL and rank by confidence."""
    seen_hashes: set[str] = set()
    seen_urls: set[str] = set()
    deduped: list[dict[str, Any]] = []

    for item in items:
        h = item["content_hash"]
        u = item["url"].lower().rstrip("/")

        if h in seen_hashes or u in seen_urls:
            continue

        seen_hashes.add(h)
        seen_urls.add(u)
        deduped.append(item)

    # Rank by verification status authority first, then confidence score
    STATUS_WEIGHTS = {
        "official_live": 1.0,
        "verified_internal": 0.9,
        "reputable_secondary": 0.75,
        "unverified_live": 0.5,
        "rejected": 0.0,
    }

    deduped.sort(
        key=lambda x: (
            STATUS_WEIGHTS.get(x["verification_status"], 0.5),
            x["confidence_score"],
        ),
        reverse=True,
    )

    return deduped[:max_items]
