from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.db import transaction

from apps.startups.models import (
    StartupReadinessAssessment,
)

from .readiness import (
    ReadinessEvaluation,
    evaluate_startup_readiness,
)

PROFILE_SNAPSHOT_FIELDS = (
    "startup_name",
    "legal_name",
    "description",
    "incorporation_type",
    "incorporation_date",
    "state",
    "district",
    "stage",
    "sectors",
    "technologies",
    "founder_categories",
    "founder_gender",
    "dpiit_recognized",
    "udyam_registered",
    "annual_turnover",
    "revenue_stage",
    "funding_required",
    "funding_purpose",
    "team_size",
    "profile_data",
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
    if isinstance(
        value,
        (list, tuple, set, frozenset),
    ):
        return [_json_ready(item) for item in value]
    return value


def snapshot_startup_profile(
    startup_profile: Any,
) -> dict[str, Any]:
    return {
        "id": str(startup_profile.pk),
        **{
            field_name: _json_ready(
                getattr(startup_profile, field_name),
            )
            for field_name in PROFILE_SNAPSHOT_FIELDS
        },
    }


@transaction.atomic
def create_startup_readiness_assessment(
    *,
    startup_profile: Any,
    requested_by: Any,
    assessment_date: date,
) -> StartupReadinessAssessment:
    evaluation: ReadinessEvaluation = evaluate_startup_readiness(
        startup_profile=startup_profile,
        as_of_date=assessment_date,
    )

    return StartupReadinessAssessment.objects.create(
        requested_by=requested_by,
        startup_profile=startup_profile,
        assessment_date=assessment_date,
        profile_snapshot=snapshot_startup_profile(
            startup_profile,
        ),
        status=evaluation.status.value,
        score=evaluation.score,
        critical_score=evaluation.critical_score,
        recommended_score=(evaluation.recommended_score),
        findings=[item.to_dict() for item in evaluation.findings],
        blocking_findings=[item.to_dict() for item in evaluation.blocking_findings],
        summary=evaluation.summary,
        engine_version=evaluation.engine_version,
    )
