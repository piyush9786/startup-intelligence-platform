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

    # Profile facts are authoritative. Question keywords are used only when
    # the corresponding structured facts are absent.
    q_words = re.findall(r"\b[a-zA-Z]{3,}\b", question.lower())
    keywords = [word for word in q_words if word not in QUESTION_STOP_WORDS]

    sub_industry = (
        profile.get("sub_industry")
        or profile.get("industry")
        or (" ".join(keywords[:2]) if keywords else industry)
    )
    target_users = (
        profile.get("target_audience")
        or profile.get("target_customer")
        or profile.get("customer_segment")
        or ["unspecified target users"]
    )

    return {
        "product": name or (" ".join(keywords[:2]) if keywords else "tech solution"),
        "industry": industry,
        "sub_industry": sub_industry,
        "target_users": target_users,
        "technology": technologies or (keywords[:2] if keywords else ["software"]),
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
    """Generate dynamic, sector-specific search queries from startup idea and question."""
    product = idea.get("product", "startup")
    industry = idea.get("industry", "technology")
    sub_ind = idea.get("sub_industry", "market")
    geo = idea.get("geography", "India")

    current_year = timezone.localdate().year
    previous_year = current_year - 1
    queries = [
        f"{product} {industry} startups {geo} {current_year}",
        f"{sub_ind} competitors market trends {geo}",
        f"{industry} startup funding rounds {geo} {previous_year} {current_year}",
        f"government schemes {industry} startups {geo}",
        f"{industry} regulatory requirements {geo}",
    ]

    # Clean and deduplicate queries
    clean_queries = [" ".join(q.split()) for q in queries]
    return list(dict.fromkeys(clean_queries))
