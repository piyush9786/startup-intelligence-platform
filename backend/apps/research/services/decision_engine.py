"""Normalization helpers for evidence-backed adviser decisions."""
from __future__ import annotations

from typing import Any

# ADVISER_DECISION_INTELLIGENCE_V1

LIST_DEFAULT_FIELDS = (
    "benefits", "success_cases", "failure_cases", "application_opportunities",
    "major_challenges", "risk_mitigations", "strategic_options",
    "decision_comparison", "conditions_that_change_decision", "immediate_actions",
    "thirty_day_plan", "sixty_day_plan", "ninety_day_plan",
)

STRING_DEFAULT_FIELDS = ("recommended_direction", "recommendation_reason")


def _valid_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def normalize_adviser_report(
    payload: dict[str, Any],
    *,
    valid_urls: set[str] | None = None,
) -> dict[str, Any]:
    """Add adviser fields without inventing evidence or changing legacy fields."""
    report = dict(payload)
    for field in LIST_DEFAULT_FIELDS:
        report[field] = _valid_list(report.get(field))
    for field in STRING_DEFAULT_FIELDS:
        value = report.get(field)
        report[field] = value if isinstance(value, str) else ""

    if not report["immediate_actions"]:
        report["immediate_actions"] = list(_valid_list(report.get("recommended_next_actions")))


    # ADVISER_RESEARCH_QUALITY_V4: recommendations/actions are allowed as
    # evidence-grounded inference even when the model leaves optional fields empty.
    if not report["risk_mitigations"] and report.get("risks"):
        report["risk_mitigations"] = [
            "Verify each unresolved risk against the strongest available primary or official source, assign an owner, and define a mitigation before committing additional capital."
        ]

    if not report["thirty_day_plan"] and report["immediate_actions"]:
        report["thirty_day_plan"] = list(report["immediate_actions"][:3])

    if not report["sixty_day_plan"] and (
        report["immediate_actions"] or report.get("recommended_direction")
    ):
        report["sixty_day_plan"] = [
            "Review the evidence gathered in the first 30 days, compare at least two strategic options, and update the recommendation before increasing commitment."
        ]

    if not report["ninety_day_plan"] and (
        report["immediate_actions"] or report.get("recommended_direction")
    ):
        report["ninety_day_plan"] = [
            "Re-run grounded research with updated market, competitor, funding, and compliance evidence, then decide whether to scale, adjust, or stop based on measured outcomes."
        ]

    if valid_urls is not None:
        for field in ("success_cases", "failure_cases"):
            sanitized = []
            for item in report[field]:
                if not isinstance(item, dict):
                    continue
                copy = dict(item)
                copy["sources"] = [
                    url for url in _valid_list(copy.get("sources"))
                    if isinstance(url, str) and url in valid_urls
                ]
                sanitized.append(copy)
            report[field] = sanitized

        opportunities = []
        for item in report["application_opportunities"]:
            if not isinstance(item, dict):
                continue
            copy = dict(item)
            source = copy.get("source")
            if not isinstance(source, str) or source not in valid_urls:
                copy["source"] = ""
            opportunities.append(copy)
        report["application_opportunities"] = opportunities

    return report


def build_decision_snapshot(report_data: dict[str, Any]) -> dict[str, Any]:
    """Create a persistence-ready decision snapshot using only report content."""
    report = normalize_adviser_report(report_data)
    return {
        "recommended_direction": report["recommended_direction"].strip(),
        "rationale": report["recommendation_reason"].strip(),
        "alternatives": report["strategic_options"],
        "decision_matrix": report["decision_comparison"],
        "conditions_to_reconsider": report["conditions_that_change_decision"],
        "immediate_actions": report["immediate_actions"],
        "action_plan": {
            "30_day": report["thirty_day_plan"],
            "60_day": report["sixty_day_plan"],
            "90_day": report["ninety_day_plan"],
        },
        "confidence_score": float(report.get("confidence_score") or 0.5),
    }
