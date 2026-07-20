from django.utils import timezone
from rest_framework import serializers

from .models import (
    StartupProfile,
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


class StartupReadinessAssessmentSerializer(serializers.ModelSerializer):
    startup_profile_id = serializers.UUIDField(
        read_only=True,
    )
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
