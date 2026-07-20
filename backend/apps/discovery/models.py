from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.documents.models import DocumentExtraction
from apps.sources.models import Source, SourceDocument


class DiscoveredURL(TimeStampedModel):
    class PageType(models.TextChoices):
        LANDING = "landing", "Landing page"
        LISTING = "listing", "Listing page"
        CATEGORY = "category", "Category page"
        SCHEME_DETAIL = "scheme_detail", "Scheme detail"
        LOAN_DETAIL = "loan_detail", "Loan detail"
        REGISTRATION_DETAIL = "registration_detail", "Registration detail"
        CERTIFICATE_DETAIL = "certificate_detail", "Certificate detail"
        BENEFIT_DETAIL = "benefit_detail", "Benefit detail"
        INCUBATOR_DETAIL = "incubator_detail", "Incubator detail"
        APPLICATION_PAGE = "application_page", "Application page"
        GUIDELINE_PDF = "guideline_pdf", "Guideline PDF"
        POLICY_PDF = "policy_pdf", "Policy PDF"
        FAQ = "faq", "FAQ"
        SITEMAP = "sitemap", "Sitemap"
        API_ENDPOINT = "api_endpoint", "API endpoint"
        LOGIN = "login", "Login or account page"
        ERROR = "error", "Error page"
        ASSET = "asset", "Non-content asset"
        UNKNOWN = "unknown", "Unknown"

    class DiscoveryMethod(models.TextChoices):
        SEED = "seed", "Seed URL"
        HTML_LINK = "html_link", "HTML link"
        PDF_LINK = "pdf_link", "PDF link"
        EMBEDDED_JSON = "embedded_json", "Embedded JSON"
        SITEMAP = "sitemap", "Sitemap"
        MANUAL = "manual", "Manual"

    class Status(models.TextChoices):
        DISCOVERED = "discovered", "Discovered"
        QUEUED = "queued", "Queued"
        COLLECTED = "collected", "Collected"
        REJECTED = "rejected", "Rejected"
        FAILED = "failed", "Failed"

    source = models.ForeignKey(
        Source,
        on_delete=models.CASCADE,
        related_name="discovered_urls",
    )
    parent_document = models.ForeignKey(
        SourceDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discovered_urls",
    )
    last_collected_document = models.ForeignKey(
        SourceDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discovery_origins",
    )
    original_url = models.URLField(max_length=2000)
    normalized_url = models.URLField(max_length=2000)
    anchor_text = models.CharField(max_length=1000, blank=True)
    page_type = models.CharField(
        max_length=40,
        choices=PageType.choices,
        default=PageType.UNKNOWN,
    )
    discovery_method = models.CharField(
        max_length=30,
        choices=DiscoveryMethod.choices,
        default=DiscoveryMethod.HTML_LINK,
    )
    crawl_depth = models.PositiveSmallIntegerField(default=0)
    priority = models.PositiveSmallIntegerField(default=50)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DISCOVERED,
    )
    allowed = models.BooleanField(default=True)
    rejection_reason = models.TextField(blank=True)
    provisional_quality_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    signals = models.JSONField(default=dict, blank=True)
    first_seen_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["priority", "crawl_depth", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "normalized_url"],
                name="unique_discovered_source_url",
            )
        ]
        indexes = [
            models.Index(fields=["status", "priority", "crawl_depth"]),
            models.Index(fields=["source", "page_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.source.name}: {self.normalized_url}"


class CrawlFrontierEntry(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    discovered_url = models.OneToOneField(
        DiscoveredURL,
        on_delete=models.CASCADE,
        related_name="frontier_entry",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    scheduled_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    max_retries = models.PositiveSmallIntegerField(default=3)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    task_id = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = [
            "discovered_url__priority",
            "scheduled_at",
            "created_at",
        ]
        indexes = [
            models.Index(fields=["status", "scheduled_at"]),
            models.Index(fields=["next_retry_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.discovered_url} - {self.status}"


class DocumentQualityAssessment(TimeStampedModel):
    extraction = models.OneToOneField(
        DocumentExtraction,
        on_delete=models.CASCADE,
        related_name="quality_assessment",
    )
    page_type = models.CharField(
        max_length=40,
        choices=DiscoveredURL.PageType.choices,
        default=DiscoveredURL.PageType.UNKNOWN,
    )
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    positive_signals = models.JSONField(default=list, blank=True)
    negative_signals = models.JSONField(default=list, blank=True)
    usable_for_discovery = models.BooleanField(default=False)
    usable_for_rag = models.BooleanField(default=False)
    usable_for_structured_extraction = models.BooleanField(default=False)
    rejection_reason = models.TextField(blank=True)
    assessor_version = models.CharField(max_length=50, default="v1")
    assessed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-score", "-assessed_at"]
        indexes = [
            models.Index(fields=["page_type", "-score"]),
            models.Index(fields=["usable_for_structured_extraction", "-score"]),
        ]

    def __str__(self) -> str:
        return f"{self.extraction} - {self.score}"
