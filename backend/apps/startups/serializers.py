from django.utils import timezone
from rest_framework import serializers

from .models import (
    StartupAdvisorSnapshot,
    StartupProfile,
    StartupReadinessActionPlan,
    StartupReadinessAssessment,
)


class StartupProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StartupProfile
        fields = "__all__"
        read_only_fields = (
            "id",
            "owner",
            "created_at",
            "updated_at",
        )


class StartupReadinessEvaluationRequestSerializer(serializers.Serializer):
    startup_profile_id = serializers.UUIDField()
    assessment_date = serializers.DateField(
        required=False,
        default=timezone.localdate,
    )
    profile = serializers.JSONField(
        required=False,
        write_only=True,
    )

    def validate(self, attrs):
        if "profile" in attrs:
            raise serializers.ValidationError(
                {"profile": ("Raw profile data is not accepted. Use startup_profile_id.")}
            )
        return attrs


class StartupReadinessRetrievalRequestSerializer(serializers.Serializer):
    startup_profile_id = serializers.UUIDField()


class StartupReadinessAssessmentSerializer(serializers.ModelSerializer):
    startup_profile_id = serializers.UUIDField(read_only=True)
    requested_by_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = StartupReadinessAssessment
        fields = (
            "id",
            "startup_profile_id",
            "requested_by_id",
            "assessment_date",
            "profile_snapshot",
            "status",
            "score",
            "critical_score",
            "recommended_score",
            "findings",
            "blocking_findings",
            "summary",
            "engine_version",
            "created_at",
        )
        read_only_fields = fields


class StartupReadinessActionPlanGenerationRequestSerializer(serializers.Serializer):
    readiness_assessment_id = serializers.UUIDField()
    findings = serializers.JSONField(required=False, write_only=True)
    profile = serializers.JSONField(required=False, write_only=True)
    assessment = serializers.JSONField(required=False, write_only=True)

    def validate(self, attrs):
        raw_fields = [name for name in ("findings", "profile", "assessment") if name in attrs]
        if raw_fields:
            raise serializers.ValidationError(
                {
                    name: ("Raw readiness data is not accepted. Use readiness_assessment_id.")
                    for name in raw_fields
                }
            )
        return attrs


class StartupReadinessActionPlanSerializer(serializers.ModelSerializer):
    startup_profile_id = serializers.UUIDField(read_only=True)
    source_assessment_id = serializers.UUIDField(read_only=True)
    requested_by_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = StartupReadinessActionPlan
        fields = (
            "id",
            "startup_profile_id",
            "source_assessment_id",
            "requested_by_id",
            "source_assessment_snapshot",
            "readiness_status",
            "has_actions",
            "blocker_count",
            "recommendation_count",
            "total_action_count",
            "next_action",
            "items",
            "source_engine_version",
            "planner_version",
            "created_at",
        )
        read_only_fields = fields


class StartupAdvisorSnapshotGenerationRequestSerializer(serializers.Serializer):
    startup_profile_id = serializers.UUIDField()
    profile = serializers.JSONField(required=False, write_only=True)
    readiness = serializers.JSONField(required=False, write_only=True)
    assessment = serializers.JSONField(required=False, write_only=True)
    action_plan = serializers.JSONField(required=False, write_only=True)
    recommendations = serializers.JSONField(
        required=False,
        write_only=True,
    )
    generation = serializers.JSONField(required=False, write_only=True)

    def validate(self, attrs):
        raw_fields = [
            name
            for name in (
                "profile",
                "readiness",
                "assessment",
                "action_plan",
                "recommendations",
                "generation",
            )
            if name in attrs
        ]
        if raw_fields:
            raise serializers.ValidationError(
                {
                    name: ("Raw advisor data is not accepted. Use startup_profile_id.")
                    for name in raw_fields
                }
            )
        return attrs


class StartupAdvisorSnapshotSerializer(serializers.ModelSerializer):
    startup_profile_id = serializers.UUIDField(read_only=True)
    requested_by_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )
    readiness_assessment_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )
    readiness_action_plan_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )
    recommendation_generation_run_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = StartupAdvisorSnapshot
        fields = (
            "id",
            "startup_profile_id",
            "requested_by_id",
            "readiness_assessment_id",
            "readiness_action_plan_id",
            "recommendation_generation_run_id",
            "has_readiness_assessment",
            "has_action_plan",
            "has_recommendation_generation",
            "profile_snapshot",
            "readiness_snapshot",
            "action_plan_snapshot",
            "recommendation_generation_snapshot",
            "recommendations_snapshot",
            "recommendation_count",
            "snapshot_version",
            "created_at",
        )
        read_only_fields = fields
