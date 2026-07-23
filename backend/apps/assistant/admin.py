from django.contrib import admin

from .models import (
    AgentClaimReference,
    AgentMessage,
    AgentSession,
    AgentToolCallLog,
)


class ReadOnlyAuditAdmin(admin.ModelAdmin):
    def has_add_permission(
        self,
        request,
    ) -> bool:
        return False

    def has_change_permission(
        self,
        request,
        obj=None,
    ) -> bool:
        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ) -> bool:
        return False


@admin.register(AgentSession)
class AgentSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "founder",
        "startup_profile",
        "agent_type",
        "status",
        "turn_count",
        "max_turns",
        "last_activity_at",
    )
    list_filter = (
        "agent_type",
        "status",
    )
    search_fields = (
        "founder__username",
        "founder__email",
        "startup_profile__startup_name",
    )
    readonly_fields = (
        "scope_key",
        "turn_count",
        "last_activity_at",
        "completed_at",
        "created_at",
        "updated_at",
    )


@admin.register(AgentMessage)
class AgentMessageAdmin(ReadOnlyAuditAdmin):
    list_display = (
        "id",
        "session",
        "sequence_number",
        "role",
        "created_at",
    )
    list_filter = ("role",)
    search_fields = (
        "session__founder__username",
        "content",
    )


@admin.register(AgentToolCallLog)
class AgentToolCallLogAdmin(ReadOnlyAuditAdmin):
    list_display = (
        "id",
        "session",
        "sequence_number",
        "tool_name",
        "tool_version",
        "status",
        "duration_ms",
        "called_at",
    )
    list_filter = (
        "status",
        "tool_name",
        "tool_version",
    )
    search_fields = (
        "session__founder__username",
        "tool_name",
        "output_hash",
    )


@admin.register(AgentClaimReference)
class AgentClaimReferenceAdmin(ReadOnlyAuditAdmin):
    list_display = (
        "id",
        "message",
        "claim_key",
        "tool_call",
        "created_at",
    )
    search_fields = (
        "claim_key",
        "claim_text",
        "output_path",
    )
