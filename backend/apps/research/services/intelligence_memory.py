"""Persist and retrieve reusable research intelligence."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.utils import timezone

from apps.research.models import (
    DecisionRecommendation,
    ResearchInsight,
    StartupResearchReport,
)
from apps.research.services.decision_engine import build_decision_snapshot

# ADVISER_DECISION_INTELLIGENCE_V1


def _freshness(last_verified_at) -> str:
    age = timezone.now() - last_verified_at
    if age <= timedelta(days=30):
        return ResearchInsight.FreshnessStatus.CURRENT
    if age <= timedelta(days=90):
        return ResearchInsight.FreshnessStatus.AGING
    if age <= timedelta(days=180):
        return ResearchInsight.FreshnessStatus.STALE
    return ResearchInsight.FreshnessStatus.REVERIFY


def _urls(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _confidence(report_data: dict[str, Any]) -> float:
    try:
        return min(1.0, max(0.0, float(report_data.get("confidence_score", 0.5))))
    except (TypeError, ValueError):
        return 0.5


def get_prior_intelligence(profile, *, limit: int = 24) -> list[dict[str, Any]]:
    """Return recent structured memory; freshness is recalculated at read time."""
    queryset = (
        ResearchInsight.objects.filter(startup_profile=profile)
        .select_related("source_report")
        .order_by("-last_verified_at", "-created_at")[:limit]
    )
    return [
        {
            "type": item.insight_type,
            "title": item.title,
            "summary": item.summary,
            "details": item.details,
            "evidence_urls": item.evidence_urls,
            "confidence_score": item.confidence_score,
            "freshness_status": _freshness(item.last_verified_at),
            "last_verified_at": item.last_verified_at.isoformat(),
            "source_report_id": str(item.source_report_id),
        }
        for item in queryset
    ]


def _string_insight(
    *, report: StartupResearchReport, insight_type: str, title_prefix: str,
    value: str, details: dict[str, Any] | None = None,
) -> ResearchInsight:
    report_data = report.report or {}
    verified_at = report.live_search_date or report.local_data_cutoff or report.created_at
    return ResearchInsight(
        startup_profile=report.startup_profile,
        source_report=report,
        insight_type=insight_type,
        title=f"{title_prefix}: {value}"[:255],
        summary=value,
        details=details or {},
        evidence_urls=_urls(report_data.get("sources")),
        confidence_score=_confidence(report_data),
        freshness_status=_freshness(verified_at),
        last_verified_at=verified_at,
    )


def persist_report_intelligence(report: StartupResearchReport) -> None:
    """Materialize useful report sections into reusable structured memory."""
    data = report.report or {}
    objects: list[ResearchInsight] = []

    list_specs = (
        ("benefits", ResearchInsight.InsightType.BENEFIT, "Benefit"),
        ("current_competitors", ResearchInsight.InsightType.COMPETITOR, "Competitor"),
        ("major_challenges", ResearchInsight.InsightType.CHALLENGE, "Challenge"),
        ("risks", ResearchInsight.InsightType.RISK, "Risk"),
        ("market_gaps", ResearchInsight.InsightType.MARKET_GAP, "Market gap"),
        ("government_schemes", ResearchInsight.InsightType.OPPORTUNITY, "Scheme"),
        ("funding_opportunities", ResearchInsight.InsightType.OPPORTUNITY, "Funding"),
        ("loan_options", ResearchInsight.InsightType.OPPORTUNITY, "Loan"),
    )
    for field, insight_type, prefix in list_specs:
        for value in data.get(field) or []:
            if isinstance(value, str) and value.strip():
                objects.append(_string_insight(
                    report=report, insight_type=insight_type,
                    title_prefix=prefix, value=value.strip(),
                ))

    for case in data.get("success_cases") or []:
        if not isinstance(case, dict):
            continue
        company = str(case.get("company") or "Success case").strip()
        summary = str(case.get("why_it_worked") or "").strip()
        if summary:
            objects.append(_string_insight(
                report=report,
                insight_type=ResearchInsight.InsightType.SUCCESS_CASE,
                title_prefix="Success case", value=f"{company} — {summary}", details=case,
            ))
        lesson = str(case.get("lesson") or "").strip()
        if lesson:
            objects.append(_string_insight(
                report=report,
                insight_type=ResearchInsight.InsightType.LESSON,
                title_prefix=f"Lesson from {company}", value=lesson,
                details={"case_type": "success", **case},
            ))

    for case in data.get("failure_cases") or []:
        if not isinstance(case, dict):
            continue
        company = str(case.get("company") or "Failure case").strip()
        summary = str(case.get("what_happened") or "").strip()
        if summary:
            objects.append(_string_insight(
                report=report,
                insight_type=ResearchInsight.InsightType.FAILURE_CASE,
                title_prefix="Failure case", value=f"{company} — {summary}", details=case,
            ))
        lesson = str(case.get("lesson") or "").strip()
        if lesson:
            objects.append(_string_insight(
                report=report,
                insight_type=ResearchInsight.InsightType.LESSON,
                title_prefix=f"Lesson from {company}", value=lesson,
                details={"case_type": "failure", **case},
            ))

    for opportunity in data.get("application_opportunities") or []:
        if not isinstance(opportunity, dict):
            continue
        name = str(opportunity.get("name") or "Opportunity").strip()
        why = str(opportunity.get("why_relevant") or "").strip()
        if why:
            objects.append(_string_insight(
                report=report,
                insight_type=ResearchInsight.InsightType.OPPORTUNITY,
                title_prefix=str(opportunity.get("category") or "Opportunity").title(),
                value=f"{name} — {why}", details=opportunity,
            ))

    if objects:
        ResearchInsight.objects.bulk_create(objects, ignore_conflicts=True)

    decision = build_decision_snapshot(data)
    if decision["recommended_direction"]:
        DecisionRecommendation.objects.get_or_create(
            source_report=report,
            defaults={
                "startup_profile": report.startup_profile,
                "question": report.research_request.question,
                "recommended_direction": decision["recommended_direction"],
                "rationale": decision["rationale"],
                "alternatives": decision["alternatives"],
                "decision_matrix": decision["decision_matrix"],
                "conditions_to_reconsider": decision["conditions_to_reconsider"],
                "immediate_actions": decision["immediate_actions"],
                "action_plan": decision["action_plan"],
                "confidence_score": min(1.0, max(0.0, decision["confidence_score"])),
            },
        )
