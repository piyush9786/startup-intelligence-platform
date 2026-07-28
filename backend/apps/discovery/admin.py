from django.contrib import admin, messages

from .models import CrawlFrontierEntry, DiscoveredURL, DocumentQualityAssessment
from .tasks import process_frontier_entry_task


@admin.register(DiscoveredURL)
class DiscoveredURLAdmin(admin.ModelAdmin):
    list_display = (
        "source",
        "page_type",
        "status",
        "priority",
        "crawl_depth",
        "allowed",
        "normalized_url",
    )
    list_filter = (
        "source",
        "page_type",
        "status",
        "allowed",
        "crawl_depth",
    )
    search_fields = ("normalized_url", "anchor_text", "rejection_reason")
    readonly_fields = (
        "source",
        "parent_document",
        "last_collected_document",
        "original_url",
        "normalized_url",
        "anchor_text",
        "page_type",
        "discovery_method",
        "crawl_depth",
        "priority",
        "status",
        "allowed",
        "rejection_reason",
        "provisional_quality_score",
        "signals",
        "first_seen_at",
        "last_seen_at",
        "created_at",
        "updated_at",
    )


@admin.register(CrawlFrontierEntry)
class CrawlFrontierEntryAdmin(admin.ModelAdmin):
    list_display = (
        "discovered_url",
        "status",
        "retry_count",
        "scheduled_at",
        "finished_at",
    )
    list_filter = ("status", "discovered_url__source")
    search_fields = ("discovered_url__normalized_url", "error_message")
    actions = ("queue_selected",)

    @admin.action(description="Queue selected frontier entries")
    def queue_selected(self, request, queryset):
        count = 0
        for entry in queryset:
            task = process_frontier_entry_task.delay(str(entry.id))
            entry.task_id = task.id
            entry.save(update_fields=["task_id", "updated_at"])
            count += 1
        self.message_user(
            request,
            f"Queued {count} frontier entrie(s).",
            level=messages.SUCCESS,
        )


@admin.register(DocumentQualityAssessment)
class DocumentQualityAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "extraction",
        "page_type",
        "score",
        "usable_for_rag",
        "usable_for_structured_extraction",
        "assessed_at",
    )
    list_filter = (
        "page_type",
        "usable_for_discovery",
        "usable_for_rag",
        "usable_for_structured_extraction",
        "assessor_version",
    )
    search_fields = (
        "extraction__detected_title",
        "extraction__source_document__source_url",
        "rejection_reason",
    )
    readonly_fields = (
        "extraction",
        "page_type",
        "score",
        "positive_signals",
        "negative_signals",
        "usable_for_discovery",
        "usable_for_rag",
        "usable_for_structured_extraction",
        "rejection_reason",
        "assessor_version",
        "assessed_at",
        "created_at",
        "updated_at",
    )
