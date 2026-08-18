"""Research models for live hybrid search and grounded report generation."""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.startups.models import StartupProfile


class ResearchRequest(TimeStampedModel):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        PARTIAL = "partial", "Partial results"
        FAILED = "failed", "Failed"

    class WorkflowType(models.TextChoices):
        STANDALONE = (
            "standalone",
            "Standalone research",
        )
        ADVISOR_FOLLOWUP = (
            "advisor_followup",
            "Advisor follow-up research",
        )
        RESEARCH_FIRST_INTELLIGENCE = (
            "research_first_intelligence",
            "Research-first founder intelligence",
        )

    startup_profile = models.ForeignKey(
        StartupProfile,
        on_delete=models.CASCADE,
        related_name="research_requests",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="research_requests",
    )
    workflow_type = models.CharField(
        max_length=40,
        choices=WorkflowType.choices,
        default=WorkflowType.STANDALONE,
        db_index=True,
    )
    advisor_snapshot = models.ForeignKey(
        "startups.StartupAdvisorSnapshot",
        on_delete=models.PROTECT,
        related_name="research_first_requests",
        null=True,
        blank=True,
    )
    source_advisor_job = models.OneToOneField(
        "startups.StartupAdvisorBriefingJob",
        on_delete=models.SET_NULL,
        related_name="automatic_research_request",
        null=True,
        blank=True,
    )
    source_advisor_briefing = models.OneToOneField(
        "startups.StartupAdvisorBriefing",
        on_delete=models.SET_NULL,
        related_name="automatic_research_request",
        null=True,
        blank=True,
    )
    question = models.TextField()
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.QUEUED,
        db_index=True,
    )
    requires_live_search = models.BooleanField(default=False)
    search_decision_reason = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=64, blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    celery_task_id = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["startup_profile"],
                condition=Q(status__in=["queued", "running"]),
                name="research_one_active_request_per_profile",
            ),
        ]

    def __str__(self) -> str:
        return f"ResearchRequest({self.id}, status={self.status})"


class ResearchSearchQuery(TimeStampedModel):
    class Status(models.TextChoices):
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    research_request = models.ForeignKey(
        ResearchRequest,
        on_delete=models.CASCADE,
        related_name="search_queries",
    )
    query = models.TextField()
    provider = models.CharField(max_length=64, default="tavily")
    result_count = models.IntegerField(default=0)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.SUCCEEDED,
    )
    error_message = models.TextField(blank=True, default="")
    executed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["research_request", "query", "provider"],
                name="research_unique_search_query",
            ),
        ]

    def __str__(self) -> str:
        return f"ResearchSearchQuery({self.query[:30]}, count={self.result_count})"


class ResearchEvidence(TimeStampedModel):
    class VerificationStatus(models.TextChoices):
        VERIFIED_INTERNAL = "verified_internal", "Verified Internal"
        OFFICIAL_LIVE = "official_live", "Official Live"
        REPUTABLE_SECONDARY = "reputable_secondary", "Reputable Secondary"
        UNVERIFIED_LIVE = "unverified_live", "Unverified Live"
        REJECTED = "rejected", "Rejected"

    research_request = models.ForeignKey(
        ResearchRequest,
        on_delete=models.CASCADE,
        related_name="evidence_items",
    )
    title = models.TextField()
    url = models.URLField(max_length=2000)
    publisher = models.CharField(max_length=255, blank=True, default="")
    published_at = models.CharField(max_length=64, blank=True, default="")
    retrieved_at = models.DateTimeField(default=timezone.now)
    source_type = models.CharField(max_length=64, default="unverified_live")
    content_excerpt = models.TextField()
    content_hash = models.CharField(max_length=64, db_index=True)
    confidence_score = models.FloatField(default=0.5)
    verification_status = models.CharField(
        max_length=64,
        choices=VerificationStatus.choices,
        default=VerificationStatus.UNVERIFIED_LIVE,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["research_request", "content_hash"],
                name="research_unique_evidence_per_request",
            ),
        ]

    def __str__(self) -> str:
        return f"ResearchEvidence({self.title[:30]}, status={self.verification_status})"


class StartupResearchReport(TimeStampedModel):
    startup_profile = models.ForeignKey(
        StartupProfile,
        on_delete=models.CASCADE,
        related_name="research_reports",
    )
    research_request = models.OneToOneField(
        ResearchRequest,
        on_delete=models.CASCADE,
        related_name="generated_report",
    )
    local_data_cutoff = models.DateTimeField(default=timezone.now)
    live_search_date = models.DateTimeField(null=True, blank=True)
    model_name = models.CharField(max_length=128)
    algorithm_version = models.CharField(max_length=64, default="v1.0")
    report = models.JSONField(default=dict)
    source_snapshot = models.JSONField(default=dict)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"StartupResearchReport({self.id}, profile={self.startup_profile_id})"

# ADVISER_DECISION_INTELLIGENCE_V1
class ResearchInsight(TimeStampedModel):
    """Reusable structured intelligence extracted from a grounded report."""

    class InsightType(models.TextChoices):
        BENEFIT = "benefit", "Benefit"
        COMPETITOR = "competitor", "Competitor"
        SUCCESS_CASE = "success_case", "Success case"
        FAILURE_CASE = "failure_case", "Failure case"
        CHALLENGE = "challenge", "Challenge"
        OPPORTUNITY = "opportunity", "Opportunity"
        RISK = "risk", "Risk"
        MARKET_GAP = "market_gap", "Market gap"
        LESSON = "lesson", "Lesson"

    class FreshnessStatus(models.TextChoices):
        CURRENT = "current", "Current"
        AGING = "aging", "Aging"
        STALE = "stale", "Stale"
        REVERIFY = "reverify", "Reverify"

    startup_profile = models.ForeignKey(
        StartupProfile,
        on_delete=models.CASCADE,
        related_name="research_insights",
    )
    source_report = models.ForeignKey(
        StartupResearchReport,
        on_delete=models.CASCADE,
        related_name="structured_insights",
    )
    insight_type = models.CharField(max_length=32, choices=InsightType.choices)
    title = models.CharField(max_length=255)
    summary = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    evidence_urls = models.JSONField(default=list, blank=True)
    confidence_score = models.FloatField(default=0.5)
    freshness_status = models.CharField(
        max_length=16,
        choices=FreshnessStatus.choices,
        default=FreshnessStatus.CURRENT,
    )
    last_verified_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-last_verified_at", "-created_at"]
        indexes = [
            models.Index(
                fields=["startup_profile", "insight_type", "last_verified_at"],
                name="research_insight_profile_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["source_report", "insight_type", "title"],
                name="research_unique_report_insight",
            ),
            models.CheckConstraint(
                condition=(
                    Q(confidence_score__gte=0.0)
                    & Q(confidence_score__lte=1.0)
                ),
                name="research_insight_conf_rng",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.insight_type}: {self.title}"


class DecisionRecommendation(TimeStampedModel):
    """Persisted evidence-backed recommendation for future review."""

    startup_profile = models.ForeignKey(
        StartupProfile,
        on_delete=models.CASCADE,
        related_name="decision_recommendations",
    )
    source_report = models.OneToOneField(
        StartupResearchReport,
        on_delete=models.CASCADE,
        related_name="decision_recommendation",
    )
    question = models.TextField()
    recommended_direction = models.TextField()
    rationale = models.TextField(blank=True, default="")
    alternatives = models.JSONField(default=list, blank=True)
    decision_matrix = models.JSONField(default=list, blank=True)
    conditions_to_reconsider = models.JSONField(default=list, blank=True)
    immediate_actions = models.JSONField(default=list, blank=True)
    action_plan = models.JSONField(default=dict, blank=True)
    confidence_score = models.FloatField(default=0.5)
    generated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-generated_at", "-created_at"]
        indexes = [
            models.Index(
                fields=["startup_profile", "generated_at"],
                name="research_decision_profile_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(confidence_score__gte=0.0)
                    & Q(confidence_score__lte=1.0)
                ),
                name="research_decision_conf_rng",
            ),
        ]

    def __str__(self) -> str:
        return f"DecisionRecommendation({self.startup_profile_id}, {self.generated_at})"
