import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.schemes.models import EligibilityRule, SchemeVersion
from apps.startups.models import StartupProfile


class RecommendationGenerationRun(TimeStampedModel):
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recommendation_generation_runs",
    )
    startup_profile = models.ForeignKey(
        StartupProfile,
        on_delete=models.CASCADE,
        related_name="recommendation_generation_runs",
    )
    assessment_date = models.DateField()
    ranking_version = models.CharField(
        max_length=50,
        default="recommendations-v1",
    )
    profile_snapshot = models.JSONField(default=dict)
    assessed_scheme_count = models.PositiveIntegerField(default=0)
    recommendation_count = models.PositiveIntegerField(default=0)
    excluded_schemes = models.JSONField(default=list)
    recommendation_snapshot = models.JSONField(default=list)
    is_current = models.BooleanField(default=True)
    completed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["startup_profile", "-completed_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["startup_profile"],
                condition=Q(is_current=True),
                name="unique_current_recommendation_run",
            )
        ]


class EligibilityAssessment(TimeStampedModel):
    class Result(models.TextChoices):
        ELIGIBLE = "eligible", "Eligible"
        INELIGIBLE = "ineligible", "Ineligible"
        LIKELY = "likely_eligible", "Likely eligible"
        CONDITIONAL = "conditionally_eligible", "Conditionally eligible"
        INSUFFICIENT = "insufficient_information", "Insufficient information"
        VERIFY = "verification_required", "Verification required"
        CLOSED = "application_closed", "Application closed"

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    startup_profile = models.ForeignKey(
        StartupProfile,
        on_delete=models.CASCADE,
        related_name="assessments",
    )
    scheme_version = models.ForeignKey(
        SchemeVersion,
        on_delete=models.PROTECT,
        related_name="assessments",
    )
    generation_run = models.ForeignKey(
        RecommendationGenerationRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assessments",
    )
    assessment_date = models.DateField(default=timezone.localdate)
    profile_snapshot = models.JSONField(default=dict)
    result = models.CharField(max_length=40, choices=Result.choices)
    matched_rules = models.JSONField(default=list)
    failed_rules = models.JSONField(default=list)
    unknown_rules = models.JSONField(default=list)
    explanation = models.TextField(blank=True)
    engine_version = models.CharField(max_length=50, default="rules-v1")


class EligibilityVerificationSubmission(TimeStampedModel):
    startup_profile = models.ForeignKey(
        StartupProfile,
        on_delete=models.CASCADE,
        related_name="eligibility_verification_submissions",
    )
    scheme_version = models.ForeignKey(
        SchemeVersion,
        on_delete=models.PROTECT,
        related_name="eligibility_verification_submissions",
    )
    eligibility_rule = models.ForeignKey(
        EligibilityRule,
        on_delete=models.PROTECT,
        related_name="verification_submissions",
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eligibility_verification_submissions",
    )
    supersedes = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="superseding_submissions",
    )
    is_current = models.BooleanField(default=True)
    claim_value = models.JSONField(null=True, blank=True)
    claim_text = models.TextField(blank=True)

    class Meta:
        ordering = ["startup_profile", "-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "startup_profile",
                    "eligibility_rule",
                ],
                condition=Q(is_current=True),
                name="unique_current_eligibility_verification",
            ),
        ]
        indexes = [
            models.Index(
                fields=[
                    "startup_profile",
                    "is_current",
                    "-created_at",
                ],
                name="elig_ver_profile_current",
            ),
            models.Index(
                fields=[
                    "eligibility_rule",
                    "is_current",
                    "-created_at",
                ],
                name="elig_ver_rule_current",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}

        if self.eligibility_rule_id and self.scheme_version_id:
            rule_scheme_version_id = (
                EligibilityRule.objects.filter(
                    pk=self.eligibility_rule_id,
                )
                .values_list("scheme_version_id", flat=True)
                .first()
            )
            if (
                rule_scheme_version_id is not None
                and rule_scheme_version_id != self.scheme_version_id
            ):
                errors["eligibility_rule"] = (
                    "The eligibility rule must belong to the selected scheme version."
                )

        if self.supersedes_id:
            if self.pk and self.supersedes_id == self.pk:
                errors["supersedes"] = "A submission cannot supersede itself."
            else:
                superseded = (
                    type(self)
                    .objects.filter(pk=self.supersedes_id)
                    .values(
                        "startup_profile_id",
                        "scheme_version_id",
                        "eligibility_rule_id",
                    )
                    .first()
                )
                if superseded is not None:
                    if superseded["startup_profile_id"] != self.startup_profile_id:
                        errors["supersedes"] = (
                            "The superseded submission must belong to the same startup profile."
                        )
                    elif (
                        superseded["scheme_version_id"] != self.scheme_version_id
                        or superseded["eligibility_rule_id"] != self.eligibility_rule_id
                    ):
                        errors["supersedes"] = (
                            "The superseded submission must target the "
                            "same scheme version and eligibility rule."
                        )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.startup_profile} - {self.eligibility_rule.field_path}"


class EligibilityVerificationEvidence(TimeStampedModel):
    submission = models.ForeignKey(
        EligibilityVerificationSubmission,
        on_delete=models.CASCADE,
        related_name="evidence",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eligibility_verification_evidence_uploads",
    )
    filename = models.CharField(max_length=500)
    mime_type = models.CharField(max_length=255)
    size_bytes = models.PositiveBigIntegerField()
    content_hash = models.CharField(
        max_length=64,
        db_index=True,
    )
    storage_key = models.CharField(
        max_length=1000,
        unique=True,
    )

    class Meta:
        ordering = ["submission", "created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "submission",
                    "content_hash",
                ],
                name="unique_submission_evidence_hash",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.submission_id} - {self.filename}"


class EligibilityVerificationDecisionQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Eligibility verification decisions are immutable.")

    def delete(self):
        raise ValidationError("Eligibility verification decisions cannot be deleted.")


class EligibilityVerificationDecision(TimeStampedModel):
    class Outcome(models.TextChoices):
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    objects = EligibilityVerificationDecisionQuerySet.as_manager()

    submission = models.ForeignKey(
        EligibilityVerificationSubmission,
        on_delete=models.PROTECT,
        related_name="decisions",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="eligibility_verification_decisions",
    )
    outcome = models.CharField(
        max_length=20,
        choices=Outcome.choices,
    )
    verified_value = models.JSONField(
        null=True,
        blank=True,
    )
    review_notes = models.TextField(blank=True)
    valid_from = models.DateField(
        default=timezone.localdate,
    )
    expires_on = models.DateField(
        null=True,
        blank=True,
    )
    submission_snapshot = models.JSONField(default=dict)
    rule_snapshot = models.JSONField(default=dict)
    evidence_snapshot = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["submission", "-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        outcome="approved",
                        verified_value__isnull=False,
                    )
                    | Q(
                        outcome="rejected",
                        verified_value__isnull=True,
                    )
                ),
                name="elig_ver_decision_value_matches",
            ),
            models.CheckConstraint(
                condition=(Q(expires_on__isnull=True) | Q(expires_on__gte=models.F("valid_from"))),
                name="elig_ver_decision_dates_valid",
            ),
        ]
        indexes = [
            models.Index(
                fields=[
                    "submission",
                    "-created_at",
                ],
                name="elig_ver_decision_latest",
            ),
            models.Index(
                fields=[
                    "outcome",
                    "valid_from",
                    "expires_on",
                ],
                name="elig_ver_decision_validity",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Eligibility verification decisions are immutable.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Eligibility verification decisions cannot be deleted.")

    def __str__(self) -> str:
        return f"{self.submission_id} - {self.outcome}"


class Recommendation(TimeStampedModel):
    startup_profile = models.ForeignKey(
        StartupProfile,
        on_delete=models.CASCADE,
        related_name="recommendations",
    )
    scheme_version = models.ForeignKey(
        SchemeVersion,
        on_delete=models.PROTECT,
    )
    assessment = models.ForeignKey(
        EligibilityAssessment,
        on_delete=models.PROTECT,
    )
    generation_run = models.ForeignKey(
        RecommendationGenerationRun,
        on_delete=models.PROTECT,
        related_name="recommendations",
    )
    generation_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        db_index=True,
    )
    ranking_version = models.CharField(
        max_length=50,
        default="recommendations-v1",
    )
    rank = models.PositiveIntegerField()
    score = models.DecimalField(max_digits=7, decimal_places=6)
    score_breakdown = models.JSONField(default=dict)
    evidence_snapshot = models.JSONField(default=dict)
    # ML Engine fields
    svm_score = models.DecimalField(
        max_digits=7, decimal_places=6, null=True, blank=True,
        help_text="SVM-predicted probability of scheme acquisition success (0.0–1.0).",
    )
    ml_score_breakdown = models.JSONField(
        default=dict, blank=True,
        help_text="Breakdown of the blended ML+heuristic score components.",
    )

    class Meta:
        ordering = ["startup_profile", "rank"]
        constraints = [
            models.UniqueConstraint(
                fields=["generation_id", "rank"],
                name="unique_recommendation_generation_rank",
            ),
            models.UniqueConstraint(
                fields=["generation_run", "rank"],
                name="unique_recommendation_run_rank",
            ),
        ]


class SchemeApplicationTracker(TimeStampedModel):
    class Stage(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved / Granted"
        REJECTED = "rejected", "Rejected"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scheme_applications",
    )
    startup_profile = models.ForeignKey(
        "startups.StartupProfile",
        on_delete=models.CASCADE,
        related_name="scheme_applications",
    )
    scheme_version = models.ForeignKey(
        "schemes.SchemeVersion",
        on_delete=models.CASCADE,
        related_name="tracker_applications",
    )
    stage = models.CharField(
        max_length=30,
        choices=Stage.choices,
        default=Stage.DRAFT,
    )

    def clean(self):
        super().clean()
        if (
            self.startup_profile_id
            and self.owner_id
            and self.startup_profile.owner_id != self.owner_id
        ):
            raise ValidationError(
                {"startup_profile": "The startup profile must belong to the application tracker owner."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
    submission_reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    application_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["startup_profile", "scheme_version"],
                name="unique_startup_scheme_tracker_application",
            )
        ]

    def __str__(self) -> str:
        cname = self.scheme_version.scheme.canonical_name
        return f"{self.startup_profile.startup_name} -> {cname} ({self.stage})"

