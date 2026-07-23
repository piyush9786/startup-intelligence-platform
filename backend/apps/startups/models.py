from django.conf import settings
from django.db import models
from django.utils import timezone

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


class StartupAssessmentDraft(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        SUPERSEDED = "superseded", "Superseded"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="startup_assessment_drafts",
    )
    startup_profile = models.ForeignKey(
        StartupProfile,
        on_delete=models.CASCADE,
        related_name="assessment_drafts",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    current_step = models.PositiveSmallIntegerField(default=1)
    data = models.JSONField(default=dict, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    submitted_profile_snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(
                fields=["owner", "-updated_at"],
                name="startup_draft_owner_updated",
            ),
            models.Index(
                fields=["startup_profile", "-updated_at"],
                name="startup_draft_profile_updated",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    current_step__gte=1,
                    current_step__lte=8,
                ),
                name="startup_draft_step_range",
            ),
            models.UniqueConstraint(
                fields=["owner", "startup_profile"],
                condition=models.Q(
                    status="draft",
                    startup_profile__isnull=False,
                ),
                name="startup_one_draft_per_profile",
            ),
            models.UniqueConstraint(
                fields=["owner"],
                condition=models.Q(
                    status="draft",
                    startup_profile__isnull=True,
                ),
                name="startup_one_onboarding_draft",
            ),
        ]

    def __str__(self) -> str:
        profile_name = (
            self.startup_profile.startup_name
            if self.startup_profile_id
            else self.data.get("startup_name", "New startup")
        )
        return f"{profile_name} assessment ({self.status})"


class OnboardingProgress(TimeStampedModel):
    TOUR_VERSION = "founder-onboarding-v1"
    TOTAL_STEPS = 4

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DISMISSED = "dismissed", "Dismissed"
        COMPLETED = "completed", "Completed"

    class Variant(models.TextChoices):
        EMPTY_PROFILE = "empty_profile", "Empty profile"
        RETURNING_FOUNDER = (
            "returning_founder",
            "Returning founder",
        )

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="startup_onboarding_progress",
    )
    tour_version = models.CharField(
        max_length=64,
        default=TOUR_VERSION,
    )
    variant = models.CharField(
        max_length=32,
        choices=Variant.choices,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    current_step = models.PositiveSmallIntegerField(
        default=1,
    )
    started_at = models.DateTimeField(
        default=timezone.now,
    )
    dismissed_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-updated_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    current_step__gte=1,
                    current_step__lte=4,
                ),
                name="startup_onboarding_step_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.owner} onboarding ({self.tour_version}, {self.status})"


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


class StartupReadinessActionPlan(TimeStampedModel):
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="startup_readiness_action_plans",
    )
    startup_profile = models.ForeignKey(
        StartupProfile,
        on_delete=models.CASCADE,
        related_name="readiness_action_plans",
    )
    source_assessment = models.ForeignKey(
        StartupReadinessAssessment,
        on_delete=models.PROTECT,
        related_name="action_plans",
    )
    source_assessment_snapshot = models.JSONField(default=dict)
    readiness_status = models.CharField(
        max_length=32,
        choices=StartupReadinessAssessment.Status.choices,
    )
    has_actions = models.BooleanField()
    blocker_count = models.PositiveIntegerField()
    recommendation_count = models.PositiveIntegerField()
    total_action_count = models.PositiveIntegerField()
    next_action = models.TextField(null=True, blank=True)
    items = models.JSONField(default=list)
    source_engine_version = models.CharField(max_length=64)
    planner_version = models.CharField(max_length=64)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["startup_profile", "-created_at"],
                name="startup_action_profile_created",
            ),
            models.Index(
                fields=["source_assessment", "-created_at"],
                name="startup_action_source_created",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        has_actions=True,
                        total_action_count__gt=0,
                        next_action__isnull=False,
                    )
                    | models.Q(
                        has_actions=False,
                        total_action_count=0,
                        next_action__isnull=True,
                    )
                ),
                name="startup_action_presence_match",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    total_action_count=(
                        models.F("blocker_count") + models.F("recommendation_count")
                    ),
                ),
                name="startup_action_counts_match",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.startup_profile} action plan from {self.source_assessment_id}"


class StartupStartingPlan(TimeStampedModel):
    PLAN_VERSION = "startup-starting-plan-v1"

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="startup_starting_plans",
    )
    startup_profile = models.ForeignKey(
        StartupProfile,
        on_delete=models.CASCADE,
        related_name="starting_plans",
    )
    source_assessment = models.ForeignKey(
        StartupReadinessAssessment,
        on_delete=models.PROTECT,
        related_name="starting_plans",
    )
    source_action_plan = models.ForeignKey(
        StartupReadinessActionPlan,
        on_delete=models.PROTECT,
        related_name="starting_plans",
    )
    recommendation_generation_run = models.ForeignKey(
        "recommendations.RecommendationGenerationRun",
        on_delete=models.PROTECT,
        related_name="starting_plans",
    )
    profile_snapshot = models.JSONField(default=dict)
    readiness_snapshot = models.JSONField(default=dict)
    action_plan_snapshot = models.JSONField(default=dict)
    recommendation_generation_snapshot = models.JSONField(default=dict)
    recommendations_snapshot = models.JSONField(default=list)
    readiness_item_count = models.PositiveIntegerField(default=0)
    recommendation_item_count = models.PositiveIntegerField(default=0)
    total_item_count = models.PositiveIntegerField(default=0)
    next_item = models.JSONField(null=True, blank=True)
    items = models.JSONField(default=list)
    plan_version = models.CharField(
        max_length=64,
        default=PLAN_VERSION,
    )
    is_current = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["startup_profile", "-created_at"],
                name="startup_start_profile_created",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "source_action_plan",
                    "recommendation_generation_run",
                ],
                name="startup_unique_starting_plan_sources",
            ),
            models.UniqueConstraint(
                fields=["startup_profile"],
                condition=models.Q(is_current=True),
                name="startup_unique_current_starting_plan",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    total_item_count=(
                        models.F("readiness_item_count")
                        + models.F("recommendation_item_count")
                    ),
                ),
                name="startup_start_plan_counts_match",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        total_item_count=0,
                        next_item__isnull=True,
                    )
                    | models.Q(
                        total_item_count__gt=0,
                        next_item__isnull=False,
                    )
                ),
                name="startup_start_plan_next_match",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.startup_profile} starting plan {self.plan_version}"


class StartupAdvisorSnapshot(TimeStampedModel):
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="startup_advisor_snapshots",
    )
    startup_profile = models.ForeignKey(
        StartupProfile,
        on_delete=models.CASCADE,
        related_name="advisor_snapshots",
    )
    readiness_assessment = models.ForeignKey(
        StartupReadinessAssessment,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="advisor_snapshots",
    )
    readiness_action_plan = models.ForeignKey(
        StartupReadinessActionPlan,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="advisor_snapshots",
    )
    recommendation_generation_run = models.ForeignKey(
        "recommendations.RecommendationGenerationRun",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="advisor_snapshots",
    )
    has_readiness_assessment = models.BooleanField()
    has_action_plan = models.BooleanField()
    has_recommendation_generation = models.BooleanField()
    profile_snapshot = models.JSONField(default=dict)
    readiness_snapshot = models.JSONField(default=dict)
    action_plan_snapshot = models.JSONField(default=dict)
    recommendation_generation_snapshot = models.JSONField(default=dict)
    recommendations_snapshot = models.JSONField(default=list)
    recommendation_count = models.PositiveIntegerField(default=0)
    snapshot_version = models.CharField(
        max_length=64,
        default="startup-advisor-snapshot-v1",
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["startup_profile", "-created_at"],
                name="startup_adv_profile_created",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        has_readiness_assessment=True,
                        readiness_assessment__isnull=False,
                    )
                    | models.Q(
                        has_readiness_assessment=False,
                        readiness_assessment__isnull=True,
                    )
                ),
                name="startup_adv_readiness_match",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        has_action_plan=True,
                        readiness_action_plan__isnull=False,
                    )
                    | models.Q(
                        has_action_plan=False,
                        readiness_action_plan__isnull=True,
                    )
                ),
                name="startup_adv_action_match",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        has_recommendation_generation=True,
                        recommendation_generation_run__isnull=False,
                    )
                    | models.Q(
                        has_recommendation_generation=False,
                        recommendation_generation_run__isnull=True,
                        recommendation_count=0,
                    )
                ),
                name="startup_adv_generation_match",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.startup_profile} advisor snapshot {self.snapshot_version}"


class StartupAdvisorBriefing(TimeStampedModel):
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="startup_advisor_briefings",
    )
    startup_profile = models.ForeignKey(
        StartupProfile,
        on_delete=models.CASCADE,
        related_name="advisor_briefings",
    )
    source_snapshot = models.ForeignKey(
        StartupAdvisorSnapshot,
        on_delete=models.PROTECT,
        related_name="briefings",
    )
    provider = models.CharField(max_length=64)
    model_name = models.CharField(max_length=255)
    prompt_version = models.CharField(max_length=64)
    schema_version = models.CharField(max_length=64)
    generation_parameters = models.JSONField(default=dict)
    prompt_snapshot = models.JSONField(default=dict)
    briefing = models.JSONField(default=dict)
    prompt_token_count = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    output_token_count = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    total_duration_ns = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )
    response_metadata = models.JSONField(default=dict)
    completed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-completed_at", "-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["startup_profile", "-created_at"],
                name="st_brief_profile_created",
            ),
            models.Index(
                fields=["source_snapshot", "-created_at"],
                name="st_brief_source_created",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.startup_profile} briefing with {self.provider}/{self.model_name}"


class StartupAdvisorBriefingJob(TimeStampedModel):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="startup_advisor_briefing_jobs",
    )
    startup_profile = models.ForeignKey(
        StartupProfile,
        on_delete=models.CASCADE,
        related_name="advisor_briefing_jobs",
    )
    source_snapshot = models.ForeignKey(
        StartupAdvisorSnapshot,
        on_delete=models.PROTECT,
        related_name="briefing_jobs",
    )
    briefing = models.OneToOneField(
        StartupAdvisorBriefing,
        on_delete=models.SET_NULL,
        related_name="generation_job",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED,
    )
    celery_task_id = models.CharField(
        max_length=255,
        blank=True,
    )
    error_code = models.CharField(
        max_length=64,
        blank=True,
    )
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["startup_profile", "-created_at"],
                name="st_brief_job_profile_created",
            ),
            models.Index(
                fields=["status", "-created_at"],
                name="st_brief_job_status_created",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["startup_profile"],
                condition=models.Q(
                    status__in=("queued", "running"),
                ),
                name="st_brief_one_active_job",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status="queued",
                        started_at__isnull=True,
                        completed_at__isnull=True,
                        briefing__isnull=True,
                    )
                    | models.Q(
                        status="running",
                        started_at__isnull=False,
                        completed_at__isnull=True,
                        briefing__isnull=True,
                    )
                    | models.Q(
                        status="succeeded",
                        started_at__isnull=False,
                        completed_at__isnull=False,
                        briefing__isnull=False,
                    )
                    | models.Q(
                        status="failed",
                        completed_at__isnull=False,
                        briefing__isnull=True,
                    )
                ),
                name="st_brief_job_state_match",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.startup_profile} advisor briefing job {self.status}"
