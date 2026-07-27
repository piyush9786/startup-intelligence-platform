from pathlib import Path

from django.conf import settings
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

    _ALLOWED_TYPES = {
        ".pdf": ("application/pdf", lambda header: header.startswith(b"%PDF-")),
        ".png": ("image/png", lambda header: header.startswith(b"\x89PNG\r\n\x1a\n")),
        ".jpg": ("image/jpeg", lambda header: header.startswith(b"\xff\xd8\xff")),
        ".jpeg": ("image/jpeg", lambda header: header.startswith(b"\xff\xd8\xff")),
    }

    def validate_file(self, uploaded_file):
        if uploaded_file.size > settings.ELIGIBILITY_EVIDENCE_MAX_BYTES:
            max_mib = settings.ELIGIBILITY_EVIDENCE_MAX_BYTES / (1024 * 1024)
            raise serializers.ValidationError(
                f"Evidence files must be no larger than {max_mib:g} MiB."
            )

        extension = Path(uploaded_file.name).suffix.casefold()
        allowed = self._ALLOWED_TYPES.get(extension)
        if allowed is None:
            raise serializers.ValidationError(
                "Evidence must be a PDF, PNG, or JPEG file."
            )

        expected_mime_type, signature_matches = allowed
        header = uploaded_file.read(16)
        uploaded_file.seek(0)
        if not signature_matches(header):
            raise serializers.ValidationError(
                "The file contents do not match the selected file type."
            )
        if uploaded_file.content_type != expected_mime_type:
            raise serializers.ValidationError(
                f"The declared content type must be {expected_mime_type}."
            )
        return uploaded_file


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
