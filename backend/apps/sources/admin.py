from django.contrib import admin

from .models import Source, SourceDocument


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "authority_tier", "category", "state", "active", "last_checked_at")
    list_filter = ("authority_tier", "category", "state", "active")
    search_fields = ("name", "official_domain", "ministry", "department")


@admin.register(SourceDocument)
class SourceDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "source", "status", "retrieved_at", "content_hash")
    list_filter = ("status", "mime_type", "source")
    search_fields = ("title", "source_url", "content_hash")
