"""
Grounded AI Scheme Application Proposal Draft Generator.
Synthesizes founder startup profile, traction metrics, and scheme requirements
into a pre-filled executive application proposal.
"""
from __future__ import annotations

import logging
from typing import Any

from apps.schemes.models import SchemeVersion
from apps.startups.models import StartupProfile

logger = logging.getLogger(__name__)


def generate_scheme_application_proposal(
    profile: StartupProfile,
    scheme_version: SchemeVersion,
) -> dict[str, Any]:
    """
    Generates a structured scheme application proposal draft pre-filled with founder data.
    """
    startup_name = profile.startup_name or "Startup Entity"
    legal_name = profile.legal_name or startup_name
    stage_display = profile.get_stage_display()
    sectors = ", ".join(profile.sectors) if profile.sectors else "General Technology"
    scheme_name = scheme_version.scheme.canonical_name

    executive_summary = (
        f"{startup_name} ({legal_name}) is an early-stage Indian startup operating "
        f"in the {sectors} sector at the {stage_display} stage. This application "
        f"proposal is formally submitted for the '{scheme_name}' programme to "
        "accelerate product validation and commercial deployment."
    )

    problem_statement = (
        profile.profile_data.get("problem_statement")
        or f"High operational costs and technological fragmentation in the {sectors} sector."
    )

    proposed_solution = (
        profile.profile_data.get("proposed_solution")
        or f"An innovative technological platform built by {startup_name} to streamline operations."
    )

    budget_utilization_plan = [
        {
            "category": "Product Development & R&D",
            "percentage": 40,
            "description": "Core software, IP, & prototyping",
        },
        {
            "category": "Go-to-Market & Acquisition",
            "percentage": 30,
            "description": "Direct customer acquisition & pilots",
        },
        {
            "category": "Team Expansion",
            "percentage": 20,
            "description": "Key technical & operational hires",
        },
        {
            "category": "Compliance & Reserve",
            "percentage": 10,
            "description": "Legal, IP filing, & 15% liquid reserve",
        },
    ]

    expected_impact = (
        f"Acquiring support through {scheme_name} will enable {startup_name} to "
        "expand headcount, scale monthly recurring revenues, and achieve "
        "self-sustaining commercial readiness within 12 months."
    )

    return {
        "proposal_title": f"Scheme Application Proposal — {scheme_name}",
        "startup_name": startup_name,
        "legal_name": legal_name,
        "scheme_id": str(scheme_version.scheme.id),
        "scheme_version_id": str(scheme_version.id),
        "scheme_name": scheme_name,
        "executive_summary": executive_summary,
        "problem_statement": problem_statement,
        "proposed_solution": proposed_solution,
        "budget_utilization_plan": budget_utilization_plan,
        "expected_impact": expected_impact,
        "dpiit_recognized": profile.dpiit_recognized,
        "annual_turnover": float(profile.annual_turnover or 0),
        "funding_required": float(profile.funding_required or 0),
        "generator_version": "ai-proposal-generator-v1",
    }
