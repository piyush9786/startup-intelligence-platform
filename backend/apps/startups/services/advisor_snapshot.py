from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.db import transaction

from apps.recommendations.models import (
    Recommendation,
    RecommendationGenerationRun,
)
from apps.recommendations.services import (
    CurrentRecommendationSet,
    get_current_recommendation_set,
)
from apps.startups.models import (
    StartupAdvisorSnapshot,
    StartupProfile,
    StartupReadinessActionPlan,
    StartupReadinessAssessment,
)

from .action_plan_persistence import snapshot_readiness_assessment
from .assessment import snapshot_startup_profile

ADVISOR_SNAPSHOT_VERSION = "startup-advisor-snapshot-v1"


def _json_ready(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {
            str(key): _json_ready(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_ready(item) for item in value]
    return value


def snapshot_readiness_action_plan(
    action_plan: StartupReadinessActionPlan,
) -> dict[str, Any]:
    return {
        "id": str(action_plan.id),
        "startup_profile_id": str(action_plan.startup_profile_id),
        "source_assessment_id": str(
            action_plan.source_assessment_id,
        ),
        "requested_by_id": (
            str(action_plan.requested_by_id) if action_plan.requested_by_id else None
        ),
        "source_assessment_snapshot": _json_ready(
            action_plan.source_assessment_snapshot,
        ),
        "readiness_status": action_plan.readiness_status,
        "has_actions": action_plan.has_actions,
        "blocker_count": action_plan.blocker_count,
        "recommendation_count": action_plan.recommendation_count,
        "total_action_count": action_plan.total_action_count,
        "next_action": action_plan.next_action,
        "items": _json_ready(action_plan.items),
        "source_engine_version": action_plan.source_engine_version,
        "planner_version": action_plan.planner_version,
        "created_at": _json_ready(action_plan.created_at),
    }


def snapshot_recommendation_generation_run(
    generation_run: RecommendationGenerationRun,
) -> dict[str, Any]:
    return {
        "generation_id": str(generation_run.id),
        "startup_profile_id": str(
            generation_run.startup_profile_id,
        ),
        "requested_by_id": (
            str(generation_run.requested_by_id) if generation_run.requested_by_id else None
        ),
        "assessment_date": _json_ready(
            generation_run.assessment_date,
        ),
        "ranking_version": generation_run.ranking_version,
        "profile_snapshot": _json_ready(
            generation_run.profile_snapshot,
        ),
        "assessed_scheme_count": (generation_run.assessed_scheme_count),
        "recommendation_count": (generation_run.recommendation_count),
        "excluded_scheme_count": len(
            generation_run.excluded_schemes,
        ),
        "excluded_schemes": _json_ready(
            generation_run.excluded_schemes,
        ),
        "recommendation_snapshot": _json_ready(
            generation_run.recommendation_snapshot,
        ),
        "is_current": generation_run.is_current,
        "completed_at": _json_ready(
            generation_run.completed_at,
        ),
        "created_at": _json_ready(generation_run.created_at),
    }


def snapshot_recommendation(
    recommendation: Recommendation,
) -> dict[str, Any]:
    return {
        "id": str(recommendation.id),
        "generation_id": str(recommendation.generation_id),
        "ranking_version": recommendation.ranking_version,
        "startup_profile_id": str(
            recommendation.startup_profile_id,
        ),
        "assessment_id": str(recommendation.assessment_id),
        "assessment_result": recommendation.assessment.result,
        "scheme_id": str(
            recommendation.scheme_version.scheme_id,
        ),
        "scheme_version_id": str(
            recommendation.scheme_version_id,
        ),
        "scheme_name": (recommendation.scheme_version.scheme.canonical_name),
        "application_status": (recommendation.scheme_version.application_status),
        "rank": recommendation.rank,
        "score": _json_ready(recommendation.score),
        "score_breakdown": _json_ready(
            recommendation.score_breakdown,
        ),
        "evidence_snapshot": _json_ready(
            recommendation.evidence_snapshot,
        ),
        "created_at": _json_ready(recommendation.created_at),
    }


def _latest_readiness_assessment(
    startup_profile: StartupProfile,
) -> StartupReadinessAssessment | None:
    return (
        StartupReadinessAssessment.objects.filter(
            startup_profile=startup_profile,
        )
        .select_related(
            "startup_profile",
            "requested_by",
        )
        .order_by(
            "-created_at",
            "-id",
        )
        .first()
    )


def _latest_readiness_action_plan(
    startup_profile: StartupProfile,
) -> StartupReadinessActionPlan | None:
    return (
        StartupReadinessActionPlan.objects.filter(
            startup_profile=startup_profile,
        )
        .select_related(
            "startup_profile",
            "source_assessment",
            "requested_by",
        )
        .order_by(
            "-created_at",
            "-id",
        )
        .first()
    )


@transaction.atomic
def create_startup_advisor_snapshot(
    *,
    startup_profile: StartupProfile,
    requested_by: Any,
) -> StartupAdvisorSnapshot:
    locked_profile = (
        StartupProfile.objects.select_for_update(of=("self",))
        .select_related("owner")
        .get(pk=startup_profile.pk)
    )
    readiness_assessment = _latest_readiness_assessment(
        locked_profile,
    )
    readiness_action_plan = _latest_readiness_action_plan(
        locked_profile,
    )
    current_recommendations: CurrentRecommendationSet = get_current_recommendation_set(
        startup_profile=locked_profile,
    )

    generation_run = current_recommendations.generation_run
    recommendations = current_recommendations.recommendations

    return StartupAdvisorSnapshot.objects.create(
        requested_by=requested_by,
        startup_profile=locked_profile,
        readiness_assessment=readiness_assessment,
        readiness_action_plan=readiness_action_plan,
        recommendation_generation_run=generation_run,
        has_readiness_assessment=(readiness_assessment is not None),
        has_action_plan=readiness_action_plan is not None,
        has_recommendation_generation=(generation_run is not None),
        profile_snapshot=snapshot_startup_profile(
            locked_profile,
        ),
        readiness_snapshot=(
            snapshot_readiness_assessment(
                readiness_assessment,
            )
            if readiness_assessment is not None
            else {}
        ),
        action_plan_snapshot=(
            snapshot_readiness_action_plan(
                readiness_action_plan,
            )
            if readiness_action_plan is not None
            else {}
        ),
        recommendation_generation_snapshot=(
            snapshot_recommendation_generation_run(
                generation_run,
            )
            if generation_run is not None
            else {}
        ),
        recommendations_snapshot=[snapshot_recommendation(item) for item in recommendations],
        recommendation_count=len(recommendations),
        snapshot_version=ADVISOR_SNAPSHOT_VERSION,
    )
