"""
Founder Intelligence Dashboard — aggregate metrics endpoint.

GET /api/v1/startups/<profile_id>/intelligence/

Returns a deterministic snapshot of all key operating metrics for a startup
from all platform workspaces. No LLM calls are made; all values are read
from persisted records.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.recommendations.models import (
    EligibilityAssessment,
    Recommendation,
    RecommendationGenerationRun,
)
from apps.startups.models import (
    StartupBuilderSection,
    StartupCapitalPlan,
    StartupMilestone,
    StartupProfile,
    StartupReadinessAssessment,
)

from .startup_intelligence_serializers import FounderIntelligenceSerializer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SCORE_GRADE: list[tuple[int, str]] = [
    (90, "A"),
    (70, "B"),
    (55, "C"),
    (40, "D"),
    (0, "F"),
]


def _readiness_grade(score: int) -> str:
    for threshold, grade in _SCORE_GRADE:
        if score >= threshold:
            return grade
    return "F"


def _build_readiness_snapshot(profile: StartupProfile) -> dict[str, Any]:
    assessment = (
        StartupReadinessAssessment.objects.filter(startup_profile=profile)
        .order_by("-created_at")
        .first()
    )
    if assessment is None:
        return {
            "score": None,
            "grade": None,
            "domain_count": 0,
            "critical_gap_count": 0,
            "has_assessment": False,
        }

    findings = assessment.findings if isinstance(assessment.findings, list) else []
    blocking = (
        assessment.blocking_findings
        if isinstance(assessment.blocking_findings, list)
        else []
    )

    domain_keys: set[str] = set()
    for finding in findings:
        if isinstance(finding, dict) and finding.get("domain"):
            domain_keys.add(str(finding["domain"]))

    return {
        "score": assessment.score,
        "grade": _readiness_grade(assessment.score),
        "domain_count": len(domain_keys) or 5,
        "critical_gap_count": len(blocking),
        "has_assessment": True,
    }


def _build_capital_snapshot(profile: StartupProfile) -> dict[str, Any]:
    plan = (
        StartupCapitalPlan.objects.filter(startup_profile=profile)
        .order_by("-created_at")
        .first()
    )
    if plan is None:
        return {
            "runway_months": None,
            "runway_status": None,
            "net_burn": None,
            "has_plan": False,
        }
    return {
        "runway_months": float(plan.runway_months),
        "runway_status": plan.runway_status,
        "net_burn": float(plan.net_burn),
        "has_plan": True,
    }


def _build_milestones_snapshot(profile: StartupProfile) -> dict[str, Any]:
    milestones = StartupMilestone.objects.filter(startup_profile=profile)
    total = milestones.count()
    if total == 0:
        return {
            "total": 0,
            "completed": 0,
            "in_progress": 0,
            "blocked": 0,
            "completion_pct": 0,
        }
    completed = milestones.filter(status=StartupMilestone.Status.COMPLETED).count()
    in_progress = milestones.filter(status=StartupMilestone.Status.IN_PROGRESS).count()
    blocked = milestones.filter(status=StartupMilestone.Status.BLOCKED).count()
    return {
        "total": total,
        "completed": completed,
        "in_progress": in_progress,
        "blocked": blocked,
        "completion_pct": round((completed / total) * 100) if total else 0,
    }


def _build_builder_snapshot(profile: StartupProfile) -> dict[str, Any]:
    sections_total = len(StartupBuilderSection.SectionType.values)
    confirmed = StartupBuilderSection.objects.filter(
        startup_profile=profile,
        status=StartupBuilderSection.Status.CONFIRMED,
    ).count()
    drafted = StartupBuilderSection.objects.filter(
        startup_profile=profile,
        status__in=[
            StartupBuilderSection.Status.AI_DRAFTED,
            StartupBuilderSection.Status.CONFIRMED,
        ],
    ).count()
    return {
        "sections_confirmed": confirmed,
        "sections_drafted": drafted,
        "sections_total": sections_total,
        "completion_pct": round((confirmed / sections_total) * 100),
    }


def _build_schemes_snapshot(
    profile: StartupProfile,
) -> dict[str, Any]:
    """
    Summarize the current persisted recommendation set.

    Ranked recommendations are counted as matches. A recommendation that
    still requires manual eligibility verification is presented as a
    potential match rather than as confirmed eligible.
    """

    latest_run = (
        RecommendationGenerationRun.objects.filter(
            startup_profile=profile,
            is_current=True,
        )
        .order_by(
            "-completed_at",
            "-created_at",
            "-id",
        )
        .first()
    )

    if latest_run is None:
        return {
            "matched": 0,
            "eligible": 0,
            "conditionally_eligible": 0,
            "pending_review": 0,
            "has_recommendations": False,
        }

    recommendations = Recommendation.objects.filter(
        generation_run=latest_run,
    ).select_related(
        "assessment",
    )

    matched = recommendations.count()

    eligible = recommendations.filter(
        assessment__result="eligible",
    ).count()

    conditional = recommendations.filter(
        assessment__result__in=[
            "conditionally_eligible",
            "likely_eligible",
        ],
    ).count()

    pending = recommendations.filter(
        assessment__result__in=[
            "verification_required",
            "insufficient_information",
        ],
    ).count()

    return {
        "matched": matched,
        "eligible": eligible,
        "conditionally_eligible": conditional,
        "pending_review": pending,
        "has_recommendations": matched > 0,
    }

def _format_dt(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _build_recent_activity(profile: StartupProfile) -> list[dict[str, Any]]:
    events: list[tuple[datetime, dict[str, Any]]] = []

    # Completed milestones
    for m in (
        StartupMilestone.objects.filter(
            startup_profile=profile,
            status=StartupMilestone.Status.COMPLETED,
        )
        .exclude(completed_at=None)
        .order_by("-completed_at")[:5]
    ):
        events.append(
            (
                m.completed_at,
                {
                    "type": "milestone_completed",
                    "label": f"Completed milestone: {m.title}",
                    "workspace": "milestones",
                    "occurred_at": _format_dt(m.completed_at),
                },
            )
        )

    # Capital plans
    for p in (
        StartupCapitalPlan.objects.filter(startup_profile=profile).order_by("-created_at")[:3]
    ):
        events.append(
            (
                p.created_at,
                {
                    "type": "capital_plan_saved",
                    "label": (
                        f"Capital plan saved — {float(p.runway_months):.1f} months runway"
                    ),
                    "workspace": "capital-planner",
                    "occurred_at": _format_dt(p.created_at),
                },
            )
        )

    # Builder section confirmations
    for s in (
        StartupBuilderSection.objects.filter(
            startup_profile=profile,
            status=StartupBuilderSection.Status.CONFIRMED,
        )
        .exclude(confirmed_at=None)
        .order_by("-confirmed_at")[:5]
    ):
        events.append(
            (
                s.confirmed_at,
                {
                    "type": "builder_section_confirmed",
                    "label": (
                        f"Builder section confirmed: "
                        f"{s.get_section_type_display()}"
                    ),
                    "workspace": "builder",
                    "occurred_at": _format_dt(s.confirmed_at),
                },
            )
        )

    # Readiness assessments
    for a in (
        StartupReadinessAssessment.objects.filter(startup_profile=profile).order_by(
            "-created_at"
        )[:2]
    ):
        events.append(
            (
                a.created_at,
                {
                    "type": "readiness_assessed",
                    "label": f"Readiness assessed — score {a.score}/100",
                    "workspace": "startup",
                    "occurred_at": _format_dt(a.created_at),
                },
            )
        )

    # Sort newest-first, cap at 10
    events.sort(key=lambda e: e[0], reverse=True)
    return [event for _, event in events[:10]]


def _determine_weakest_workspace(
    readiness: dict[str, Any],
    capital: dict[str, Any],
    milestones: dict[str, Any],
    builder: dict[str, Any],
    schemes: dict[str, Any],
) -> str:
    """
    Return the workspace slug with the most critical gap.
    Priority: no assessment > critical runway > no capital plan > low builder > no schemes.
    """
    if not readiness["has_assessment"]:
        return "startup"

    if capital["has_plan"] and capital["runway_status"] == StartupCapitalPlan.RunwayStatus.CRITICAL:
        return "capital-planner"

    if not capital["has_plan"]:
        return "capital-planner"

    if builder["completion_pct"] < 50:
        return "builder"

    if milestones["total"] == 0:
        return "milestones"

    if not schemes["has_recommendations"]:
        return "schemes"

    return "roadmap"


# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------


class StartupIntelligenceView(APIView):
    """
    Returns a cross-workspace aggregate intelligence snapshot for a startup.
    All values are computed from persisted platform records — no LLM calls.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, profile_id: str) -> Response:
        profile = (
            StartupProfile.objects.filter(pk=profile_id, owner=request.user)
            .select_related("owner")
            .first()
        )
        if profile is None:
            return Response(
                {"detail": "Startup profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        readiness = _build_readiness_snapshot(profile)
        capital = _build_capital_snapshot(profile)
        milestones = _build_milestones_snapshot(profile)
        builder = _build_builder_snapshot(profile)
        schemes = _build_schemes_snapshot(profile)
        recent_activity = _build_recent_activity(profile)
        weakest_workspace = _determine_weakest_workspace(
            readiness, capital, milestones, builder, schemes
        )

        payload = {
            "profile_id": str(profile.pk),
            "startup_name": profile.startup_name,
            "generated_at": timezone.now().isoformat(),
            "readiness": readiness,
            "capital": capital,
            "milestones": milestones,
            "builder": builder,
            "schemes": schemes,
            "recent_activity": recent_activity,
            "weakest_workspace": weakest_workspace,
        }

        serializer = FounderIntelligenceSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)
