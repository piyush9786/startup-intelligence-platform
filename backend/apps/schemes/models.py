from django.db import models

from apps.core.models import TimeStampedModel
from apps.sources.models import SourceDocument


class Authority(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    authority_type = models.CharField(max_length=100, blank=True)
    ministry = models.CharField(max_length=255, blank=True)
    department = models.CharField(max_length=255, blank=True)
    state = models.CharField(max_length=100, blank=True)
    official_url = models.URLField(max_length=1000, blank=True)

    def __str__(self) -> str:
        return self.name


class Scheme(TimeStampedModel):
    class LifecycleStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        SUPERSEDED = "superseded", "Superseded"
        ARCHIVED = "archived", "Archived"

    canonical_name = models.CharField(max_length=500)
    short_name = models.CharField(max_length=150, blank=True)
    alternative_names = models.JSONField(default=list, blank=True)
    authority = models.ForeignKey(Authority, on_delete=models.PROTECT, related_name="schemes")
    lifecycle_status = models.CharField(
        max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.DRAFT
    )
    current_version = models.ForeignKey(
        "SchemeVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_for_schemes",
    )

    class Meta:
        ordering = ["canonical_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["canonical_name", "authority"], name="unique_scheme_authority"
            )
        ]

    def __str__(self) -> str:
        return self.canonical_name


class SchemeVersion(TimeStampedModel):
    class VerificationStatus(models.TextChoices):
        EXTRACTED = "extracted", "Extracted"
        REVIEW_REQUIRED = "review_required", "Review required"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    class ApplicationStatus(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"
        ROLLING = "rolling", "Rolling"
        UPCOMING = "upcoming", "Upcoming"
        UNKNOWN = "unknown", "Unknown"

    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    source_document = models.ForeignKey(
        SourceDocument, on_delete=models.PROTECT, related_name="scheme_versions"
    )
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    captured_at = models.DateTimeField()
    content_hash = models.CharField(max_length=128, db_index=True)
    description = models.TextField(blank=True)
    objective = models.TextField(blank=True)
    support_types = models.JSONField(default=list, blank=True)
    categories = models.JSONField(default=list, blank=True)
    eligible_sectors = models.JSONField(default=list, blank=True)
    eligible_stages = models.JSONField(default=list, blank=True)
    eligible_states = models.JSONField(default=list, blank=True)
    founder_categories = models.JSONField(default=list, blank=True)
    minimum_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    maximum_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="INR")
    equity_required = models.BooleanField(null=True, blank=True)
    interest_rate_min = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True)
    interest_rate_max = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True)
    application_status = models.CharField(
        max_length=20, choices=ApplicationStatus.choices, default=ApplicationStatus.UNKNOWN
    )
    opening_date = models.DateField(null=True, blank=True)
    deadline = models.DateField(null=True, blank=True)
    official_url = models.URLField(max_length=1500)
    application_url = models.URLField(max_length=1500, blank=True)
    required_documents = models.JSONField(default=list, blank=True)
    application_steps = models.JSONField(default=list, blank=True)
    benefits = models.JSONField(default=list, blank=True)
    restrictions = models.JSONField(default=list, blank=True)
    verification_status = models.CharField(
        max_length=32, choices=VerificationStatus.choices, default=VerificationStatus.EXTRACTED
    )
    extraction_confidence = models.DecimalField(
        max_digits=5, decimal_places=4, null=True, blank=True
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_scheme_versions",
    )

    class Meta:
        ordering = ["scheme", "-version_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["scheme", "version_number"], name="unique_scheme_version_number"
            ),
            models.UniqueConstraint(
                fields=["scheme", "content_hash"], name="unique_scheme_content_hash"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.scheme} v{self.version_number}"


class EligibilityRule(TimeStampedModel):
    class Operator(models.TextChoices):
        EQUALS = "equals", "Equals"
        NOT_EQUALS = "not_equals", "Not equals"
        IN = "in", "In"
        NOT_IN = "not_in", "Not in"
        GREATER_THAN = "greater_than", "Greater than"
        GREATER_OR_EQUAL = "greater_or_equal", "Greater than or equal"
        LESS_THAN = "less_than", "Less than"
        LESS_OR_EQUAL = "less_or_equal", "Less than or equal"
        BETWEEN = "between", "Between"
        CONTAINS_ANY = "contains_any", "Contains any"
        CONTAINS_ALL = "contains_all", "Contains all"
        EXISTS = "exists", "Exists"
        NOT_EXISTS = "not_exists", "Does not exist"

    scheme_version = models.ForeignKey(
        SchemeVersion, on_delete=models.CASCADE, related_name="eligibility_rules"
    )
    field_path = models.CharField(max_length=255)
    operator = models.CharField(max_length=32, choices=Operator.choices)
    expected_value = models.JSONField(null=True, blank=True)
    mandatory = models.BooleanField(default=True)
    rule_group = models.CharField(max_length=100, blank=True)
    evidence_text = models.TextField()
    evidence_page = models.PositiveIntegerField(null=True, blank=True)
    extraction_confidence = models.DecimalField(
        max_digits=5, decimal_places=4, null=True, blank=True
    )
    manually_verified = models.BooleanField(default=False)

    class Meta:
        ordering = ["scheme_version", "rule_group", "field_path"]

    def __str__(self) -> str:
        return f"{self.field_path} {self.operator} {self.expected_value}"
