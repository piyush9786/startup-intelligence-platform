from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.db import transaction

from apps.recommendations.models import RecommendationGenerationRun

from ..models import (
    StartupProfile,
    StartupReadinessActionPlan,
    StartupReadinessAssessment,
    StartupStartingPlan,
)

STARTING_PLAN_VERSION = StartupStartingPlan.PLAN_VERSION


class StartingPlanSourceError(ValueError):
    """Raised when persisted source records cannot form one starting plan."""


@dataclass(frozen=True)
class StartingPlanResult:
    plan: StartupStartingPlan
    created: bool


def _readiness_snapshot(
    assessment: StartupReadinessAssessment,
) -> dict[str, Any]:
    return {
        "id": str(assessment.pk),
        "assessment_date": assessment.assessment_date.isoformat(),
        "status": assessment.status,
        "score": assessment.score,
        "critical_score": assessment.critical_score,
        "recommended_score": assessment.recommended_score,
        "findings": list(assessment.findings),
        "blocking_findings": list(assessment.blocking_findings),
        "summary": assessment.summary,
        "engine_version": assessment.engine_version,
        "created_at": assessment.created_at.isoformat(),
    }


def _action_plan_snapshot(
    action_plan: StartupReadinessActionPlan,
) -> dict[str, Any]:
    return {
        "id": str(action_plan.pk),
        "source_assessment_id": str(action_plan.source_assessment_id),
        "readiness_status": action_plan.readiness_status,
        "has_actions": action_plan.has_actions,
        "blocker_count": action_plan.blocker_count,
        "recommendation_count": action_plan.recommendation_count,
        "total_action_count": action_plan.total_action_count,
        "next_action": action_plan.next_action,
        "items": list(action_plan.items),
        "source_engine_version": action_plan.source_engine_version,
        "planner_version": action_plan.planner_version,
        "created_at": action_plan.created_at.isoformat(),
    }


def _generation_snapshot(
    generation_run: RecommendationGenerationRun,
) -> dict[str, Any]:
    return {
        "generation_id": str(generation_run.pk),
        "assessment_date": generation_run.assessment_date.isoformat(),
        "ranking_version": generation_run.ranking_version,
        "assessed_scheme_count": generation_run.assessed_scheme_count,
        "recommendation_count": generation_run.recommendation_count,
        "excluded_scheme_count": len(generation_run.excluded_schemes),
        "excluded_schemes": list(generation_run.excluded_schemes),
        "completed_at": generation_run.completed_at.isoformat(),
    }


def _readiness_items(
    action_plan: StartupReadinessActionPlan,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    for source_position, source_item in enumerate(action_plan.items, start=1):
        if not isinstance(source_item, dict):
            raise StartingPlanSourceError("The readiness action plan contains an invalid item.")

        code = str(source_item.get("code") or f"action-{source_position}")
        action = str(source_item.get("action") or "Complete the readiness action.")
        priority = str(source_item.get("priority") or "recommended")

        items.append(
            {
                "position": len(items) + 1,
                "item_type": "readiness_action",
                "priority": priority,
                "title": action,
                "description": str(
                    source_item.get("reason")
                    or "This action comes from the deterministic readiness assessment."
                ),
                "status": "not_started",
                "dependency_status": "not_evaluated",
                "destination": {
                    "view": "roadmap",
                },
                "source": {
                    "kind": "readiness_action_plan",
                    "action_plan_id": str(action_plan.pk),
                    "assessment_id": str(action_plan.source_assessment_id),
                    "code": code,
                    "field_path": str(source_item.get("field_path") or ""),
                    "source_position": int(source_item.get("position") or source_position),
                    "readiness_engine_version": action_plan.source_engine_version,
                    "action_planner_version": action_plan.planner_version,
                },
            }
        )

    return items


def _recommendation_items(
    generation_run: RecommendationGenerationRun,
    *,
    starting_position: int,
) -> list[dict[str, Any]]:
    recommendations = generation_run.recommendation_snapshot

    if not isinstance(recommendations, list):
        raise StartingPlanSourceError("The recommendation run contains an invalid snapshot.")

    ordered = sorted(
        recommendations,
        key=lambda item: (
            int(item.get("rank") or 0)
            if isinstance(item, dict)
            else 0
        ),
    )
    items: list[dict[str, Any]] = []

    for source_item in ordered:
        if not isinstance(source_item, dict):
            raise StartingPlanSourceError("The recommendation run contains an invalid item.")

        evidence = source_item.get("evidence_snapshot")
        if not isinstance(evidence, dict):
            evidence = {}

        rank = int(source_item.get("rank") or len(items) + 1)
        scheme_name = str(evidence.get("scheme_name") or "Verified startup scheme")
        scheme_id = str(source_item.get("scheme_id") or evidence.get("scheme_id") or "")
        scheme_version_id = str(
            source_item.get("scheme_version_id")
            or evidence.get("scheme_version_id")
            or ""
        )

        items.append(
            {
                "position": starting_position + len(items),
                "item_type": "scheme_opportunity",
                "priority": "opportunity",
                "title": f"Review {scheme_name}",
                "description": (
                    f"This verified scheme is eligible and ranked #{rank} "
                    "by the deterministic recommendation engine."
                ),
                "status": "not_started",
                "dependency_status": "not_evaluated",
                "destination": {
                    "view": "schemes",
                    "scheme_id": scheme_id,
                },
                "source": {
                    "kind": "recommendation_generation",
                    "generation_id": str(generation_run.pk),
                    "recommendation_id": str(source_item.get("recommendation_id") or ""),
                    "assessment_id": str(source_item.get("assessment_id") or ""),
                    "scheme_id": scheme_id,
                    "scheme_version_id": scheme_version_id,
                    "rank": rank,
                    "score": str(source_item.get("score") or ""),
                    "ranking_version": generation_run.ranking_version,
                    "eligibility_engine_version": str(
                        evidence.get("eligibility_engine_version") or ""
                    ),
                },
            }
        )

    return items


def _validate_sources(
    *,
    source_assessment: StartupReadinessAssessment,
    source_action_plan: StartupReadinessActionPlan,
    recommendation_generation_run: RecommendationGenerationRun,
) -> None:
    profile_ids = {
        source_assessment.startup_profile_id,
        source_action_plan.startup_profile_id,
        recommendation_generation_run.startup_profile_id,
    }

    if len(profile_ids) != 1:
        raise StartingPlanSourceError(
            "The readiness, action-plan, and recommendation sources must share a startup profile."
        )

    if source_action_plan.source_assessment_id != source_assessment.pk:
        raise StartingPlanSourceError(
            "The readiness action plan must derive from the selected readiness assessment."
        )


@transaction.atomic
def create_startup_starting_plan(
    *,
    source_assessment: StartupReadinessAssessment,
    source_action_plan: StartupReadinessActionPlan,
    recommendation_generation_run: RecommendationGenerationRun,
    requested_by: Any,
) -> StartingPlanResult:
    _validate_sources(
        source_assessment=source_assessment,
        source_action_plan=source_action_plan,
        recommendation_generation_run=recommendation_generation_run,
    )

    profile = StartupProfile.objects.select_for_update().get(
        pk=source_assessment.startup_profile_id,
    )
    existing = (
        StartupStartingPlan.objects.select_for_update()
        .filter(
            source_action_plan=source_action_plan,
            recommendation_generation_run=recommendation_generation_run,
        )
        .first()
    )

    StartupStartingPlan.objects.filter(
        startup_profile=profile,
        is_current=True,
    ).exclude(
        pk=getattr(existing, "pk", None),
    ).update(
        is_current=False,
    )

    if existing is not None:
        if not existing.is_current:
            existing.is_current = True
            existing.save(
                update_fields=[
                    "is_current",
                    "updated_at",
                ]
            )
        return StartingPlanResult(
            plan=existing,
            created=False,
        )

    readiness_items = _readiness_items(source_action_plan)
    recommendation_items = _recommendation_items(
        recommendation_generation_run,
        starting_position=len(readiness_items) + 1,
    )
    items = [
        *readiness_items,
        *recommendation_items,
    ]

    plan = StartupStartingPlan.objects.create(
        requested_by=requested_by,
        startup_profile=profile,
        source_assessment=source_assessment,
        source_action_plan=source_action_plan,
        recommendation_generation_run=recommendation_generation_run,
        profile_snapshot=dict(source_assessment.profile_snapshot),
        readiness_snapshot=_readiness_snapshot(source_assessment),
        action_plan_snapshot=_action_plan_snapshot(source_action_plan),
        recommendation_generation_snapshot=_generation_snapshot(
            recommendation_generation_run
        ),
        recommendations_snapshot=list(
            recommendation_generation_run.recommendation_snapshot
        ),
        readiness_item_count=len(readiness_items),
        recommendation_item_count=len(recommendation_items),
        total_item_count=len(items),
        next_item=(dict(items[0]) if items else None),
        items=items,
        plan_version=STARTING_PLAN_VERSION,
        is_current=True,
    )

    return StartingPlanResult(
        plan=plan,
        created=True,
    )
