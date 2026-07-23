from django.contrib import admin

from .models import (
    OnboardingProgress,
    StartupAdvisorBriefing,
    StartupAdvisorBriefingJob,
    StartupAdvisorSnapshot,
    StartupAssessmentDraft,
    StartupProfile,
    StartupReadinessActionPlan,
    StartupReadinessAssessment,
    StartupStartingPlan,
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


@admin.register(OnboardingProgress)
class OnboardingProgressAdmin(admin.ModelAdmin):
    list_display = (
        "owner",
        "tour_version",
        "variant",
        "status",
        "current_step",
        "updated_at",
    )
    list_filter = (
        "tour_version",
        "variant",
        "status",
        "current_step",
    )
    search_fields = (
        "owner__username",
        "owner__email",
    )
    readonly_fields = (
        "owner",
        "tour_version",
        "variant",
        "status",
        "current_step",
        "started_at",
        "dismissed_at",
        "completed_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StartupAssessmentDraft)
class StartupAssessmentDraftAdmin(admin.ModelAdmin):
    list_display = (
        "owner",
        "startup_profile",
        "status",
        "current_step",
        "submitted_at",
        "updated_at",
    )
    list_filter = (
        "status",
        "current_step",
        "submitted_at",
    )
    search_fields = (
        "owner__username",
        "owner__email",
        "startup_profile__startup_name",
        "startup_profile__legal_name",
    )
    readonly_fields = (
        "owner",
        "startup_profile",
        "status",
        "current_step",
        "data",
        "submitted_at",
        "submitted_profile_snapshot",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


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


@admin.register(StartupStartingPlan)
class StartupStartingPlanAdmin(admin.ModelAdmin):
    list_display = (
        "startup_profile",
        "plan_version",
        "total_item_count",
        "is_current",
        "requested_by",
        "created_at",
    )
    list_filter = (
        "plan_version",
        "is_current",
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
        "source_action_plan",
        "recommendation_generation_run",
        "profile_snapshot",
        "readiness_snapshot",
        "action_plan_snapshot",
        "recommendation_generation_snapshot",
        "recommendations_snapshot",
        "readiness_item_count",
        "recommendation_item_count",
        "total_item_count",
        "next_item",
        "items",
        "plan_version",
        "is_current",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StartupAdvisorSnapshot)
class StartupAdvisorSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "startup_profile",
        "has_readiness_assessment",
        "has_action_plan",
        "has_recommendation_generation",
        "recommendation_count",
        "snapshot_version",
        "requested_by",
        "created_at",
    )
    list_filter = (
        "has_readiness_assessment",
        "has_action_plan",
        "has_recommendation_generation",
        "snapshot_version",
    )
    search_fields = (
        "startup_profile__startup_name",
        "startup_profile__legal_name",
        "requested_by__email",
    )
    readonly_fields = (
        "requested_by",
        "startup_profile",
        "readiness_assessment",
        "readiness_action_plan",
        "recommendation_generation_run",
        "has_readiness_assessment",
        "has_action_plan",
        "has_recommendation_generation",
        "profile_snapshot",
        "readiness_snapshot",
        "action_plan_snapshot",
        "recommendation_generation_snapshot",
        "recommendations_snapshot",
        "recommendation_count",
        "snapshot_version",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StartupAdvisorBriefing)
class StartupAdvisorBriefingAdmin(admin.ModelAdmin):
    list_display = (
        "startup_profile",
        "provider",
        "model_name",
        "prompt_version",
        "schema_version",
        "requested_by",
        "completed_at",
    )
    list_filter = (
        "provider",
        "model_name",
        "prompt_version",
        "schema_version",
    )
    search_fields = (
        "startup_profile__startup_name",
        "startup_profile__legal_name",
        "requested_by__email",
    )
    readonly_fields = (
        "requested_by",
        "startup_profile",
        "source_snapshot",
        "provider",
        "model_name",
        "prompt_version",
        "schema_version",
        "generation_parameters",
        "prompt_snapshot",
        "briefing",
        "prompt_token_count",
        "output_token_count",
        "total_duration_ns",
        "response_metadata",
        "completed_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StartupAdvisorBriefingJob)
class StartupAdvisorBriefingJobAdmin(admin.ModelAdmin):
    list_display = (
        "startup_profile",
        "status",
        "source_snapshot",
        "briefing",
        "requested_by",
        "started_at",
        "completed_at",
        "created_at",
    )
    list_filter = (
        "status",
        "error_code",
        "created_at",
    )
    search_fields = (
        "startup_profile__startup_name",
        "startup_profile__legal_name",
        "requested_by__email",
        "celery_task_id",
    )
    readonly_fields = (
        "requested_by",
        "startup_profile",
        "source_snapshot",
        "briefing",
        "status",
        "celery_task_id",
        "error_code",
        "error_message",
        "started_at",
        "completed_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
