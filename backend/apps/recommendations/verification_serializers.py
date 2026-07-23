from django.utils import timezone
from rest_framework import serializers

from .models import (
    EligibilityVerificationEvidence,
    EligibilityVerificationSubmission,
)


class EligibilityVerificationGateQuerySerializer(
    serializers.Serializer,
):
    scheme_id = serializers.UUIDField()
    startup_profile_id = serializers.UUIDField()
    as_of_date = serializers.DateField(
        required=False,
        default=timezone.localdate,
    )


class EligibilityVerificationSubmissionCreateSerializer(
    serializers.Serializer,
):
    scheme_id = serializers.UUIDField()
    startup_profile_id = serializers.UUIDField()
    eligibility_rule_id = serializers.UUIDField()
    claim_value = serializers.JSONField(
        required=False,
        allow_null=True,
    )
    claim_text = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    def validate(self, attrs):
        claim_value = attrs.get("claim_value")
        claim_text = attrs.get("claim_text", "").strip()

        if claim_value is None and not claim_text:
            raise serializers.ValidationError(
                {"claim": ("Provide a structured claim value or explanatory claim text.")}
            )

        attrs["claim_text"] = claim_text
        return attrs


class EligibilityVerificationEvidenceUploadSerializer(
    serializers.Serializer,
):
    file = serializers.FileField()


class EligibilityVerificationEvidenceSerializer(
    serializers.ModelSerializer,
):
    uploaded_by_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = EligibilityVerificationEvidence
        fields = (
            "id",
            "uploaded_by_id",
            "filename",
            "mime_type",
            "size_bytes",
            "content_hash",
            "created_at",
        )
        read_only_fields = fields


class EligibilityVerificationSubmissionSerializer(
    serializers.ModelSerializer,
):
    startup_profile_id = serializers.UUIDField(read_only=True)
    scheme_version_id = serializers.UUIDField(read_only=True)
    eligibility_rule_id = serializers.UUIDField(read_only=True)
    submitted_by_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )
    supersedes_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )
    evidence = EligibilityVerificationEvidenceSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = EligibilityVerificationSubmission
        fields = (
            "id",
            "startup_profile_id",
            "scheme_version_id",
            "eligibility_rule_id",
            "submitted_by_id",
            "supersedes_id",
            "is_current",
            "claim_value",
            "claim_text",
            "evidence",
            "created_at",
        )
        read_only_fields = fields
