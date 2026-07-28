from django.core.exceptions import ValidationError
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


class AuthorityAlias(TimeStampedModel):
    authority = models.ForeignKey(
        Authority,
        on_delete=models.CASCADE,
        related_name="aliases",
    )
    alias = models.CharField(max_length=500)
    normalized_alias = models.CharField(
        max_length=500,
        unique=True,
    )
    source = models.CharField(
        max_length=100,
        blank=True,
    )
    verified = models.BooleanField(default=False)

    class Meta:
        ordering = ["normalized_alias"]

    def __str__(self) -> str:
        return f"{self.alias} → {self.authority.name}"


class GraphReviewStatus(models.TextChoices):
    REVIEW_REQUIRED = (
        "review_required",
        "Review required",
    )
    VERIFIED = "verified", "Verified"
    REJECTED = "rejected", "Rejected"
    RETIRED = "retired", "Retired"


class GraphRecordOrigin(models.TextChoices):
    MANUAL = "manual", "Manual"
    EXTRACTED = "extracted", "Extracted"
    IMPORTED = "imported", "Imported"


class PrerequisiteConcept(TimeStampedModel):
    class Category(models.TextChoices):
        REGISTRATION = "registration", "Registration"
        CERTIFICATION = "certification", "Certification"
        COMPLIANCE = "compliance", "Compliance"
        FINANCIAL = "financial", "Financial readiness"
        OPERATIONAL = "operational", "Operational readiness"
        SCHEME_ACCESS = "scheme_access", "Scheme access"
        OTHER = "other", "Other"

    class LifecycleStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        VERIFIED = "verified", "Verified"
        RETIRED = "retired", "Retired"

    key = models.SlugField(
        max_length=150,
        unique=True,
    )
    name = models.CharField(max_length=300)
    description = models.TextField()
    category = models.CharField(
        max_length=40,
        choices=Category.choices,
        default=Category.OTHER,
    )
    lifecycle_status = models.CharField(
        max_length=30,
        choices=LifecycleStatus.choices,
        default=LifecycleStatus.DRAFT,
    )
    source_document = models.ForeignKey(
        SourceDocument,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="prerequisite_concepts",
    )
    evidence_text = models.TextField(blank=True)
    evidence_page = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    verified_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_prerequisite_concepts",
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        ordering = [
            "category",
            "name",
        ]
        indexes = [
            models.Index(
                fields=[
                    "lifecycle_status",
                    "category",
                ],
            ),
        ]

    def clean(self) -> None:
        super().clean()

        if self.lifecycle_status != self.LifecycleStatus.VERIFIED:
            return

        errors = {}

        if self.source_document_id is None:
            errors["source_document"] = "A verified prerequisite requires an official source."

        if not self.evidence_text.strip():
            errors["evidence_text"] = "A verified prerequisite requires source evidence."

        if self.verified_by_id is None:
            errors["verified_by"] = "A verified prerequisite requires a reviewer."

        if self.verified_at is None:
            errors["verified_at"] = "A verified prerequisite requires a review timestamp."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class ReviewedGraphRelationship(TimeStampedModel):
    origin = models.CharField(
        max_length=20,
        choices=GraphRecordOrigin.choices,
        default=GraphRecordOrigin.MANUAL,
    )
    review_status = models.CharField(
        max_length=30,
        choices=GraphReviewStatus.choices,
        default=GraphReviewStatus.REVIEW_REQUIRED,
    )
    source_document = models.ForeignKey(
        SourceDocument,
        on_delete=models.PROTECT,
        related_name="+",
    )
    evidence_text = models.TextField()
    evidence_page = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    review_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        abstract = True

    def clean(self) -> None:
        super().clean()

        errors = {}

        if not self.evidence_text.strip():
            errors["evidence_text"] = "A graph relationship requires source evidence."

        if self.review_status == GraphReviewStatus.VERIFIED:
            if self.reviewed_by_id is None:
                errors["reviewed_by"] = "A verified relationship requires a reviewer."

            if self.reviewed_at is None:
                errors["reviewed_at"] = "A verified relationship requires a review timestamp."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class SchemePrerequisite(ReviewedGraphRelationship):
    class RequirementType(models.TextChoices):
        HARD = "hard", "Hard prerequisite"
        SUPPORTING = "supporting", "Supporting prerequisite"

    scheme_version = models.ForeignKey(
        SchemeVersion,
        on_delete=models.CASCADE,
        related_name="prerequisite_relationships",
    )
    prerequisite = models.ForeignKey(
        PrerequisiteConcept,
        on_delete=models.PROTECT,
        related_name="scheme_relationships",
    )
    requirement_type = models.CharField(
        max_length=20,
        choices=RequirementType.choices,
        default=RequirementType.HARD,
    )

    class Meta:
        ordering = [
            "scheme_version",
            "requirement_type",
            "prerequisite",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "scheme_version",
                    "prerequisite",
                ],
                name="unique_scheme_version_prerequisite",
            ),
        ]
        indexes = [
            models.Index(
                fields=[
                    "review_status",
                    "scheme_version",
                ],
            ),
        ]

    def clean(self) -> None:
        super().clean()

        if self.review_status != GraphReviewStatus.VERIFIED:
            return

        errors = {}

        if self.scheme_version.verification_status != SchemeVersion.VerificationStatus.VERIFIED:
            errors["scheme_version"] = (
                "A verified prerequisite relationship requires a verified scheme version."
            )

        if self.prerequisite.lifecycle_status != PrerequisiteConcept.LifecycleStatus.VERIFIED:
            errors["prerequisite"] = (
                "A verified relationship requires a verified prerequisite concept."
            )

        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        return f"{self.scheme_version} requires {self.prerequisite}"


class SchemeUnlock(ReviewedGraphRelationship):
    predecessor_version = models.ForeignKey(
        SchemeVersion,
        on_delete=models.CASCADE,
        related_name="unlock_relationships_out",
    )
    unlocked_version = models.ForeignKey(
        SchemeVersion,
        on_delete=models.CASCADE,
        related_name="unlock_relationships_in",
    )

    class Meta:
        ordering = [
            "predecessor_version",
            "unlocked_version",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "predecessor_version",
                    "unlocked_version",
                ],
                name="unique_scheme_version_unlock",
            ),
        ]
        indexes = [
            models.Index(
                fields=[
                    "review_status",
                    "predecessor_version",
                ],
            ),
            models.Index(
                fields=[
                    "review_status",
                    "unlocked_version",
                ],
            ),
        ]

    def clean(self) -> None:
        super().clean()

        errors = {}

        if (
            self.predecessor_version_id is not None
            and self.unlocked_version_id is not None
            and self.predecessor_version.scheme_id == self.unlocked_version.scheme_id
        ):
            errors["unlocked_version"] = "A scheme cannot unlock itself."

        if self.review_status == GraphReviewStatus.VERIFIED:
            for field_name in (
                "predecessor_version",
                "unlocked_version",
            ):
                version = getattr(self, field_name)

                if version.verification_status != SchemeVersion.VerificationStatus.VERIFIED:
                    errors[field_name] = "A verified unlock requires verified scheme versions."

        if errors:
            raise ValidationError(errors)

        if (
            self.review_status == GraphReviewStatus.VERIFIED
            and self.predecessor_version_id is not None
            and self.unlocked_version_id is not None
        ):
            from apps.schemes.services.prerequisite_graph import (
                validate_no_unlock_cycles,
            )

            validate_no_unlock_cycles(
                extra_edge=(
                    self.predecessor_version.scheme_id,
                    self.unlocked_version.scheme_id,
                ),
                exclude_relationship_id=self.pk,
            )

    def __str__(self) -> str:
        return f"{self.predecessor_version} unlocks {self.unlocked_version}"


class SchemeGraphProjectionRun(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    graph_version = models.CharField(
        max_length=100,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    source_hash = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
    )
    scheme_node_count = models.PositiveIntegerField(default=0)
    prerequisite_node_count = models.PositiveIntegerField(
        default=0,
    )
    prerequisite_edge_count = models.PositiveIntegerField(
        default=0,
    )
    unlock_edge_count = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    finished_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.graph_version} - {self.status} - {self.created_at:%Y-%m-%d %H:%M}"
