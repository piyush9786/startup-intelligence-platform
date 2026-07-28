from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from django.conf import settings
from rest_framework import serializers

from apps.sources.services.storage import (
    delete_object,
    upload_stream,
)

from .workspace_models import (
    ApplicationStageEvent,
    ApplicationTask,
    ComplianceRecord,
    ConsultantProfile,
    FounderVaultDocument,
)


def _validate_owned_startup(request, startup_profile):
    if request and startup_profile.owner_id != request.user.id:
        raise serializers.ValidationError(
            "The selected startup profile does not belong to you."
        )
    return startup_profile


class ComplianceRecordSerializer(serializers.ModelSerializer):
    effective_status = serializers.CharField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)

    class Meta:
        model = ComplianceRecord
        fields = (
            "id",
            "startup_profile",
            "compliance_type",
            "title",
            "registration_number",
            "issuing_authority",
            "status",
            "effective_status",
            "issued_on",
            "expires_on",
            "days_until_expiry",
            "renewal_reminder_days",
            "notes",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "effective_status",
            "days_until_expiry",
            "created_at",
            "updated_at",
        )

    def validate_startup_profile(self, value):
        return _validate_owned_startup(self.context.get("request"), value)


class FounderVaultDocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, required=False)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = FounderVaultDocument
        fields = (
            "id",
            "startup_profile",
            "title",
            "category",
            "file",
            "original_filename",
            "mime_type",
            "size_bytes",
            "content_hash",
            "expires_on",
            "tags",
            "is_archived",
            "metadata",
            "download_url",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "original_filename",
            "mime_type",
            "size_bytes",
            "content_hash",
            "download_url",
            "created_at",
            "updated_at",
        )

    def get_download_url(self, obj):
        request = self.context.get("request")
        if request is None:
            return None
        return request.build_absolute_uri(
            f"/api/v1/founder-vault-documents/{obj.id}/download/"
        )

    def validate_startup_profile(self, value):
        return _validate_owned_startup(self.context.get("request"), value)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        uploaded = attrs.get("file")
        if self.instance is None and uploaded is None:
            raise serializers.ValidationError(
                {"file": "A document file is required."}
            )
        if uploaded is not None:
            max_bytes = int(
                getattr(settings, "FOUNDER_VAULT_MAX_BYTES", 25 * 1024 * 1024)
            )
            if uploaded.size > max_bytes:
                raise serializers.ValidationError(
                    {"file": f"The file exceeds the {max_bytes}-byte limit."}
                )
        return attrs

    def create(self, validated_data):
        uploaded = validated_data.pop("file")
        request = self.context["request"]
        digest = hashlib.sha256()
        for chunk in uploaded.chunks():
            digest.update(chunk)
        uploaded.seek(0)

        safe_name = Path(uploaded.name).name or "document"
        object_key = (
            f"founder-vault/{request.user.id}/"
            f"{uuid.uuid4().hex}/{safe_name}"
        )
        bucket_name = getattr(
            settings,
            "MINIO_BUCKET_STARTUP_EVIDENCE",
            "startup-eligibility-evidence",
        )
        upload_stream(
            object_key=object_key,
            stream=uploaded,
            length=uploaded.size,
            content_type=(
                getattr(uploaded, "content_type", "")
                or "application/octet-stream"
            ),
            bucket_name=bucket_name,
        )

        try:
            return FounderVaultDocument.objects.create(
                owner=request.user,
                original_filename=safe_name,
                mime_type=(
                    getattr(uploaded, "content_type", "")
                    or "application/octet-stream"
                ),
                size_bytes=uploaded.size,
                content_hash=digest.hexdigest(),
                storage_key=object_key,
                bucket_name=bucket_name,
                **validated_data,
            )
        except Exception:  # noqa: BLE001
            delete_object(object_key, bucket_name=bucket_name)
            raise


class ConsultantProfileSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    username = serializers.CharField(source="user.username", read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = ConsultantProfile
        fields = (
            "id",
            "username",
            "display_name",
            "headline",
            "bio",
            "expertise",
            "languages",
            "states_served",
            "industries",
            "hourly_rate",
            "availability",
            "verification_status",
            "is_public",
            "years_experience",
            "sessions_completed",
            "average_rating",
            "is_owner",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "verification_status",
            "sessions_completed",
            "average_rating",
            "is_owner",
            "created_at",
            "updated_at",
        )

    def get_display_name(self, obj):
        full_name = obj.user.get_full_name().strip()
        return full_name or obj.user.username

    def get_is_owner(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.id == obj.user_id)


class ApplicationTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationTask
        fields = (
            "id",
            "application",
            "title",
            "status",
            "due_on",
            "completed_at",
            "notes",
            "sort_order",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "completed_at",
            "created_at",
            "updated_at",
        )

    def validate_application(self, value):
        request = self.context.get("request")
        if request and value.owner_id != request.user.id:
            raise serializers.ValidationError(
                "The selected application does not belong to you."
            )
        return value


class ApplicationStageEventSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationStageEvent
        fields = (
            "id",
            "application",
            "from_stage",
            "to_stage",
            "note",
            "created_by_name",
            "occurred_at",
            "created_at",
        )
        read_only_fields = fields

    def get_created_by_name(self, obj):
        if obj.created_by is None:
            return "System"
        return obj.created_by.get_full_name().strip() or obj.created_by.username
