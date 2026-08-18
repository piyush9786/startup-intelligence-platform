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


# ADVISER_RESEARCH_QUALITY_V4
ADVISER_LIVE_TERMS = {
    "strategy",
    "strategic",
    "recommend",
    "recommendation",
    "best direction",
    "what should i do",
    "growth plan",
    "go to market",
    "go-to-market",
    "business model",
    "pricing",
    "success case",
    "successful startup",
    "successful startups",
    "failure",
    "failed startup",
    "failed startups",
    "shutdown",
    "opportunity",
    "opportunities",
    "accelerator",
    "incubator",
    "investor",
    "grant",
    "loan",
    "scheme",
    "market",
    "competition",
    "compare",
    "benchmark",
    "30 days",
    "60 days",
    "90 days",
}

INTERNAL_ONLY_TERMS = {
    "summarize my saved startup profile",
    "summarise my saved startup profile",
    "my readiness score",
    "my saved assessment",
    "my saved profile",
}

@dataclass(frozen=True)
class SearchDecision:
    required: bool
    reason: str


def decide_live_search(question: str) -> SearchDecision:
    """Determine whether a research question requires live external web search.

    Strategic founder-adviser questions are live by default because competitors,
    success/failure examples, market conditions and opportunities are time-sensitive.
    Explicitly internal-only questions can still stay on verified platform data.
    """
    normalized = " ".join(question.casefold().split())

    matching_terms = sorted(
        term for term in (LIVE_TERMS | ADVISER_LIVE_TERMS)
        if term in normalized
    )

    if matching_terms:
        return SearchDecision(
            required=True,
            reason=(
                "The request needs current external evidence for founder decision support: "
                + ", ".join(matching_terms)
            ),
        )

    internal_only = [
        term for term in INTERNAL_ONLY_TERMS
        if term in normalized
    ]
    if internal_only:
        return SearchDecision(
            required=False,
            reason="The request explicitly asks for saved internal startup information.",
        )

    return SearchDecision(
        required=False,
        reason="The request can be answered from internal verified platform data.",
    )
