"""Serializers for research app."""
from __future__ import annotations

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from .models import (
    DecisionRecommendation,
    ResearchEvidence,
    ResearchInsight,
    ResearchRequest,
    ResearchSearchQuery,
    StartupResearchReport,
)


class ResearchEvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchEvidence
        fields = [
            "id",
            "title",
            "url",
            "publisher",
            "published_at",
            "source_type",
            "content_excerpt",
            "confidence_score",
            "verification_status",
            "retrieved_at",
        ]


class ResearchSearchQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchSearchQuery
        fields = [
            "id",
            "query",
            "provider",
            "result_count",
            "status",
            "error_message",
            "executed_at",
        ]


class ResearchInsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchInsight
        fields = [
            "id", "source_report", "insight_type", "title", "summary",
            "details", "evidence_urls", "confidence_score",
            "freshness_status", "last_verified_at", "created_at",
        ]


class DecisionRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DecisionRecommendation
        fields = [
            "id", "source_report", "question", "recommended_direction",
            "rationale", "alternatives", "decision_matrix",
            "conditions_to_reconsider", "immediate_actions", "action_plan",
            "confidence_score", "generated_at", "created_at",
        ]


class StartupResearchReportSerializer(serializers.ModelSerializer):
    structured_insights = ResearchInsightSerializer(many=True, read_only=True)
    decision_recommendation = DecisionRecommendationSerializer(
        read_only=True, allow_null=True,
    )

    class Meta:
        model = StartupResearchReport
        fields = [
            "id",
            "startup_profile",
            "research_request",
            "local_data_cutoff",
            "live_search_date",
            "model_name",
            "algorithm_version",
            "report",
            "structured_insights",
            "decision_recommendation",
            "created_at",
        ]


class ResearchRequestDetailSerializer(serializers.ModelSerializer):
    search_queries = ResearchSearchQuerySerializer(many=True, read_only=True)
    evidence_items = ResearchEvidenceSerializer(many=True, read_only=True)
    generated_report = StartupResearchReportSerializer(read_only=True)
    advisor_job = serializers.SerializerMethodField()

    def get_advisor_job(self, obj):
        try:
            report = obj.generated_report
        except ObjectDoesNotExist:
            return None

        try:
            job = report.advisor_generation_job
        except ObjectDoesNotExist:
            return None

        return {
            "id": str(job.id),
            "startup_profile_id": str(job.startup_profile_id),
            "source_snapshot_id": str(job.source_snapshot_id),
            "source_research_report_id": str(
                job.source_research_report_id
            ),
            "briefing_id": (
                str(job.briefing_id)
                if job.briefing_id
                else None
            ),
            "status": job.status,
            "error_code": job.error_code,
            "error_message": job.error_message,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "is_terminal": job.status in (
                "succeeded",
                "failed",
            ),
        }

    class Meta:
        model = ResearchRequest
        fields = [
            "id",
            "startup_profile",
            "requested_by",
            "workflow_type",
            "advisor_snapshot",
            "source_advisor_job",
            "source_advisor_briefing",
            "question",
            "status",
            "requires_live_search",
            "search_decision_reason",
            "started_at",
            "completed_at",
            "error_code",
            "error_message",
            "search_queries",
            "evidence_items",
            "generated_report",
            "advisor_job",
            "created_at",
        ]


class ResearchRequestCreateSerializer(serializers.Serializer):
    startup_profile_id = serializers.UUIDField()
    question = serializers.CharField(min_length=5, max_length=2000)
    generate_founder_advice = serializers.BooleanField(
        required=False,
        default=False,
    )
