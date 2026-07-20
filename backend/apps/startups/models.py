from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class StartupProfile(TimeStampedModel):
    class Stage(models.TextChoices):
        IDEA = "idea", "Idea"
        VALIDATION = "validation", "Problem validation"
        PROTOTYPE = "prototype", "Prototype"
        MVP = "mvp", "Minimum viable product"
        PILOT = "pilot", "Pilot"
        EARLY_REVENUE = "early_revenue", "Early revenue"
        GROWTH = "growth", "Growth"
        EXPANSION = "expansion", "Expansion"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="startup_profiles",
    )
    startup_name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    incorporation_type = models.CharField(max_length=100, blank=True)
    incorporation_date = models.DateField(null=True, blank=True)
    state = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    stage = models.CharField(max_length=32, choices=Stage.choices)
    sectors = models.JSONField(default=list, blank=True)
    technologies = models.JSONField(default=list, blank=True)
    founder_categories = models.JSONField(default=list, blank=True)
    founder_gender = models.CharField(max_length=50, blank=True)
    dpiit_recognized = models.BooleanField(null=True, blank=True)
    udyam_registered = models.BooleanField(null=True, blank=True)
    annual_turnover = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
    )
    revenue_stage = models.CharField(max_length=100, blank=True)
    funding_required = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
    )
    funding_purpose = models.TextField(blank=True)
    team_size = models.PositiveIntegerField(null=True, blank=True)
    profile_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["startup_name"]

    def __str__(self) -> str:
        return self.startup_name


class StartupReadinessAssessment(TimeStampedModel):
    class Status(models.TextChoices):
        BLOCKED = "blocked", "Blocked"
        READY_WITH_RECOMMENDATIONS = (
            "ready_with_recommendations",
            "Ready with recommendations",
        )
        READY = "ready", "Ready"

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="startup_readiness_assessments",
    )
    startup_profile = models.ForeignKey(
        StartupProfile,
        on_delete=models.CASCADE,
        related_name="readiness_assessments",
    )
    assessment_date = models.DateField()
    profile_snapshot = models.JSONField(default=dict)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
    )
    score = models.PositiveSmallIntegerField()
    critical_score = models.PositiveSmallIntegerField()
    recommended_score = models.PositiveSmallIntegerField()
    findings = models.JSONField(default=list)
    blocking_findings = models.JSONField(default=list)
    summary = models.TextField()
    engine_version = models.CharField(max_length=64)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["startup_profile", "-created_at"],
                name="startup_ready_profile_created",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    score__gte=0,
                    score__lte=100,
                    critical_score__gte=0,
                    critical_score__lte=100,
                    recommended_score__gte=0,
                    recommended_score__lte=100,
                ),
                name="startup_ready_scores_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.startup_profile} readiness on {self.assessment_date}"
