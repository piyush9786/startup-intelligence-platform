"""
Startup Executive Resume & Pitch One-Pager Generator.
Generates a structured, context-aware one-page startup executive resume document
tailored dynamically to the founder's specific idea concept.
"""
from __future__ import annotations

import logging
from typing import Any

from apps.startups.models import StartupProfile
from apps.startups.services.builder_consultant_service import (
    _generate_sector_context_intelligence,
)

logger = logging.getLogger(__name__)


def generate_startup_executive_resume(
    *,
    idea_description: str,
    sector: str = "Technology / General",
    stage: str = "Idea / Prototype",
    funding_required: str = "₹25 Lakhs",
    profile: StartupProfile | None = None,
) -> dict[str, Any]:
    """
    Synthesizes minimal founder inputs into a One-Page Startup Executive Resume / Pitch Teaser.
    """
    idea = idea_description.strip()

    # Synthesize context intelligence
    intel = _generate_sector_context_intelligence(idea, sector, stage, funding_required)
    startup_title = intel.get("generated_title") or (
        profile.startup_name if (profile and profile.startup_name) else "Startup Entity"
    )

    bp = intel.get("business_plan", {})
    schemes_raw = intel.get("recommended_schemes", [])
    idea_und = intel.get("idea_understanding", {})

    resume_header = {
        "startup_name": startup_title,
        "tagline": idea_und.get("value_proposition")
        or f"An innovative {sector} platform transforming '{idea}'.",
        "sector": sector,
        "stage": stage,
        "funding_target": funding_required,
        "document_type": "AI-DRAFTED STARTUP EXECUTIVE ONE-PAGER",
        "version": "Draft v2 — Unverified Strategic Hypothesis",
    }

    executive_summary = (
        f"{startup_title} is an early-stage Indian startup operating in the "
        f"{sector} space at the {stage} stage. {idea_und.get('core_concept', '')} "
        f"{idea_und.get('market_opportunity', '')}"
    )

    prob_stmt = bp.get("problem", {}).get("problem_statement", f"High friction in '{idea}'.")
    sol_stmt = bp.get("business_model", {}).get(
        "value_proposition",
        f"A proposed lower-friction workflow for customers dealing with '{idea}'.",
    )
    cust_stmt = bp.get("customer", {}).get(
        "primary_customer_segment", "Target industry buyers."
    )
    rev_stmt = bp.get("business_model", {}).get("revenue_model", "Tiered subscription model.")

    core_pillars = [
        {"title": "Problem Statement", "icon": "🎯", "content": prob_stmt},
        {"title": "Proposed Solution", "icon": "🚀", "content": sol_stmt},
        {"title": "Target Customer Persona", "icon": "👥", "content": cust_stmt},
        {"title": "Business & Monetization Model", "icon": "💎", "content": rev_stmt},
    ]

    matched_schemes = [
        {
            "scheme_name": scheme.get("name", "Potential government scheme"),
            "authority": "Verify with the official scheme authority",
            "support": (
                "Current support terms must be verified on the official scheme page."
            ),
            "match_badge": "Suggested fit — not eligibility assessed",
            "summary": (
                "This is an unverified scheme idea. Confirm current availability, "
                "eligibility rules and benefit terms before relying on it."
            ),
            "is_verified": False,
        }
        for scheme in schemes_raw
        if isinstance(scheme, dict)
    ]

    execution_roadmap = intel.get("execution_roadmap", [])
    consultant_insights = intel.get("consultant_recommendations", {})

    return {
        "resume_header": resume_header,
        "executive_summary": executive_summary,
        "core_pillars": core_pillars,
        "matched_schemes": matched_schemes,
        "execution_roadmap": execution_roadmap,
        "consultant_insights": consultant_insights,
        "trust_level": "suggested_hypothesis",
        "requires_verification": True,
        "generator_version": "startup-executive-resume-v2",
    }
