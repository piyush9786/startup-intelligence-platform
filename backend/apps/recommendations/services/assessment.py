from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.db import transaction

from apps.recommendations.models import (
    EligibilityAssessment,
    RecommendationGenerationRun,
)
from apps.recommendations.services.eligibility import (
    EligibilityEvaluation,
    evaluate_scheme_eligibility,
)
from apps.recommendations.services.verification import (
    approved_verification_values,
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
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_ready(item) for item in value]
    return value


def snapshot_startup_profile(startup_profile: Any) -> dict[str, Any]:
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
def create_eligibility_assessment(
    *,
    startup_profile: Any,
    scheme_version: Any,
    requested_by: Any,
    assessment_date: date,
    generation_run: RecommendationGenerationRun | None = None,
) -> EligibilityAssessment:
    approved_verifications = approved_verification_values(
        startup_profile=startup_profile,
        scheme_version=scheme_version,
        as_of_date=assessment_date,
    )
    evaluation: EligibilityEvaluation = evaluate_scheme_eligibility(
        startup_profile=startup_profile,
        scheme_version=scheme_version,
        as_of_date=assessment_date,
        approved_verifications=approved_verifications,
    )

    return EligibilityAssessment.objects.create(
        requested_by=requested_by,
        startup_profile=startup_profile,
        scheme_version=scheme_version,
        generation_run=generation_run,
        assessment_date=assessment_date,
        profile_snapshot=snapshot_startup_profile(
            startup_profile,
        ),
        result=evaluation.result,
        matched_rules=[item.to_dict() for item in evaluation.matched_rules],
        failed_rules=[item.to_dict() for item in evaluation.failed_rules],
        unknown_rules=[item.to_dict() for item in evaluation.unknown_rules],
        explanation=evaluation.explanation,
        engine_version=evaluation.engine_version,
    )
