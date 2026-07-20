from django.contrib import admin, messages

from .models import CrawlRun, Source, SourceDocument
from .tasks import collect_source_task


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "authority_tier",
        "category",
        "state",
        "active",
        "last_checked_at",
    )
    list_filter = ("authority_tier", "category", "state", "active")
    search_fields = ("name", "official_domain", "ministry", "department")
    actions = ("queue_collection",)

    @admin.action(description="Queue collection for selected sources")
    def queue_collection(self, request, queryset):
        count = 0
        for source in queryset.filter(active=True):
            collect_source_task.delay(str(source.id))
            count += 1
        self.message_user(
            request,
            f"Queued {count} source collection job(s).",
            level=messages.SUCCESS,
        )


@admin.register(SourceDocument)
class SourceDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "source",
        "version_number",
        "is_current",
        "status",
        "mime_type",
        "content_length",
        "retrieved_at",
    )
    list_filter = ("status", "mime_type", "source", "is_current")
    search_fields = ("title", "source_url", "final_url", "content_hash")
    readonly_fields = (
        "content_hash",
        "storage_key",
        "response_headers",
        "metadata",
        "retrieved_at",
    )


@admin.register(CrawlRun)
class CrawlRunAdmin(admin.ModelAdmin):
    list_display = (
        "source",
        "status",
        "trigger",
        "documents_created",
        "documents_unchanged",
        "error_count",
        "started_at",
        "finished_at",
    )
    list_filter = ("status", "trigger", "source")
    search_fields = ("source__name", "requested_url", "error_message")
    readonly_fields = (
        "source",
        "trigger",
        "requested_url",
        "status",
        "started_at",
        "finished_at",
        "documents_created",
        "documents_unchanged",
        "error_count",
        "error_message",
        "metadata",
        "created_at",
        "updated_at",
    )
