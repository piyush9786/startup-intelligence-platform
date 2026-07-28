from django.contrib import admin

from .models import (
    EligibilityAssessment,
    Recommendation,
    RecommendationGenerationRun,
)


@admin.register(RecommendationGenerationRun)
class RecommendationGenerationRunAdmin(admin.ModelAdmin):
    list_display = (
        "startup_profile",
        "id",
        "ranking_version",
        "assessment_date",
        "assessed_scheme_count",
        "recommendation_count",
        "is_current",
        "completed_at",
    )
    list_filter = ("ranking_version", "is_current")
    ordering = ("startup_profile", "-completed_at")


@admin.register(EligibilityAssessment)
class EligibilityAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "startup_profile",
        "scheme_version",
        "generation_run",
        "result",
        "engine_version",
        "created_at",
    )
    list_filter = ("result", "engine_version")


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = (
        "startup_profile",
        "scheme_version",
        "generation_run",
        "generation_id",
        "ranking_version",
        "rank",
        "score",
        "created_at",
    )
    list_filter = ("ranking_version",)
    ordering = ("startup_profile", "rank")
