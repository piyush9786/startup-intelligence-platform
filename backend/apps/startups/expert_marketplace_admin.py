from django.contrib import admin

from .expert_marketplace_models import ConsultationRequest


@admin.register(ConsultationRequest)
class ConsultationRequestAdmin(admin.ModelAdmin):
    list_display = (
        "topic",
        "startup_profile",
        "consultant",
        "founder",
        "status",
        "preferred_date",
        "scheduled_for",
        "created_at",
    )
    list_filter = (
        "status",
        "preferred_date",
        "scheduled_for",
        "created_at",
    )
    search_fields = (
        "topic",
        "message",
        "consultant_response",
        "startup_profile__startup_name",
        "founder__email",
        "consultant__user__email",
    )
    readonly_fields = (
        "founder",
        "startup_profile",
        "consultant",
        "topic",
        "message",
        "preferred_date",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False
