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
    allowed_domains = models.JSONField(default=list, blank=True)
    listing_url = models.URLField(max_length=1000)
    application_portal_url = models.URLField(max_length=1000, blank=True)
    authority_tier = models.CharField(
        max_length=1,
        choices=AuthorityTier.choices,
    )
    crawl_frequency = models.CharField(
        max_length=20,
        choices=CrawlFrequency.choices,
        default=CrawlFrequency.WEEKLY,
    )
    language = models.CharField(max_length=20, default="en")
    active = models.BooleanField(default=True)
    respect_robots_txt = models.BooleanField(default=True)
    request_timeout_seconds = models.PositiveSmallIntegerField(default=30)
    max_document_bytes = models.PositiveIntegerField(default=25 * 1024 * 1024)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class CrawlRun(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        PARTIAL = "partial", "Partially succeeded"
        FAILED = "failed", "Failed"

    class Trigger(models.TextChoices):
        MANUAL = "manual", "Manual"
        SCHEDULED = "scheduled", "Scheduled"
        API = "api", "API"

    source = models.ForeignKey(
        Source,
        on_delete=models.PROTECT,
        related_name="crawl_runs",
    )
    trigger = models.CharField(
        max_length=20,
        choices=Trigger.choices,
        default=Trigger.MANUAL,
    )
    requested_url = models.URLField(max_length=1500)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    documents_created = models.PositiveIntegerField(default=0)
    documents_unchanged = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.source.name} - {self.status} - {self.created_at:%Y-%m-%d %H:%M}"


class SourceDocument(TimeStampedModel):
    class Status(models.TextChoices):
        COLLECTED = "collected", "Collected"
        EXTRACTED = "extracted", "Extracted"
        REVIEW_REQUIRED = "review_required", "Review required"
        VERIFIED = "verified", "Verified"
        FAILED = "failed", "Failed"

    source = models.ForeignKey(
        Source,
        on_delete=models.PROTECT,
        related_name="documents",
    )
    crawl_run = models.ForeignKey(
        CrawlRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    supersedes = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="superseded_by",
    )
    source_url = models.URLField(max_length=1500)
    final_url = models.URLField(max_length=1500, blank=True)
    title = models.CharField(max_length=500, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    storage_key = models.CharField(max_length=1000, blank=True)
    content_hash = models.CharField(max_length=128, db_index=True)
    version_number = models.PositiveIntegerField(default=1)
    is_current = models.BooleanField(default=True)
    retrieved_at = models.DateTimeField()
    published_at = models.DateTimeField(null=True, blank=True)
    http_status = models.PositiveSmallIntegerField(null=True, blank=True)
    etag = models.CharField(max_length=500, blank=True)
    last_modified = models.CharField(max_length=500, blank=True)
    content_length = models.PositiveBigIntegerField(default=0)
    response_headers = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.COLLECTED,
    )
    extractor_version = models.CharField(max_length=50, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_url", "version_number"],
                name="unique_source_url_version_number",
            ),
        ]
        indexes = [
            models.Index(fields=["source_url", "is_current"]),
            models.Index(fields=["source", "-retrieved_at"]),
        ]
        ordering = ["-retrieved_at"]

    def __str__(self) -> str:
        return self.title or self.source_url
