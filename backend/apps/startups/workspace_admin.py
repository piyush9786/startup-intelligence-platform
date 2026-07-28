from django.contrib import admin

from .workspace_models import (
    ApplicationStageEvent,
    ApplicationTask,
    ComplianceRecord,
    ConsultantProfile,
    FounderVaultDocument,
)


@admin.register(ComplianceRecord)
class ComplianceRecordAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "startup_profile",
        "compliance_type",
        "status",
        "expires_on",
        "owner",
    )
    list_filter = ("compliance_type", "status", "expires_on")
    search_fields = (
        "title",
        "registration_number",
        "startup_profile__startup_name",
        "owner__email",
    )


@admin.register(ConsultantProfile)
class ConsultantProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "headline",
        "verification_status",
        "availability",
        "is_public",
        "years_experience",
    )
    list_filter = (
        "verification_status",
        "availability",
        "is_public",
    )
    search_fields = (
        "headline",
        "bio",
        "user__username",
        "user__email",
    )
    list_editable = (
        "verification_status",
        "availability",
        "is_public",
    )


@admin.register(FounderVaultDocument)
class FounderVaultDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "startup_profile",
        "category",
        "size_bytes",
        "is_archived",
        "owner",
        "created_at",
    )
    list_filter = ("category", "is_archived", "expires_on")
    search_fields = (
        "title",
        "original_filename",
        "startup_profile__startup_name",
        "owner__email",
    )
    readonly_fields = (
        "owner",
        "startup_profile",
        "original_filename",
        "mime_type",
        "size_bytes",
        "content_hash",
        "storage_key",
        "bucket_name",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False


@admin.register(ApplicationTask)
class ApplicationTaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "application",
        "status",
        "due_on",
        "completed_at",
        "sort_order",
    )
    list_filter = ("status", "due_on")
    search_fields = (
        "title",
        "notes",
        "application__startup_profile__startup_name",
    )


@admin.register(ApplicationStageEvent)
class ApplicationStageEventAdmin(admin.ModelAdmin):
    list_display = (
        "application",
        "from_stage",
        "to_stage",
        "created_by",
        "occurred_at",
    )
    list_filter = ("from_stage", "to_stage", "occurred_at")
    search_fields = (
        "note",
        "application__startup_profile__startup_name",
        "created_by__email",
    )
    readonly_fields = (
        "application",
        "from_stage",
        "to_stage",
        "note",
        "created_by",
        "occurred_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
