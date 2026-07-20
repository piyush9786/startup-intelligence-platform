from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.schemes.models import SchemeVersion
from apps.startups.models import StartupProfile


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
    assessment_date = models.DateField(default=timezone.localdate)
    profile_snapshot = models.JSONField(default=dict)
    result = models.CharField(max_length=40, choices=Result.choices)
    matched_rules = models.JSONField(default=list)
    failed_rules = models.JSONField(default=list)
    unknown_rules = models.JSONField(default=list)
    explanation = models.TextField(blank=True)
    engine_version = models.CharField(max_length=50, default="rules-v1")


class Recommendation(TimeStampedModel):
    startup_profile = models.ForeignKey(
        StartupProfile,
        on_delete=models.CASCADE,
        related_name="recommendations",
    )
    scheme_version = models.ForeignKey(SchemeVersion, on_delete=models.PROTECT)
    assessment = models.ForeignKey(EligibilityAssessment, on_delete=models.PROTECT)
    rank = models.PositiveIntegerField()
    score = models.DecimalField(max_digits=7, decimal_places=6)
    score_breakdown = models.JSONField(default=dict)
    evidence_snapshot = models.JSONField(default=dict)
