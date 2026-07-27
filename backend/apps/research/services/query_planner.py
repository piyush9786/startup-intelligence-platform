"""Dynamic query planning and structured idea extraction service."""
from __future__ import annotations

import re
from typing import Any


def extract_structured_idea(
    profile_data: dict[str, Any] | None,
    question: str,
) -> dict[str, Any]:
    """Extract a dynamic, structured startup idea representation from profile data & question."""
    profile = profile_data or {}
    name = profile.get("startup_name") or "Tech Startup"

    sectors = profile.get("sectors") or []
    industry = sectors[0] if sectors else "technology"

    technologies = profile.get("technologies") or []
    stage = profile.get("stage") or "idea"
    geography = profile.get("state") or profile.get("country") or "India"

    # Dynamic target user extraction from question/profile
    q_words = re.findall(r"\b[a-zA-Z]{3,}\b", question.lower())
    ignored = {"what", "who", "where", "when", "how", "build", "want", "startup", "company", "product", "the", "and", "for"}
    keywords = [w for w in q_words if w not in ignored]

    sub_industry = keywords[0] if keywords else industry
    target_users = profile.get("target_audience") or (keywords[1:] if len(keywords) > 1 else ["target customers"])

    return {
        "product": name if name != "Tech Startup" else (keywords[0] if keywords else "tech solution"),
        "industry": industry,
        "sub_industry": sub_industry,
        "target_users": target_users,
        "technology": technologies or (keywords[:2] if keywords else ["software"]),
        "geography": geography,
        "stage": stage,
        "revenue_model": profile.get("revenue_model") or "B2B / B2C subscription",
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

    queries = [
        f"{product} {industry} startups {geo} 2026",
        f"{sub_ind} competitors market trends {geo}",
        f"{industry} startup funding rounds {geo} 2025 2026",
        f"government schemes {industry} startups {geo}",
        f"{industry} regulatory requirements {geo}",
    ]

    # Clean and deduplicate queries
    clean_queries = [" ".join(q.split()) for q in queries]
    return list(dict.fromkeys(clean_queries))
