from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.db import transaction

from apps.startups.models import (
    StartupReadinessActionPlan,
    StartupReadinessAssessment,
)

from .action_plan import build_startup_readiness_action_plan
from .readiness import (
    ReadinessEvaluation,
    ReadinessFinding,
    ReadinessOutcome,
    ReadinessPriority,
    ReadinessStatus,
)


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


def snapshot_readiness_assessment(
    assessment: StartupReadinessAssessment,
) -> dict[str, Any]:
    return {
        "id": str(assessment.id),
        "startup_profile_id": str(assessment.startup_profile_id),
        "requested_by_id": (
            str(assessment.requested_by_id) if assessment.requested_by_id else None
        ),
        "assessment_date": _json_ready(assessment.assessment_date),
        "profile_snapshot": _json_ready(assessment.profile_snapshot),
        "status": assessment.status,
        "score": assessment.score,
        "critical_score": assessment.critical_score,
        "recommended_score": assessment.recommended_score,
        "findings": _json_ready(assessment.findings),
        "blocking_findings": _json_ready(
            assessment.blocking_findings,
        ),
        "summary": assessment.summary,
        "engine_version": assessment.engine_version,
        "created_at": _json_ready(assessment.created_at),
    }


def _finding_from_payload(payload: Any) -> ReadinessFinding:
    if not isinstance(payload, dict):
        raise ValueError("Persisted readiness findings must be objects.")

    required = (
        "code",
        "field_path",
        "priority",
        "outcome",
        "reason",
        "action",
    )
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError("Persisted readiness finding is missing: " + ", ".join(missing))

    return ReadinessFinding(
        code=str(payload["code"]),
        field_path=str(payload["field_path"]),
        priority=ReadinessPriority(payload["priority"]),
        outcome=ReadinessOutcome(payload["outcome"]),
        reason=str(payload["reason"]),
        action=str(payload["action"]),
        actual_value=_json_ready(payload.get("actual_value")),
    )


def evaluation_from_persisted_assessment(
    assessment: StartupReadinessAssessment,
) -> ReadinessEvaluation:
    if not isinstance(assessment.findings, list):
        raise ValueError("Persisted readiness findings must be a list.")

    return ReadinessEvaluation(
        status=ReadinessStatus(assessment.status),
        score=assessment.score,
        critical_score=assessment.critical_score,
        recommended_score=assessment.recommended_score,
        findings=tuple(_finding_from_payload(payload) for payload in assessment.findings),
        summary=assessment.summary,
        engine_version=assessment.engine_version,
    )


@transaction.atomic
def create_startup_readiness_action_plan(
    *,
    source_assessment: StartupReadinessAssessment,
    requested_by: Any,
) -> StartupReadinessActionPlan:
    locked_assessment = (
        StartupReadinessAssessment.objects.select_for_update(of=("self",))
        .select_related(
            "startup_profile",
            "requested_by",
        )
        .get(pk=source_assessment.pk)
    )
    evaluation = evaluation_from_persisted_assessment(
        locked_assessment,
    )
    payload = build_startup_readiness_action_plan(
        evaluation=evaluation,
    ).to_dict()

    return StartupReadinessActionPlan.objects.create(
        requested_by=requested_by,
        startup_profile=locked_assessment.startup_profile,
        source_assessment=locked_assessment,
        source_assessment_snapshot=snapshot_readiness_assessment(
            locked_assessment,
        ),
        readiness_status=payload["readiness_status"],
        has_actions=payload["has_actions"],
        blocker_count=payload["blocker_count"],
        recommendation_count=payload["recommendation_count"],
        total_action_count=payload["total_action_count"],
        next_action=payload["next_action"],
        items=payload["items"],
        source_engine_version=payload["source_engine_version"],
        planner_version=payload["planner_version"],
    )
