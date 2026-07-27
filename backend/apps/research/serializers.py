"""Serializers for research app."""
from __future__ import annotations

from rest_framework import serializers

from .models import (
    ResearchEvidence,
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
            "executed_at",
        ]


class StartupResearchReportSerializer(serializers.ModelSerializer):
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
            "created_at",
        ]


class ResearchRequestDetailSerializer(serializers.ModelSerializer):
    search_queries = ResearchSearchQuerySerializer(many=True, read_only=True)
    evidence_items = ResearchEvidenceSerializer(many=True, read_only=True)
    generated_report = StartupResearchReportSerializer(read_only=True)

    class Meta:
        model = ResearchRequest
        fields = [
            "id",
            "startup_profile",
            "requested_by",
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
            "created_at",
        ]


class ResearchRequestCreateSerializer(serializers.Serializer):
    startup_profile_id = serializers.UUIDField()
    question = serializers.CharField(min_length=5, max_length=2000)
