from django.db import models

from apps.core.models import TimeStampedModel


class Source(TimeStampedModel):
    class AuthorityTier(models.TextChoices):
        OFFICIAL_PROGRAMME = "A", "A - Official programme portal or notification"
        OFFICIAL_AUTHORITY = "B", "B - Ministry, department or implementing agency"
        GOVERNMENT_AGGREGATOR = "C", "C - Government aggregator"
        DELIVERY_PARTNER = "D", "D - Authorised delivery partner"
        DISCOVERY_ONLY = "E", "E - Discovery only"

    class CrawlFrequency(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        MANUAL = "manual", "Manual"

    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True)
    ministry = models.CharField(max_length=255, blank=True)
    department = models.CharField(max_length=255, blank=True)
    state = models.CharField(max_length=100, blank=True)
    official_domain = models.CharField(max_length=255, unique=True)
    listing_url = models.URLField(max_length=1000)
    application_portal_url = models.URLField(max_length=1000, blank=True)
    authority_tier = models.CharField(max_length=1, choices=AuthorityTier.choices)
    crawl_frequency = models.CharField(
        max_length=20, choices=CrawlFrequency.choices, default=CrawlFrequency.WEEKLY
    )
    language = models.CharField(max_length=20, default="en")
    active = models.BooleanField(default=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class SourceDocument(TimeStampedModel):
    class Status(models.TextChoices):
        COLLECTED = "collected", "Collected"
        EXTRACTED = "extracted", "Extracted"
        REVIEW_REQUIRED = "review_required", "Review required"
        VERIFIED = "verified", "Verified"
        FAILED = "failed", "Failed"

    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="documents")
    source_url = models.URLField(max_length=1500)
    title = models.CharField(max_length=500, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    storage_key = models.CharField(max_length=1000, blank=True)
    content_hash = models.CharField(max_length=128, db_index=True)
    retrieved_at = models.DateTimeField()
    published_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.COLLECTED)
    extractor_version = models.CharField(max_length=50, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_url", "content_hash"], name="unique_source_document_version"
            )
        ]
        ordering = ["-retrieved_at"]

    def __str__(self) -> str:
        return self.title or self.source_url
