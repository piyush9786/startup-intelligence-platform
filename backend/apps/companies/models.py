from __future__ import annotations

import re
import unicodedata

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel


def normalize_company_name(value: str) -> str:
    """Return a stable, conservative company name for exact entity matching."""
    value = unicodedata.normalize("NFKC", value or "").casefold()
    value = value.replace("&", " and ")
    legal_suffix = (
        r"\b(private|pvt|limited|ltd|llp|incorporated|inc|corp|corporation)\b"
    )
    value = re.sub(legal_suffix, " ", value)
    value = "".join(
        character
        if unicodedata.category(character)[0] in {"L", "M", "N"}
        else " "
        for character in value
    )
    return re.sub(r"\s+", " ", value).strip()


class CompanyDataSource(TimeStampedModel):
    class SourceType(models.TextChoices):
        GOVERNMENT = "government", "Government data"
        PUBLIC_DATASET = "public_dataset", "Public dataset"
        COMPANY_DISCLOSURE = "company_disclosure", "Company disclosure"
        RESEARCH_REPORT = "research_report", "Research report"
        NEWS = "news", "News"
        MANUAL = "manual", "Manual research"

    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending review"
        REVIEWED = "reviewed", "Reviewed"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=32, choices=SourceType.choices)
    publisher = models.CharField(max_length=255, blank=True)
    source_url = models.URLField(max_length=1500, blank=True)
    licence = models.CharField(max_length=255, blank=True)
    reliability_score = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Governance score from 0 (untrusted) to 1 (highest confidence).",
    )
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    active = models.BooleanField(default=True)
    last_retrieved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class RawCompanyDataset(TimeStampedModel):
    class ParsingStatus(models.TextChoices):
        REGISTERED = "registered", "Registered"
        PROCESSING = "processing", "Processing"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    dataset_id = models.CharField(max_length=150, unique=True)
    source = models.ForeignKey(
        CompanyDataSource,
        on_delete=models.PROTECT,
        related_name="datasets",
    )
    original_filename = models.CharField(max_length=500)
    original_url = models.URLField(max_length=1500, blank=True)
    storage_path = models.CharField(max_length=1500, blank=True)
    checksum_sha256 = models.CharField(max_length=64, db_index=True)
    content_length = models.PositiveBigIntegerField(default=0)
    retrieved_at = models.DateTimeField()
    schema_version = models.PositiveSmallIntegerField(default=1)
    parsing_status = models.CharField(
        max_length=20,
        choices=ParsingStatus.choices,
        default=ParsingStatus.REGISTERED,
    )
    row_count = models.PositiveIntegerField(default=0)
    accepted_count = models.PositiveIntegerField(default=0)
    rejected_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-retrieved_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "checksum_sha256"],
                name="company_dataset_source_checksum_unique",
            ),
        ]

    def __str__(self) -> str:
        return self.dataset_id


class Company(TimeStampedModel):
    class OperatingStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        PROFITABLE = "profitable", "Profitable"
        ACQUIRED = "acquired", "Acquired"
        MERGED = "merged", "Merged"
        IPO = "ipo", "IPO"
        PIVOTED = "pivoted", "Pivoted"
        CLOSED = "closed", "Closed"
        INACTIVE = "inactive", "Inactive"
        UNKNOWN = "unknown", "Unknown"

    class VerificationStatus(models.TextChoices):
        UNVERIFIED = "unverified", "Unverified"
        PARTIALLY_VERIFIED = "partially_verified", "Partially verified"
        VERIFIED = "verified", "Verified"
        DISPUTED = "disputed", "Disputed"

    canonical_name = models.CharField(max_length=255)
    normalized_name = models.CharField(max_length=255, db_index=True, editable=False)
    industry = models.CharField(max_length=150)
    sub_industry = models.CharField(max_length=150, blank=True)
    business_model = models.CharField(max_length=100)
    customer_segment = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    founded_year = models.PositiveSmallIntegerField(null=True, blank=True)
    website = models.URLField(max_length=1000, blank=True)
    operating_status = models.CharField(
        max_length=20,
        choices=OperatingStatus.choices,
        default=OperatingStatus.UNKNOWN,
    )
    verification_status = models.CharField(
        max_length=24,
        choices=VerificationStatus.choices,
        default=VerificationStatus.UNVERIFIED,
    )

    class Meta:
        ordering = ["canonical_name"]
        indexes = [
            models.Index(
                fields=["industry", "business_model", "country"],
                name="company_peer_lookup_idx",
            ),
            models.Index(
                fields=["operating_status", "verification_status"],
                name="company_status_verify_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        self.normalized_name = normalize_company_name(self.canonical_name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.canonical_name


class CompanyAlias(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="aliases")
    alias = models.CharField(max_length=255)
    normalized_alias = models.CharField(max_length=255, db_index=True, editable=False)
    source = models.ForeignKey(
        CompanyDataSource,
        on_delete=models.PROTECT,
        related_name="company_aliases",
    )

    class Meta:
        ordering = ["alias"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "normalized_alias", "source"],
                name="company_alias_source_unique",
            ),
        ]

    def save(self, *args, **kwargs):
        self.normalized_alias = normalize_company_name(self.alias)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.alias


class CompanySourceRecord(TimeStampedModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="source_records",
    )
    source = models.ForeignKey(
        CompanyDataSource,
        on_delete=models.PROTECT,
        related_name="company_records",
    )
    latest_dataset = models.ForeignKey(
        RawCompanyDataset,
        on_delete=models.PROTECT,
        related_name="company_records",
    )
    external_id = models.CharField(max_length=255)
    source_record_url = models.URLField(max_length=1500, blank=True)
    confidence_score = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    is_primary = models.BooleanField(default=False)
    raw_data = models.JSONField(default=dict)

    class Meta:
        ordering = ["company", "-confidence_score"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"],
                name="company_source_external_id_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.source.slug}:{self.external_id}"


class CompanyMetric(TimeStampedModel):
    class MetricName(models.TextChoices):
        REVENUE = "revenue", "Revenue"
        EMPLOYEE_COUNT = "employee_count", "Employee count"
        CUSTOMER_COUNT = "customer_count", "Customer count"
        MONTHLY_GROWTH = "monthly_growth", "Monthly growth"
        BURN_RATE = "burn_rate", "Burn rate"
        RUNWAY_MONTHS = "runway_months", "Runway (months)"
        FUNDING_TOTAL = "funding_total", "Total funding"
        VALUATION = "valuation", "Valuation"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="metrics")
    dataset = models.ForeignKey(
        RawCompanyDataset,
        on_delete=models.PROTECT,
        related_name="metrics",
    )
    source = models.ForeignKey(
        CompanyDataSource,
        on_delete=models.PROTECT,
        related_name="company_metrics",
    )
    metric_name = models.CharField(max_length=50, choices=MetricName.choices)
    metric_value = models.DecimalField(max_digits=24, decimal_places=6)
    metric_unit = models.CharField(max_length=30)
    observation_date = models.DateField()
    confidence_score = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )

    class Meta:
        ordering = ["company", "-observation_date", "metric_name"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "company",
                    "source",
                    "metric_name",
                    "observation_date",
                    "metric_unit",
                ],
                name="company_metric_observation_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=["metric_name", "-observation_date"],
                name="company_metric_date_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.company}: {self.metric_name} on {self.observation_date}"


class CompanyOutcome(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="outcomes")
    dataset = models.ForeignKey(
        RawCompanyDataset,
        on_delete=models.PROTECT,
        related_name="outcomes",
    )
    source = models.ForeignKey(
        CompanyDataSource,
        on_delete=models.PROTECT,
        related_name="company_outcomes",
    )
    outcome_type = models.CharField(max_length=20, choices=Company.OperatingStatus.choices)
    outcome_date = models.DateField(null=True, blank=True)
    reason = models.TextField(blank=True)
    evidence_url = models.URLField(max_length=1500, blank=True)
    confidence_score = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )

    class Meta:
        ordering = ["company", "-outcome_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "source", "outcome_type", "outcome_date"],
                name="company_outcome_evidence_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.company}: {self.outcome_type}"
