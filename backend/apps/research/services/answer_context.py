"""Answer context assembly and pre-computed analytics service."""
from __future__ import annotations

from typing import Any


def calculate_capital_scenarios(stage: str = "idea") -> dict[str, Any]:
    """Calculate pre-computed scenario-based capital requirements outside LLM."""
    if stage in ("idea", "validation"):
        return {
            "lean_prototype": "₹2,50,000 - ₹5,00,000 ($3,000 - $6,000)",
            "pilot_and_certification": "₹8,00,000 - ₹15,00,000 ($10,000 - $18,000)",
            "commercial_launch": "₹25,00,000 - ₹50,00,000 ($30,000 - $60,000)",
            "assumptions": [
                "Hardware sensors and prototypes",
                "Mobile app development",
                "Testing and safety certification",
                "Initial batch manufacturing",
            ],
        }
    return {
        "lean_prototype": "₹5,00,000 - ₹10,00,000",
        "pilot_and_certification": "₹15,00,000 - ₹30,00,000",
        "commercial_launch": "₹50,00,000 - ₹1,00,00,000",
        "assumptions": [
            "Clinical or field validation pilot",
            "Regulatory compliance",
            "Marketing and distribution partner onboarding",
        ],
    }


def assemble_research_context(
    *,
    idea: dict[str, Any],
    local_evidence: list[dict[str, Any]],
    live_evidence: list[dict[str, Any]],
    readiness_score: int | None = None,
) -> dict[str, Any]:
    """Assemble final structured context and rules payload for local LLM generation."""
    computed_metrics = {
        "competition_level": "medium",
        "readiness_score": readiness_score if readiness_score is not None else 50,
        "estimated_capital_scenarios": calculate_capital_scenarios(idea.get("stage", "idea")),
        "market_concentration": "fragmented",
    }

    rules = [
        "Do not invent companies or statistics.",
        "Use only supplied evidence.",
        "Clearly separate verified internal data and live web evidence.",
        "Cite every current factual claim.",
        "Explain uncertainty.",
    ]

    return {
        "startup": idea,
        "local_evidence": local_evidence,
        "live_evidence": live_evidence,
        "computed_metrics": computed_metrics,
        "rules": rules,
    }
