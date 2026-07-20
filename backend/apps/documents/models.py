from django.db import models

from apps.core.models import TimeStampedModel
from apps.sources.models import SourceDocument


class DocumentExtraction(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    source_document = models.ForeignKey(
        SourceDocument,
        on_delete=models.CASCADE,
        related_name="extractions",
    )
    extractor_version = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    detected_title = models.CharField(max_length=500, blank=True)
    language = models.CharField(max_length=20, blank=True)
    text_storage_key = models.CharField(max_length=1000, blank=True)
    text_preview = models.TextField(blank=True)
    text_hash = models.CharField(max_length=128, blank=True, db_index=True)
    page_count = models.PositiveIntegerField(default=0)
    section_count = models.PositiveIntegerField(default=0)
    chunk_count = models.PositiveIntegerField(default=0)
    word_count = models.PositiveIntegerField(default=0)
    character_count = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_document", "extractor_version"],
                name="unique_document_extractor_version",
            )
        ]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["source_document", "extractor_version"]),
        ]

    def __str__(self) -> str:
        return f"{self.source_document} - {self.extractor_version} - {self.status}"


class DocumentChunk(TimeStampedModel):
    extraction = models.ForeignKey(
        DocumentExtraction,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    chunk_index = models.PositiveIntegerField()
    heading = models.CharField(max_length=500, blank=True)
    page_number = models.PositiveIntegerField(null=True, blank=True)
    text = models.TextField()
    text_hash = models.CharField(max_length=128, db_index=True)
    character_start = models.PositiveIntegerField(default=0)
    character_end = models.PositiveIntegerField(default=0)
    token_estimate = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["extraction", "chunk_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["extraction", "chunk_index"],
                name="unique_extraction_chunk_index",
            )
        ]
        indexes = [
            models.Index(fields=["extraction", "chunk_index"]),
            models.Index(fields=["page_number"]),
        ]

    def __str__(self) -> str:
        return f"{self.extraction_id} - chunk {self.chunk_index}"
