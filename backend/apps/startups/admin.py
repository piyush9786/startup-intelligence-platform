from django.contrib import admin

from .models import (
    StartupProfile,
    StartupReadinessActionPlan,
    StartupReadinessAssessment,
)


@admin.register(StartupProfile)
class StartupProfileAdmin(admin.ModelAdmin):
    list_display = (
        "startup_name",
        "owner",
        "stage",
        "state",
        "dpiit_recognized",
        "udyam_registered",
    )
    list_filter = (
        "stage",
        "state",
        "dpiit_recognized",
        "udyam_registered",
    )
    search_fields = (
        "startup_name",
        "legal_name",
        "description",
    )


@admin.register(StartupReadinessAssessment)
class StartupReadinessAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "startup_profile",
        "status",
        "score",
        "assessment_date",
        "requested_by",
        "created_at",
    )
    list_filter = (
        "status",
        "assessment_date",
        "engine_version",
    )
    search_fields = (
        "startup_profile__startup_name",
        "startup_profile__legal_name",
        "requested_by__email",
    )
    readonly_fields = (
        "requested_by",
        "startup_profile",
        "assessment_date",
        "profile_snapshot",
        "status",
        "score",
        "critical_score",
        "recommended_score",
        "findings",
        "blocking_findings",
        "summary",
        "engine_version",
        "created_at",
        "updated_at",
    )


@admin.register(StartupReadinessActionPlan)
class StartupReadinessActionPlanAdmin(admin.ModelAdmin):
    list_display = (
        "startup_profile",
        "readiness_status",
        "total_action_count",
        "source_assessment",
        "requested_by",
        "created_at",
    )
    list_filter = (
        "readiness_status",
        "has_actions",
        "planner_version",
        "source_engine_version",
    )
    search_fields = (
        "startup_profile__startup_name",
        "startup_profile__legal_name",
        "requested_by__email",
    )
    readonly_fields = (
        "requested_by",
        "startup_profile",
        "source_assessment",
        "source_assessment_snapshot",
        "readiness_status",
        "has_actions",
        "blocker_count",
        "recommendation_count",
        "total_action_count",
        "next_action",
        "items",
        "source_engine_version",
        "planner_version",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
