from django.contrib import admin

from .models import EligibilityAssessment, Recommendation


@admin.register(EligibilityAssessment)
class EligibilityAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "startup_profile",
        "scheme_version",
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
        "generation_id",
        "ranking_version",
        "rank",
        "score",
        "created_at",
    )
    list_filter = ("ranking_version",)
    ordering = ("startup_profile", "rank")
