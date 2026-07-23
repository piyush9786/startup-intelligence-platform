from django.utils import timezone
from rest_framework import serializers

from .models import EligibilityVerificationDecision


class EligibilityVerificationReviewerQueueQuerySerializer(
    serializers.Serializer,
):
    as_of_date = serializers.DateField(
        required=False,
        default=timezone.localdate,
    )


class EligibilityVerificationDecisionCreateSerializer(
    serializers.Serializer,
):
    outcome = serializers.ChoiceField(
        choices=EligibilityVerificationDecision.Outcome.choices,
    )
    verified_value = serializers.JSONField(
        required=False,
        allow_null=True,
    )
    review_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )
    valid_from = serializers.DateField(
        required=False,
        default=timezone.localdate,
    )
    expires_on = serializers.DateField(
        required=False,
        allow_null=True,
    )

    def validate(self, attrs):
        outcome = attrs["outcome"]
        verified_value = attrs.get("verified_value")

        if outcome == EligibilityVerificationDecision.Outcome.APPROVED and verified_value is None:
            raise serializers.ValidationError(
                {"verified_value": ("Approved decisions require a verified value.")}
            )

        if (
            outcome == EligibilityVerificationDecision.Outcome.REJECTED
            and verified_value is not None
        ):
            raise serializers.ValidationError(
                {"verified_value": ("Rejected decisions cannot include a verified value.")}
            )

        valid_from = attrs["valid_from"]
        expires_on = attrs.get("expires_on")

        if expires_on is not None and expires_on < valid_from:
            raise serializers.ValidationError(
                {"expires_on": ("Expiry cannot precede the valid-from date.")}
            )

        attrs["review_notes"] = attrs["review_notes"].strip()
        return attrs


class EligibilityVerificationDecisionSerializer(
    serializers.ModelSerializer,
):
    submission_id = serializers.UUIDField(read_only=True)
    reviewed_by_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = EligibilityVerificationDecision
        fields = (
            "id",
            "submission_id",
            "reviewed_by_id",
            "outcome",
            "verified_value",
            "review_notes",
            "valid_from",
            "expires_on",
            "created_at",
        )
        read_only_fields = fields
