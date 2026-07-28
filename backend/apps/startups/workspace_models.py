from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.models import TimeStampedModel


class ComplianceRecord(TimeStampedModel):
    class ComplianceType(models.TextChoices):
        DPIIT = "dpiit", "DPIIT recognition"
        UDYAM = "udyam", "Udyam registration"
        GST = "gst", "GST registration"
        FSSAI = "fssai", "FSSAI licence"
        SHOPS_ESTABLISHMENT = (
            "shops_establishment",
            "Shops and Establishments registration",
        )
        PROFESSIONAL_TAX = "professional_tax", "Professional tax"
        IMPORT_EXPORT = "import_export", "Import Export Code"
        TRADEMARK = "trademark", "Trademark"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        IN_PROGRESS = "in_progress", "In progress"
        ACTIVE = "active", "Active"
        REJECTED = "rejected", "Rejected"
        SUSPENDED = "suspended", "Suspended"
        EXPIRED = "expired", "Expired"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="compliance_records",
    )
    startup_profile = models.ForeignKey(
        "startups.StartupProfile",
        on_delete=models.CASCADE,
        related_name="compliance_records",
    )
    compliance_type = models.CharField(
        max_length=40,
        choices=ComplianceType.choices,
    )
    title = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=255, blank=True)
    issuing_authority = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )
    issued_on = models.DateField(null=True, blank=True)
    expires_on = models.DateField(null=True, blank=True)
    renewal_reminder_days = models.PositiveSmallIntegerField(default=30)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["expires_on", "title", "id"]
        indexes = [
            models.Index(
                fields=["owner", "startup_profile", "status"],
                name="startup_comp_owner_status",
            ),
            models.Index(
                fields=["startup_profile", "expires_on"],
                name="startup_comp_expiry",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(issued_on__isnull=True)
                    | Q(expires_on__isnull=True)
                    | Q(expires_on__gte=models.F("issued_on"))
                ),
                name="startup_comp_dates_valid",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if (
            self.owner_id
            and self.startup_profile_id
            and self.startup_profile.owner_id != self.owner_id
        ):
            raise ValidationError(
                {
                    "startup_profile": (
                        "The startup profile must belong to the compliance owner."
                    )
                }
            )

    @property
    def effective_status(self) -> str:
        if self.expires_on and self.expires_on < timezone.localdate():
            return self.Status.EXPIRED
        return self.status

    @property
    def days_until_expiry(self) -> int | None:
        if self.expires_on is None:
            return None
        return (self.expires_on - timezone.localdate()).days

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.startup_profile}: {self.title}"


class FounderVaultDocument(TimeStampedModel):
    class Category(models.TextChoices):
        INCORPORATION = "incorporation", "Incorporation"
        TAX = "tax", "Tax and finance"
        COMPLIANCE = "compliance", "Compliance"
        FOUNDER = "founder", "Founder identity"
        PRODUCT = "product", "Product and technology"
        FINANCIAL = "financial", "Financial statements"
        APPLICATION = "application", "Scheme application"
        CONTRACT = "contract", "Contract"
        OTHER = "other", "Other"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vault_documents",
    )
    startup_profile = models.ForeignKey(
        "startups.StartupProfile",
        on_delete=models.CASCADE,
        related_name="vault_documents",
    )
    title = models.CharField(max_length=255)
    category = models.CharField(
        max_length=32,
        choices=Category.choices,
        default=Category.OTHER,
    )
    original_filename = models.CharField(max_length=500)
    mime_type = models.CharField(max_length=255)
    size_bytes = models.PositiveBigIntegerField()
    content_hash = models.CharField(max_length=64, db_index=True)
    storage_key = models.CharField(max_length=1000, unique=True)
    bucket_name = models.CharField(max_length=255)
    expires_on = models.DateField(null=True, blank=True)
    tags = models.JSONField(default=list, blank=True)
    is_archived = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["owner", "startup_profile", "is_archived"],
                name="startup_vault_owner_active",
            ),
            models.Index(
                fields=["startup_profile", "category"],
                name="startup_vault_category",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "startup_profile", "content_hash"],
                name="startup_vault_unique_hash",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if (
            self.owner_id
            and self.startup_profile_id
            and self.startup_profile.owner_id != self.owner_id
        ):
            raise ValidationError(
                {
                    "startup_profile": (
                        "The startup profile must belong to the document owner."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title


class ConsultantProfile(TimeStampedModel):
    class VerificationStatus(models.TextChoices):
        UNVERIFIED = "unverified", "Unverified"
        PENDING = "pending", "Pending review"
        VERIFIED = "verified", "Verified"
        SUSPENDED = "suspended", "Suspended"

    class Availability(models.TextChoices):
        AVAILABLE = "available", "Available"
        LIMITED = "limited", "Limited availability"
        UNAVAILABLE = "unavailable", "Unavailable"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="consultant_profile",
    )
    headline = models.CharField(max_length=255)
    bio = models.TextField(blank=True)
    expertise = models.JSONField(default=list, blank=True)
    languages = models.JSONField(default=list, blank=True)
    states_served = models.JSONField(default=list, blank=True)
    industries = models.JSONField(default=list, blank=True)
    hourly_rate = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    availability = models.CharField(
        max_length=20,
        choices=Availability.choices,
        default=Availability.AVAILABLE,
    )
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.UNVERIFIED,
    )
    is_public = models.BooleanField(default=False)
    years_experience = models.PositiveSmallIntegerField(default=0)
    sessions_completed = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-verification_status", "user__first_name", "user__username"]
        indexes = [
            models.Index(
                fields=["is_public", "verification_status", "availability"],
                name="startup_consultant_directory",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(average_rating__isnull=True)
                    | Q(average_rating__gte=0, average_rating__lte=5)
                ),
                name="startup_consultant_rating_range",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        role = getattr(self.user, "role", "") if self.user_id else ""
        if role not in {"consultant", "admin"}:
            raise ValidationError(
                {"user": "Only consultant or administrator accounts may publish a consultant profile."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.headline


class ApplicationTask(TimeStampedModel):
    class Status(models.TextChoices):
        TODO = "todo", "To do"
        IN_PROGRESS = "in_progress", "In progress"
        BLOCKED = "blocked", "Blocked"
        COMPLETED = "completed", "Completed"

    application = models.ForeignKey(
        "recommendations.SchemeApplicationTracker",
        on_delete=models.CASCADE,
        related_name="workflow_tasks",
    )
    title = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
    )
    due_on = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "due_on", "created_at", "id"]
        indexes = [
            models.Index(
                fields=["application", "status", "due_on"],
                name="startup_app_task_status",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.status == self.Status.COMPLETED and self.completed_at is None:
            self.completed_at = timezone.now()
        elif self.status != self.Status.COMPLETED:
            self.completed_at = None

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title


class ApplicationStageEvent(TimeStampedModel):
    application = models.ForeignKey(
        "recommendations.SchemeApplicationTracker",
        on_delete=models.CASCADE,
        related_name="stage_events",
    )
    from_stage = models.CharField(max_length=30, blank=True)
    to_stage = models.CharField(max_length=30)
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="application_stage_events",
    )
    occurred_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-occurred_at", "-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["application", "-occurred_at"],
                name="startup_app_event_latest",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Application stage events are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Application stage events cannot be deleted.")

    def __str__(self) -> str:
        return f"{self.application_id}: {self.from_stage} -> {self.to_stage}"
