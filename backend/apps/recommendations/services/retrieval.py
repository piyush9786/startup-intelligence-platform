from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from apps.recommendations.models import (
    Recommendation,
    RecommendationGenerationRun,
)
from apps.startups.models import StartupProfile


class RecommendationSetIntegrityError(RuntimeError):
    pass


@dataclass(frozen=True)
class CurrentRecommendationSet:
    startup_profile: StartupProfile
    generation_run: RecommendationGenerationRun | None
    recommendations: tuple[Recommendation, ...]

    @property
    def has_generation(self) -> bool:
        return self.generation_run is not None

    @property
    def generation_id(self) -> UUID | None:
        if self.generation_run is None:
            return None
        return self.generation_run.id

    @property
    def ranking_version(self) -> str | None:
        if self.generation_run is None:
            return None
        return self.generation_run.ranking_version

    @property
    def assessment_date(self) -> date | None:
        if self.generation_run is None:
            return None
        return self.generation_run.assessment_date

    @property
    def generated_at(self) -> datetime | None:
        if self.generation_run is None:
            return None
        return self.generation_run.completed_at

    @property
    def assessed_scheme_count(self) -> int:
        if self.generation_run is None:
            return 0
        return self.generation_run.assessed_scheme_count

    @property
    def excluded_schemes(self) -> list:
        if self.generation_run is None:
            return []
        return self.generation_run.excluded_schemes


def _validate_current_set(
    *,
    generation_run: RecommendationGenerationRun,
    recommendations: tuple[Recommendation, ...],
) -> None:
    ranks = [item.rank for item in recommendations]

    if len(recommendations) != (generation_run.recommendation_count):
        raise RecommendationSetIntegrityError(
            "Current recommendation count does not match its run."
        )
    if ranks != list(range(1, len(ranks) + 1)):
        raise RecommendationSetIntegrityError("Current recommendation ranks are not contiguous.")
    if recommendations:
        generation_ids = {item.generation_id for item in recommendations}
        ranking_versions = {item.ranking_version for item in recommendations}
        assessment_dates = {item.assessment.assessment_date for item in recommendations}
        run_ids = {item.generation_run_id for item in recommendations}

        if generation_ids != {generation_run.id}:
            raise RecommendationSetIntegrityError(
                "Current recommendations do not match the run ID."
            )
        if ranking_versions != {generation_run.ranking_version}:
            raise RecommendationSetIntegrityError(
                "Current recommendations do not match the run ranking version."
            )
        if assessment_dates != {generation_run.assessment_date}:
            raise RecommendationSetIntegrityError(
                "Current recommendations do not match the run assessment date."
            )
        if run_ids != {generation_run.id}:
            raise RecommendationSetIntegrityError(
                "Current recommendations are linked to another run."
            )


def get_current_recommendation_set(
    *,
    startup_profile: StartupProfile,
) -> CurrentRecommendationSet:
    generation_run = (
        RecommendationGenerationRun.objects.filter(
            startup_profile=startup_profile,
            is_current=True,
        )
        .order_by("-completed_at", "-created_at")
        .first()
    )

    if generation_run is None:
        return CurrentRecommendationSet(
            startup_profile=startup_profile,
            generation_run=None,
            recommendations=(),
        )

    recommendations = tuple(
        Recommendation.objects.filter(
            generation_run=generation_run,
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

    _validate_current_set(
        generation_run=generation_run,
        recommendations=recommendations,
    )

    return CurrentRecommendationSet(
        startup_profile=startup_profile,
        generation_run=generation_run,
        recommendations=recommendations,
    )
