from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from apps.recommendations.models import Recommendation
from apps.startups.models import StartupProfile


class RecommendationSetIntegrityError(RuntimeError):
    pass


@dataclass(frozen=True)
class CurrentRecommendationSet:
    startup_profile: StartupProfile
    recommendations: tuple[Recommendation, ...]
    generation_id: UUID | None
    ranking_version: str | None
    assessment_date: date | None
    generated_at: datetime | None

    @property
    def has_generation(self) -> bool:
        return bool(self.recommendations)


def _validate_current_set(
    recommendations: tuple[Recommendation, ...],
) -> None:
    generation_ids = {item.generation_id for item in recommendations}
    ranking_versions = {item.ranking_version for item in recommendations}
    assessment_dates = {item.assessment.assessment_date for item in recommendations}
    ranks = [item.rank for item in recommendations]

    if len(generation_ids) != 1:
        raise RecommendationSetIntegrityError(
            "Current recommendations contain multiple generation IDs."
        )
    if len(ranking_versions) != 1:
        raise RecommendationSetIntegrityError(
            "Current recommendations contain multiple ranking versions."
        )
    if len(assessment_dates) != 1:
        raise RecommendationSetIntegrityError(
            "Current recommendations contain multiple assessment dates."
        )
    if ranks != list(range(1, len(ranks) + 1)):
        raise RecommendationSetIntegrityError("Current recommendation ranks are not contiguous.")


def get_current_recommendation_set(
    *,
    startup_profile: StartupProfile,
) -> CurrentRecommendationSet:
    recommendations = tuple(
        Recommendation.objects.filter(
            startup_profile=startup_profile,
        )
        .select_related(
            "assessment",
            "scheme_version__scheme",
        )
        .order_by(
            "rank",
            "scheme_version__scheme__canonical_name",
            "id",
        )
    )

    if not recommendations:
        return CurrentRecommendationSet(
            startup_profile=startup_profile,
            recommendations=(),
            generation_id=None,
            ranking_version=None,
            assessment_date=None,
            generated_at=None,
        )

    _validate_current_set(recommendations)

    first = recommendations[0]
    return CurrentRecommendationSet(
        startup_profile=startup_profile,
        recommendations=recommendations,
        generation_id=first.generation_id,
        ranking_version=first.ranking_version,
        assessment_date=first.assessment.assessment_date,
        generated_at=min(item.created_at for item in recommendations),
    )
