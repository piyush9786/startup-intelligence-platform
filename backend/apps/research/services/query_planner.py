"""Dynamic query planning and structured idea extraction service."""
from __future__ import annotations

import re
from typing import Any

from django.utils import timezone

QUESTION_STOP_WORDS = {
    "are",
    "build",
    "company",
    "competitor",
    "competitors",
    "current",
    "currently",
    "for",
    "how",
    "latest",
    "market",
    "new",
    "product",
    "recent",
    "startup",
    "the",
    "trend",
    "trends",
    "want",
    "what",
    "when",
    "where",
    "which",
    "who",
}


def extract_structured_idea(
    profile_data: dict[str, Any] | None,
    question: str,
) -> dict[str, Any]:
    """Extract a dynamic, structured startup idea representation from profile data & question."""
    profile = profile_data or {}
    name = profile.get("startup_name") or ""

    sectors = profile.get("sectors") or []
    industry = sectors[0] if sectors else "technology"

    technologies = profile.get("technologies") or []
    stage = profile.get("stage") or "idea"
    geography = profile.get("state") or profile.get("country") or "India"

    # Profile facts are authoritative. Question keywords are used only
    # for genuinely specific founder questions. Broad automatic research
    # instructions must not become startup domain facts.
    question_lower = question.lower()

    q_words = re.findall(
        r"\b[a-zA-Z]{3,}\b",
        question_lower,
    )

    keywords = [
        word
        for word in q_words
        if word not in QUESTION_STOP_WORDS
    ]

    broad_research_markers = (
        "comprehensive founder research report",
        "comprehensive research report",
        "analyze current competitors",
    )

    broad_research_request = any(
        marker in question_lower
        for marker in broad_research_markers
    )

    domain_keywords = (
        []
        if broad_research_request
        else keywords
    )

    sub_industry = (
        profile.get("sub_industry")
        or profile.get("industry")
        or (
            " ".join(domain_keywords[:2])
            if domain_keywords
            else industry
        )
    )
    target_users = (
        profile.get("target_audience")
        or profile.get("target_customer")
        or profile.get("customer_segment")
        or ["unspecified target users"]
    )

    return {
        "product": (
            name
            or (
                " ".join(domain_keywords[:2])
                if domain_keywords
                else "tech solution"
            )
        ),
        "industry": industry,
        "sub_industry": sub_industry,
        "target_users": target_users,
        "technology": (
            technologies
            or (
                domain_keywords[:2]
                if domain_keywords
                else []
            )
        ),
        "geography": geography,
        "stage": stage,
        "revenue_model": (
            profile.get("revenue_model")
            or profile.get("business_model")
            or "unspecified"
        ),
    }


def generate_search_queries(
    idea: dict[str, Any],
    question: str,
) -> list[str]:
    """Generate search queries only for the founder's requested intent."""
    from apps.research.services.research_intent import (
        BROAD_RESEARCH,
        COMPLIANCE,
        COMPETITORS,
        FAILURE_CASES,
        FUNDING,
        MARKET,
        PRICING,
        SCHEMES,
        SUCCESS_CASES,
        detect_research_intents,
    )

    def as_text(value: Any) -> str:
        if isinstance(value, (list, tuple, set)):
            return " ".join(
                str(item).strip()
                for item in value
                if str(item).strip()
            )
        return str(value or "").strip()

    industry = as_text(
        idea.get("industry")
    ) or "technology"

    sub_industry = as_text(
        idea.get("sub_industry")
    ) or industry

    technology = as_text(
        idea.get("technology")
    ) or sub_industry

    target_users = as_text(
        idea.get("target_users")
    )

    startup_geo = as_text(
        idea.get("geography")
    ) or "India"

    current_year = timezone.localdate().year
    previous_year = current_year - 1

    intents = detect_research_intents(question)

    queries: list[str] = []

    if COMPETITORS in intents:
        queries.extend(
            [
                (
                    f"{sub_industry} competitors companies "
                    f"India {current_year}"
                ),
                (
                    f"{sub_industry} startups India "
                    f"{current_year}"
                ),
                (
                    f"{technology} {sub_industry} "
                    f"companies India alternatives"
                ),
                (
                    f"{target_users} {sub_industry} "
                    f"vendors companies India"
                    if target_users
                    else (
                        f"{sub_industry} vendors "
                        f"companies India"
                    )
                ),
                (
                    f"{sub_industry} competitor landscape "
                    f"{startup_geo} India {current_year}"
                ),
            ]
        )

    if SUCCESS_CASES in intents:
        queries.extend(
            [
                (
                    f"successful {sub_industry} startups "
                    f"India {previous_year} {current_year}"
                ),
                (
                    f"{sub_industry} startup success "
                    f"case study India"
                ),
                (
                    f"{sub_industry} startup growth "
                    f"funding customers India"
                ),
            ]
        )

    if FAILURE_CASES in intents:
        queries.extend(
            [
                (
                    f"{sub_industry} startup failures "
                    f"shutdown India"
                ),
                (
                    f"{sub_industry} startup failed "
                    f"case study lessons India"
                ),
                (
                    f"{sub_industry} startup shutdown "
                    f"reasons India"
                ),
            ]
        )

    if MARKET in intents:
        queries.extend(
            [
                (
                    f"{sub_industry} market trends "
                    f"India {current_year}"
                ),
                (
                    f"{sub_industry} market demand "
                    f"India {current_year}"
                ),
                (
                    f"{sub_industry} industry growth "
                    f"India {current_year}"
                ),
            ]
        )

    if FUNDING in intents:
        queries.extend(
            [
                (
                    f"{sub_industry} startup funding "
                    f"India {previous_year} {current_year}"
                ),
                (
                    f"{sub_industry} investors venture "
                    f"capital India"
                ),
                (
                    f"{sub_industry} accelerator "
                    f"incubator India"
                ),
            ]
        )

    if SCHEMES in intents:
        queries.extend(
            [
                (
                    f"government schemes {industry} "
                    f"startups India {current_year}"
                ),
                (
                    f"{industry} startup grants "
                    f"India government"
                ),
                (
                    f"{industry} startup subsidy "
                    f"{startup_geo} India"
                ),
            ]
        )

    if COMPLIANCE in intents:
        queries.extend(
            [
                (
                    f"{industry} regulatory requirements "
                    f"India {current_year}"
                ),
                (
                    f"{sub_industry} compliance "
                    f"certification India"
                ),
                (
                    f"{sub_industry} licenses "
                    f"regulations India"
                ),
            ]
        )

    if PRICING in intents:
        queries.extend(
            [
                (
                    f"{sub_industry} pricing business "
                    f"model India"
                ),
                (
                    f"{sub_industry} revenue model "
                    f"companies India"
                ),
                (
                    f"{sub_industry} customer pricing "
                    f"India"
                ),
            ]
        )

    if BROAD_RESEARCH in intents:
        queries.extend(
            [
                (
                    f"{sub_industry} competitors "
                    f"startups India {current_year}"
                ),
                (
                    f"{sub_industry} market trends "
                    f"India {current_year}"
                ),
                (
                    f"{sub_industry} startup success "
                    f"failure case studies India"
                ),
                (
                    f"{sub_industry} funding investors "
                    f"India {current_year}"
                ),
                (
                    f"{industry} government schemes "
                    f"regulatory requirements India"
                ),
            ]
        )

    cleaned = [
        " ".join(query.split())
        for query in queries
        if query.strip()
    ]

    # Preserve order while removing duplicates.
    return list(dict.fromkeys(cleaned))[:6]
