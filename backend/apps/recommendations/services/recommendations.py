from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.db import transaction
from django.db.models import Prefetch

from apps.recommendations.models import (
    EligibilityAssessment,
    Recommendation,
)
from apps.recommendations.services.assessment import (
    create_eligibility_assessment,
)
from apps.schemes.models import EligibilityRule, Scheme, SchemeVersion
from apps.startups.models import StartupProfile

RANKING_VERSION = "recommendations-v1"
_SCORE_QUANTUM = Decimal("0.000001")
_ELIGIBILITY_COMPONENT = Decimal("0.700000")
_RULE_MATCH_COMPONENT_MAX = Decimal("0.200000")
_APPLICATION_STATUS_COMPONENTS = {
    SchemeVersion.ApplicationStatus.OPEN: Decimal("0.100000"),
    SchemeVersion.ApplicationStatus.ROLLING: Decimal("0.090000"),
    SchemeVersion.ApplicationStatus.UNKNOWN: Decimal("0.050000"),
}
_ACTIONABLE_APPLICATION_STATUSES = frozenset(_APPLICATION_STATUS_COMPONENTS)


@dataclass(frozen=True)
class ScoredCandidate:
    assessment: EligibilityAssessment
    scheme_version: SchemeVersion
    score: Decimal
    score_breakdown: dict[str, Any]
    evidence_snapshot: dict[str, Any]


@dataclass(frozen=True)
class RecommendationGeneration:
    generation_id: uuid.UUID
    startup_profile: StartupProfile
    assessment_date: date
    assessments: tuple[EligibilityAssessment, ...]
    recommendations: tuple[Recommendation, ...]
    excluded_schemes: tuple[dict[str, Any], ...]
    ranking_version: str = RANKING_VERSION


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(
        _SCORE_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def _score_assessment(
    *,
    assessment: EligibilityAssessment,
    scheme_version: SchemeVersion,
) -> tuple[Decimal, dict[str, Any]]:
    matched_count = len(assessment.matched_rules)
    failed_count = len(assessment.failed_rules)
    unknown_count = len(assessment.unknown_rules)
    total_count = matched_count + failed_count + unknown_count

    if total_count <= 0:
        raise ValueError("A recommendation cannot be scored without evaluated rules.")

    match_ratio = Decimal(matched_count) / Decimal(total_count)
    rule_match_component = _quantize(match_ratio * _RULE_MATCH_COMPONENT_MAX)
    application_component = _APPLICATION_STATUS_COMPONENTS[scheme_version.application_status]
    score = _quantize(_ELIGIBILITY_COMPONENT + rule_match_component + application_component)

    return score, {
        "ranking_version": RANKING_VERSION,
        "formula": ("eligibility_component + rule_match_component + application_status_component"),
        "eligibility_component": format(
            _ELIGIBILITY_COMPONENT,
            "f",
        ),
        "rule_match_component": format(
            rule_match_component,
            "f",
        ),
        "application_status_component": format(
            application_component,
            "f",
        ),
        "matched_rule_count": matched_count,
        "failed_rule_count": failed_count,
        "unknown_rule_count": unknown_count,
        "total_rule_count": total_count,
        "application_status": scheme_version.application_status,
        "score": format(score, "f"),
    }


def _evidence_snapshot(
    *,
    assessment: EligibilityAssessment,
    scheme_version: SchemeVersion,
) -> dict[str, Any]:
    return {
        "assessment_id": str(assessment.id),
        "assessment_date": assessment.assessment_date.isoformat(),
        "eligibility_result": assessment.result,
        "eligibility_engine_version": assessment.engine_version,
        "scheme_id": str(scheme_version.scheme_id),
        "scheme_version_id": str(scheme_version.id),
        "scheme_version_number": scheme_version.version_number,
        "scheme_name": scheme_version.scheme.canonical_name,
        "scheme_content_hash": scheme_version.content_hash,
        "source_document_id": str(
            scheme_version.source_document_id,
        ),
        "application_status": scheme_version.application_status,
        "official_url": scheme_version.official_url,
        "application_url": scheme_version.application_url,
        "matched_rule_ids": [item["rule_id"] for item in assessment.matched_rules],
        "failed_rule_ids": [item["rule_id"] for item in assessment.failed_rules],
        "unknown_rule_ids": [item["rule_id"] for item in assessment.unknown_rules],
    }


def _exclusion_reason(
    *,
    assessment: EligibilityAssessment,
    scheme_version: SchemeVersion,
) -> str | None:
    if assessment.result != EligibilityAssessment.Result.ELIGIBLE:
        return f"eligibility_result:{assessment.result}"

    total_rules = (
        len(assessment.matched_rules) + len(assessment.failed_rules) + len(assessment.unknown_rules)
    )
    if total_rules == 0:
        return "no_evaluated_rules"

    if scheme_version.application_status not in _ACTIONABLE_APPLICATION_STATUSES:
        return f"application_status:{scheme_version.application_status}"

    return None


def _candidate_sort_key(
    candidate: ScoredCandidate,
) -> tuple[Decimal, str, str]:
    return (
        -candidate.score,
        candidate.scheme_version.scheme.canonical_name.casefold(),
        str(candidate.scheme_version.id),
    )


@transaction.atomic
def generate_recommendations(
    *,
    startup_profile: StartupProfile,
    requested_by: Any,
    assessment_date: date,
) -> RecommendationGeneration:
    locked_profile = StartupProfile.objects.select_for_update().get(
        pk=startup_profile.pk,
    )

    verified_rules = EligibilityRule.objects.order_by(
        "rule_group",
        "field_path",
        "operator",
        "id",
    )
    schemes = (
        Scheme.objects.filter(
            lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
            current_version__isnull=False,
            current_version__verification_status=(SchemeVersion.VerificationStatus.VERIFIED),
        )
        .select_related(
            "current_version",
            "current_version__scheme",
            "current_version__source_document",
        )
        .prefetch_related(
            Prefetch(
                "current_version__eligibility_rules",
                queryset=verified_rules,
            )
        )
        .order_by("canonical_name", "id")
    )

    assessments: list[EligibilityAssessment] = []
    candidates: list[ScoredCandidate] = []
    excluded_schemes: list[dict[str, Any]] = []

    for scheme in schemes:
        scheme_version = scheme.current_version
        assessment = create_eligibility_assessment(
            startup_profile=locked_profile,
            scheme_version=scheme_version,
            requested_by=requested_by,
            assessment_date=assessment_date,
        )
        assessments.append(assessment)

        exclusion_reason = _exclusion_reason(
            assessment=assessment,
            scheme_version=scheme_version,
        )
        if exclusion_reason is not None:
            excluded_schemes.append(
                {
                    "scheme_id": str(scheme.id),
                    "scheme_version_id": str(
                        scheme_version.id,
                    ),
                    "scheme_name": scheme.canonical_name,
                    "assessment_id": str(assessment.id),
                    "result": assessment.result,
                    "application_status": (scheme_version.application_status),
                    "reason": exclusion_reason,
                }
            )
            continue

        score, score_breakdown = _score_assessment(
            assessment=assessment,
            scheme_version=scheme_version,
        )
        candidates.append(
            ScoredCandidate(
                assessment=assessment,
                scheme_version=scheme_version,
                score=score,
                score_breakdown=score_breakdown,
                evidence_snapshot=_evidence_snapshot(
                    assessment=assessment,
                    scheme_version=scheme_version,
                ),
            )
        )

    candidates.sort(key=_candidate_sort_key)
    generation_id = uuid.uuid4()

    Recommendation.objects.filter(
        startup_profile=locked_profile,
    ).delete()

    recommendations: list[Recommendation] = []
    for rank, candidate in enumerate(candidates, start=1):
        recommendations.append(
            Recommendation.objects.create(
                startup_profile=locked_profile,
                scheme_version=candidate.scheme_version,
                assessment=candidate.assessment,
                generation_id=generation_id,
                ranking_version=RANKING_VERSION,
                rank=rank,
                score=candidate.score,
                score_breakdown=candidate.score_breakdown,
                evidence_snapshot=candidate.evidence_snapshot,
            )
        )

    return RecommendationGeneration(
        generation_id=generation_id,
        startup_profile=locked_profile,
        assessment_date=assessment_date,
        assessments=tuple(assessments),
        recommendations=tuple(recommendations),
        excluded_schemes=tuple(excluded_schemes),
    )
