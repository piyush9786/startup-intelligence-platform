from __future__ import annotations

from rest_framework import serializers

from .expert_marketplace_models import ConsultationRequest
from .workspace_models import ConsultantProfile


class ConsultationRequestSerializer(serializers.ModelSerializer):
    consultant_name = serializers.SerializerMethodField()
    founder_name = serializers.SerializerMethodField()
    startup_name = serializers.CharField(
        source="startup_profile.startup_name",
        read_only=True,
    )

    class Meta:
        model = ConsultationRequest
        fields = (
            "id",
            "startup_profile",
            "startup_name",
            "consultant",
            "consultant_name",
            "founder_name",
            "topic",
            "message",
            "preferred_date",
            "status",
            "consultant_response",
            "scheduled_for",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "startup_name",
            "consultant_name",
            "founder_name",
            "status",
            "consultant_response",
            "scheduled_for",
            "created_at",
            "updated_at",
        )

    def get_consultant_name(self, obj):
        user = obj.consultant.user
        return user.get_full_name().strip() or user.username

    def get_founder_name(self, obj):
        return obj.founder.get_full_name().strip() or obj.founder.username

    def validate_startup_profile(self, value):
        request = self.context.get("request")
        if request and value.owner_id != request.user.id:
            raise serializers.ValidationError(
                "The selected startup profile does not belong to you."
            )
        return value

    def validate_consultant(self, value):
        request = self.context.get("request")
        if value.verification_status != ConsultantProfile.VerificationStatus.VERIFIED:
            raise serializers.ValidationError(
                "Only verified consultants can receive consultation requests."
            )
        if not value.is_public:
            raise serializers.ValidationError(
                "This consultant is not currently listed in the marketplace."
            )
        if value.availability == ConsultantProfile.Availability.UNAVAILABLE:
            raise serializers.ValidationError(
                "This consultant is currently unavailable."
            )
        if request and value.user_id == request.user.id:
            raise serializers.ValidationError(
                "You cannot request a consultation from yourself."
            )
        return value

    def create(self, validated_data):
        request = self.context["request"]
        return ConsultationRequest.objects.create(
            founder=request.user,
            status=ConsultationRequest.Status.REQUESTED,
            **validated_data,
        )


class ConsultationResponseSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=(
            ConsultationRequest.Status.ACCEPTED,
            ConsultationRequest.Status.DECLINED,
            ConsultationRequest.Status.SCHEDULED,
            ConsultationRequest.Status.COMPLETED,
        )
    )
    consultant_response = serializers.CharField(
        allow_blank=True,
        required=False,
    )
    scheduled_for = serializers.DateTimeField(
        allow_null=True,
        required=False,
    )

    def validate(self, attrs):
        target_status = attrs["status"]
        if (
            target_status == ConsultationRequest.Status.SCHEDULED
            and attrs.get("scheduled_for") is None
        ):
            raise serializers.ValidationError(
                {"scheduled_for": "Choose a date and time for the consultation."}
            )
        if (
            target_status == ConsultationRequest.Status.DECLINED
            and not str(attrs.get("consultant_response") or "").strip()
        ):
            raise serializers.ValidationError(
                {"consultant_response": "Explain why the request was declined."}
            )
        return attrs
