from django.utils import timezone
from rest_framework import serializers

from .models import EligibilityAssessment


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
