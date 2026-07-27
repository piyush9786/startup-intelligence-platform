"""Query planning and structured idea extraction service."""
from __future__ import annotations

from typing import Any


def extract_structured_idea(
    profile_data: dict[str, Any] | None,
    question: str,
) -> dict[str, Any]:
    """Extract a structured startup idea representation for research planning."""
    profile = profile_data or {}
    q_lower = question.lower()

    # Product/domain inferencing
    product = profile.get("startup_name") or "Smart Tech Startup"
    if "wristband" in q_lower or "wearable" in q_lower or "elderly" in q_lower:
        product = "smart health wristband"

    industry = profile.get("sectors", [None])[0] if profile.get("sectors") else "health technology"
    sub_industry = "wearable healthcare devices" if "wristband" in q_lower else "technology"

    target_users = ["elderly people", "caregivers"] if "elderly" in q_lower else ["consumers"]
    technology = profile.get("technologies") or ["IoT", "sensors", "mobile app"]
    geography = profile.get("state") or profile.get("country") or "India"
    stage = profile.get("stage") or "idea"

    return {
        "product": product,
        "industry": industry,
        "sub_industry": sub_industry,
        "target_users": target_users,
        "technology": technology,
        "geography": geography,
        "stage": stage,
        "revenue_model": profile.get("revenue_model") or "device sale plus subscription",
    }


def generate_search_queries(
    idea: dict[str, Any],
    question: str,
) -> list[str]:
    """Generate focused, targeted search queries from idea and question."""
    product = idea.get("product", "startup")
    industry = idea.get("industry", "technology")
    geo = idea.get("geography", "India")

    queries = [
        f"{product} companies {geo} 2026",
        f"elderly monitoring wearable startups {geo}",
        f"{industry} startup funding {geo} 2025 2026",
        f"medical wearable device regulations {geo}",
        f"government schemes {industry} startup {geo}",
    ]

    return list(dict.fromkeys(queries))  # Deduplicate while preserving order
