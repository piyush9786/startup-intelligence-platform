"""Search decision router service."""
from __future__ import annotations

from dataclasses import dataclass

LIVE_TERMS = {
    "latest",
    "recent",
    "currently",
    "current",
    "today",
    "this year",
    "new competitor",
    "market trend",
    "recent funding",
    "deadline",
    "application date",
    "regulation",
    "news",
    "competitors",
    "competitor",
    "market situation",
    "market size",
    "funding options",
}


@dataclass(frozen=True)
class SearchDecision:
    required: bool
    reason: str


def decide_live_search(question: str) -> SearchDecision:
    """Determine whether a research question requires live external web search."""
    normalized = " ".join(question.casefold().split())

    matching_terms = [
        term for term in LIVE_TERMS
        if term in normalized
    ]

    if matching_terms:
        return SearchDecision(
            required=True,
            reason=(
                "The request depends on dynamic or time-sensitive market data: "
                + ", ".join(matching_terms)
            ),
        )

    return SearchDecision(
        required=False,
        reason="The request can be answered from internal verified platform data.",
    )
