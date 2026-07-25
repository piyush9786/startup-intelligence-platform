from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from apps.recommendations.models import (
    EligibilityAssessment,
    Recommendation,
    RecommendationGenerationRun,
)
from apps.recommendations.services.assessment import (
    create_eligibility_assessment,
    snapshot_startup_profile,
)
from apps.recommendations.services.explanation import (
    build_eligibility_explanation,
    build_verification_provenance,
)
from apps.schemes.models import EligibilityRule, Scheme, SchemeVersion
from apps.startups.models import StartupProfile

RANKING_VERSION = "recommendations-v2"
_SCORE_QUANTUM = Decimal("0.000001")

# Legacy / Fallback scoring components
_ELIGIBILITY_COMPONENT = Decimal("0.700000")
_RULE_MATCH_COMPONENT_MAX = Decimal("0.200000")
_APPLICATION_STATUS_COMPONENTS = {
    SchemeVersion.ApplicationStatus.OPEN: Decimal("0.100000"),
    SchemeVersion.ApplicationStatus.ROLLING: Decimal("0.090000"),
    SchemeVersion.ApplicationStatus.UNKNOWN: Decimal("0.050000"),
}
_ACTIONABLE_APPLICATION_STATUSES = frozenset(_APPLICATION_STATUS_COMPONENTS)

# Recommendations-v2 ML-blended weights
# Total Score = Eligibility (40%) + Rule Match (10%) + SVM Probability (40%) + Application Status (10%)
_ELIGIBILITY_WEIGHT_V2 = Decimal("0.400000")
_RULE_MATCH_WEIGHT_MAX_V2 = Decimal("0.100000")
_SVM_WEIGHT_V2 = Decimal("0.400000")
_APPLICATION_STATUS_WEIGHT_MAX_V2 = Decimal("0.100000")

_APPLICATION_STATUS_RATIOS_V2 = {
    SchemeVersion.ApplicationStatus.OPEN: Decimal("1.000000"),
    SchemeVersion.ApplicationStatus.ROLLING: Decimal("0.900000"),
    SchemeVersion.ApplicationStatus.UNKNOWN: Decimal("0.500000"),
}


@dataclass(frozen=True)
class ScoredCandidate:
    assessment: EligibilityAssessment
    scheme_version: SchemeVersion
    score: Decimal
    score_breakdown: dict[str, Any]
    evidence_snapshot: dict[str, Any]


@dataclass(frozen=True)
class RecommendationGeneration:
    generation_run: RecommendationGenerationRun
    startup_profile: StartupProfile
    assessment_date: date
    assessments: tuple[EligibilityAssessment, ...]
    recommendations: tuple[Recommendation, ...]
    excluded_schemes: tuple[dict[str, Any], ...]
    ranking_version: str = RANKING_VERSION

    @property
    def generation_id(self):
        return self.generation_run.id


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(
        _SCORE_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def _get_svm_score(startup_profile, scheme_version) -> Decimal | None:
    """Attempt to get SVM success probability; return None on any failure."""
    try:
        from apps.ml_engine.services.models.svm_ranker import (
            predict_scheme_probability,
        )

        prob = predict_scheme_probability(startup_profile, scheme_version)
        return Decimal(str(prob))
    except Exception:
        return None


def _score_assessment(
    *,
    assessment: EligibilityAssessment,
    scheme_version: SchemeVersion,
    startup_profile=None,
) -> tuple[Decimal, dict[str, Any]]:
    matched_count = len(assessment.matched_rules)
    failed_count = len(assessment.failed_rules)
    unknown_count = len(assessment.unknown_rules)
    total_count = matched_count + failed_count + unknown_count

    if total_count <= 0:
        raise ValueError("A recommendation cannot be scored without evaluated rules.")

    match_ratio = Decimal(matched_count) / Decimal(total_count)

    # Try ML-blended scoring (SVM)
    svm_score = _get_svm_score(startup_profile, scheme_version) if startup_profile else None

    if svm_score is not None:
        # Recommendations-v2 ML Blend: 40% eligibility + 10% rule match + 40% SVM + 10% app status
        eligibility_component = _ELIGIBILITY_WEIGHT_V2
        rule_match_component = _quantize(match_ratio * _RULE_MATCH_WEIGHT_MAX_V2)
        svm_component = _quantize(svm_score * _SVM_WEIGHT_V2)
        
        app_ratio = _APPLICATION_STATUS_RATIOS_V2.get(
            scheme_version.application_status, Decimal("0.500000")
        )
        application_status_component = _quantize(app_ratio * _APPLICATION_STATUS_WEIGHT_MAX_V2)

        score = _quantize(
            eligibility_component
            + rule_match_component
            + svm_component
            + application_status_component
        )
        ml_mode = "svm_blended"
    else:
        # Fallback: original heuristic scoring (70% eligibility + up to 20% rules + up to 10% app status)
        eligibility_component = _ELIGIBILITY_COMPONENT
        rule_match_component = _quantize(match_ratio * _RULE_MATCH_COMPONENT_MAX)
        application_status_component = _APPLICATION_STATUS_COMPONENTS.get(
            scheme_version.application_status, Decimal("0.050000")
        )
        svm_component = Decimal("0.000000")
        score = _quantize(eligibility_component + rule_match_component + application_status_component)
        ml_mode = "heuristic_fallback"

    return score, {
        "ranking_version": RANKING_VERSION,
        "ml_scoring_mode": ml_mode,
        "formula": (
            "eligibility_component + rule_match_component + "
            "svm_component + application_status_component"
        ),
        "eligibility_component": format(eligibility_component, "f"),
        "rule_match_component": format(rule_match_component, "f"),
        "svm_component": format(svm_component, "f"),
        "application_status_component": format(application_status_component, "f"),
        "svm_score": format(svm_score, "f") if svm_score is not None else None,
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
        "source_content_hash": (
            scheme_version.source_document.content_hash
        ),
        "verification_provenance": build_verification_provenance(
            assessment,
        ),
    }


def generate_recommendations(
    *,
    startup_profile: StartupProfile,
    requested_by,
    assessment_date: date | None = None,
) -> RecommendationGeneration:
    assessment_date = assessment_date or timezone.now().date()
    eligible_result = EligibilityAssessment.Result.ELIGIBLE

    active_schemes = (
        Scheme.objects.filter(
            lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
            current_version__isnull=False,
            current_version__verification_status=SchemeVersion.VerificationStatus.VERIFIED,
        )
        .select_related(
            "current_version",
            "current_version__scheme",
            "current_version__source_document",
            "current_version__source_document__source",
        )
        .prefetch_related(
            Prefetch(
                "current_version__eligibility_rules",
                queryset=EligibilityRule.objects.all(),
            ),
        )
        .order_by("canonical_name")
    )

    assessments: list[EligibilityAssessment] = []
    candidates: list[ScoredCandidate] = []
    excluded_schemes: list[dict[str, Any]] = []

    with transaction.atomic():
        RecommendationGenerationRun.objects.filter(
            startup_profile=startup_profile,
            is_current=True,
        ).update(is_current=False)

        profile_snapshot = snapshot_startup_profile(startup_profile)
        generation_run = RecommendationGenerationRun.objects.create(
            startup_profile=startup_profile,
            requested_by=requested_by,
            assessment_date=assessment_date,
            ranking_version=RANKING_VERSION,
            profile_snapshot=profile_snapshot,
            is_current=True,
        )

        for scheme in active_schemes:
            scheme_version = scheme.current_version
            assessment = create_eligibility_assessment(
                startup_profile=startup_profile,
                scheme_version=scheme_version,
                requested_by=requested_by,
                assessment_date=assessment_date,
                generation_run=generation_run,
            )
            assessments.append(assessment)

            if assessment.result != eligible_result:
                excluded_schemes.append({
                    "scheme_id": str(scheme.id),
                    "scheme_name": scheme.canonical_name,
                    "reason": f"eligibility_result:{assessment.result}",
                    "result": assessment.result,
                    "failed_rules": [
                        item.get("field_path") for item in assessment.failed_rules
                    ],
                    "eligibility_explanation": build_eligibility_explanation(
                        assessment,
                    ),
                })
                continue

            if (
                scheme_version.application_status
                not in _ACTIONABLE_APPLICATION_STATUSES
            ):
                excluded_schemes.append({
                    "scheme_id": str(scheme.id),
                    "scheme_name": scheme.canonical_name,
                    "reason": f"application_status:{scheme_version.application_status}",
                    "application_status": (
                        scheme_version.application_status
                    ),
                    "eligibility_explanation": build_eligibility_explanation(
                        assessment,
                    ),
                })
                continue

            score, breakdown = _score_assessment(
                assessment=assessment,
                scheme_version=scheme_version,
                startup_profile=startup_profile,
            )
            snapshot = _evidence_snapshot(
                assessment=assessment,
                scheme_version=scheme_version,
            )
            candidates.append(
                ScoredCandidate(
                    assessment=assessment,
                    scheme_version=scheme_version,
                    score=score,
                    score_breakdown=breakdown,
                    evidence_snapshot=snapshot,
                ),
            )

        # Deterministic sorting: score DESC, canonical_name ASC
        candidates.sort(
            key=lambda item: (
                -item.score,
                item.scheme_version.scheme.canonical_name,
            ),
        )

        # Delete previous recommendations for this profile before creating new run output
        Recommendation.objects.filter(
            startup_profile=startup_profile,
        ).delete()

        recommendations: list[Recommendation] = []
        for rank, candidate in enumerate(candidates, start=1):
            explanation = build_eligibility_explanation(
                candidate.assessment,
            )
            provenance = build_verification_provenance(
                candidate.scheme_version,
            )

            rec = Recommendation.objects.create(
                generation_run=generation_run,
                generation_id=generation_run.id,
                startup_profile=startup_profile,
                scheme_version=candidate.scheme_version,
                assessment=candidate.assessment,
                rank=rank,
                score=candidate.score,
                ranking_version=RANKING_VERSION,
                score_breakdown=candidate.score_breakdown,
                evidence_snapshot=candidate.evidence_snapshot,
            )
            recommendations.append(rec)

        rec_snapshots = [
            {
                "scheme_id": str(rec.scheme_version.scheme_id),
                "scheme_version_id": str(rec.scheme_version_id),
                "rank": rec.rank,
                "score": format(rec.score, "f"),
                "score_breakdown": rec.score_breakdown,
                "evidence_snapshot": rec.evidence_snapshot,
                "eligibility_explanation": build_eligibility_explanation(rec.assessment),
                "verification_provenance": build_verification_provenance(rec.assessment),
            }
            for rec in recommendations
        ]
        generation_run.assessed_scheme_count = len(assessments)
        generation_run.recommendation_count = len(recommendations)
        generation_run.excluded_schemes = excluded_schemes
        generation_run.recommendation_snapshot = rec_snapshots
        generation_run.save(
            update_fields=[
                "assessed_scheme_count",
                "recommendation_count",
                "excluded_schemes",
                "recommendation_snapshot",
                "updated_at",
            ]
        )

    return RecommendationGeneration(
        generation_run=generation_run,
        startup_profile=startup_profile,
        assessment_date=assessment_date,
        assessments=tuple(assessments),
        recommendations=tuple(recommendations),
        excluded_schemes=tuple(excluded_schemes),
        ranking_version=RANKING_VERSION,
    )
