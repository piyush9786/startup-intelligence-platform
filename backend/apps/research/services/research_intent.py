"""Deterministic research-intent detection for founder questions."""
from __future__ import annotations


COMPETITORS = "competitors"
SUCCESS_CASES = "success_cases"
FAILURE_CASES = "failure_cases"
MARKET = "market"
FUNDING = "funding"
SCHEMES = "schemes"
COMPLIANCE = "compliance"
PRICING = "pricing"
BROAD_RESEARCH = "broad_research"


def detect_research_intents(question: str) -> set[str]:
    """Return the research topics explicitly requested by the founder."""
    q = (question or "").lower()

    intents: set[str] = set()

    if any(
        term in q
        for term in (
            "competitor",
            "competitors",
            "competition",
            "competitive",
            "rival",
            "rivals",
            "alternative",
            "alternatives",
        )
    ):
        intents.add(COMPETITORS)

    if any(
        term in q
        for term in (
            "successful startup",
            "successful startups",
            "success case",
            "success cases",
            "why they succeeded",
            "why it succeeded",
        )
    ):
        intents.add(SUCCESS_CASES)

    if any(
        term in q
        for term in (
            "failed startup",
            "failed startups",
            "startup failure",
            "startup failures",
            "shutdown",
            "shut down",
            "why they failed",
            "why it failed",
        )
    ):
        intents.add(FAILURE_CASES)

    if any(
        term in q
        for term in (
            "market",
            "market trend",
            "market trends",
            "demand",
            "market size",
            "industry trend",
            "industry trends",
        )
    ):
        intents.add(MARKET)

    if any(
        term in q
        for term in (
            "funding",
            "fundraise",
            "fundraising",
            "investor",
            "investors",
            "investment",
            "venture capital",
            "capital raise",
        )
    ):
        intents.add(FUNDING)

    if any(
        term in q
        for term in (
            "government scheme",
            "government schemes",
            "scheme",
            "schemes",
            "grant",
            "grants",
            "subsidy",
            "subsidies",
        )
    ):
        intents.add(SCHEMES)

    if any(
        term in q
        for term in (
            "compliance",
            "regulation",
            "regulatory",
            "certification",
            "certifications",
            "license",
            "licence",
            "legal requirement",
        )
    ):
        intents.add(COMPLIANCE)

    if any(
        term in q
        for term in (
            "pricing",
            "price",
            "business model",
            "revenue model",
            "monetization",
            "monetisation",
        )
    ):
        intents.add(PRICING)

    return intents or {BROAD_RESEARCH}
