from django.contrib import admin, messages

from .models import DocumentChunk, DocumentExtraction
from .tasks import process_source_document_task


class DocumentChunkInline(admin.TabularInline):
    model = DocumentChunk
    extra = 0
    fields = (
        "chunk_index",
        "heading",
        "page_number",
        "token_estimate",
        "text_hash",
    )
    readonly_fields = fields
    can_delete = False
    show_change_link = True


@admin.register(DocumentExtraction)
class DocumentExtractionAdmin(admin.ModelAdmin):
    list_display = (
        "source_document",
        "extractor_version",
        "status",
        "word_count",
        "chunk_count",
        "page_count",
        "finished_at",
    )
    list_filter = (
        "status",
        "extractor_version",
        "source_document__source",
    )
    search_fields = (
        "detected_title",
        "source_document__title",
        "source_document__source_url",
        "text_hash",
    )
    readonly_fields = (
        "source_document",
        "extractor_version",
        "status",
        "detected_title",
        "language",
        "text_storage_key",
        "text_preview",
        "text_hash",
        "page_count",
        "section_count",
        "chunk_count",
        "word_count",
        "character_count",
        "started_at",
        "finished_at",
        "metadata",
        "error_message",
        "created_at",
        "updated_at",
    )
    inlines = (DocumentChunkInline,)
    actions = ("queue_reprocessing",)

    @admin.action(description="Queue reprocessing for selected extractions")
    def queue_reprocessing(self, request, queryset):
        count = 0
        for extraction in queryset.select_related("source_document"):
            process_source_document_task.delay(
                str(extraction.source_document_id),
                force=True,
            )
            count += 1
        self.message_user(
            request,
            f"Queued {count} document reprocessing job(s).",
            level=messages.SUCCESS,
        )


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = (
        "extraction",
        "chunk_index",
        "heading",
        "page_number",
        "token_estimate",
    )
    list_filter = (
        "extraction__extractor_version",
        "extraction__source_document__source",
        "page_number",
    )
    search_fields = ("heading", "text", "text_hash")
    readonly_fields = (
        "extraction",
        "chunk_index",
        "heading",
        "page_number",
        "text",
        "text_hash",
        "character_start",
        "character_end",
        "token_estimate",
        "metadata",
        "created_at",
        "updated_at",
    )
