from django.utils import timezone
from rest_framework import serializers

from .models import EligibilityAssessment, Recommendation


class EligibilityRequestSerializer(serializers.Serializer):
    scheme_id = serializers.UUIDField()
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


class EligibilityAssessmentSerializer(serializers.ModelSerializer):
    startup_profile_id = serializers.UUIDField(
        read_only=True,
    )
    scheme_id = serializers.UUIDField(
        source="scheme_version.scheme_id",
        read_only=True,
    )
    scheme_version_id = serializers.UUIDField(
        read_only=True,
    )
    scheme_name = serializers.CharField(
        source="scheme_version.scheme.canonical_name",
        read_only=True,
    )

    class Meta:
        model = EligibilityAssessment
        fields = (
            "id",
            "startup_profile_id",
            "scheme_id",
            "scheme_version_id",
            "scheme_name",
            "assessment_date",
            "profile_snapshot",
            "result",
            "matched_rules",
            "failed_rules",
            "unknown_rules",
            "explanation",
            "engine_version",
            "created_at",
        )
        read_only_fields = fields


class RecommendationGenerationRequestSerializer(serializers.Serializer):
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


class RecommendationSerializer(serializers.ModelSerializer):
    startup_profile_id = serializers.UUIDField(
        read_only=True,
    )
    assessment_id = serializers.UUIDField(
        read_only=True,
    )
    assessment_result = serializers.CharField(
        source="assessment.result",
        read_only=True,
    )
    scheme_id = serializers.UUIDField(
        source="scheme_version.scheme_id",
        read_only=True,
    )
    scheme_version_id = serializers.UUIDField(
        read_only=True,
    )
    scheme_name = serializers.CharField(
        source="scheme_version.scheme.canonical_name",
        read_only=True,
    )
    application_status = serializers.CharField(
        source="scheme_version.application_status",
        read_only=True,
    )

    class Meta:
        model = Recommendation
        fields = (
            "id",
            "generation_id",
            "ranking_version",
            "startup_profile_id",
            "assessment_id",
            "assessment_result",
            "scheme_id",
            "scheme_version_id",
            "scheme_name",
            "application_status",
            "rank",
            "score",
            "score_breakdown",
            "evidence_snapshot",
            "created_at",
        )
        read_only_fields = fields
