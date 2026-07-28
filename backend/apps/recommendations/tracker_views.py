"""
DRF Views for SchemeApplicationTracker Kanban Board operations.
"""
from __future__ import annotations

from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.recommendations.models import SchemeApplicationTracker
from apps.recommendations.services.proposal_generator import generate_scheme_application_proposal


class SchemeApplicationTrackerSerializer(serializers.ModelSerializer):
    scheme_name = serializers.CharField(read_only=True)

    class Meta:
        model = SchemeApplicationTracker
        fields = [
            "id",
            "startup_profile",
            "scheme_version",
            "scheme_name",
            "stage",
            "submission_reference",
            "notes",
            "submitted_at",
            "application_data",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "owner",
            "stage",
            "submitted_at",
            "created_at",
            "updated_at",
        ]

    def validate_startup_profile(self, value):
        request = self.context.get("request")
        if (
            request
            and request.user
            and not request.user.is_staff
            and value.owner_id != request.user.id
        ):
            raise serializers.ValidationError(
                "The specified startup profile does not belong to you."
            )
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance is not None and "stage" in self.initial_data:
            raise serializers.ValidationError(
                {
                    "stage": (
                        "Application stages must be changed through the "
                        "application workflow transition endpoint."
                    )
                }
            )
        if self.instance is not None and "submitted_at" in self.initial_data:
            raise serializers.ValidationError(
                {
                    "submitted_at": (
                        "Submission timestamps are managed by workflow transitions."
                    )
                }
            )
        return attrs

    def to_representation(self, instance: SchemeApplicationTracker):
        ret = super().to_representation(instance)
        ret["scheme_name"] = instance.scheme_version.scheme.canonical_name
        ret["support_amount"] = (
            getattr(instance.scheme_version, "funding_amount", "")
            or "Published support"
        )
        return ret


class SchemeApplicationTrackerViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = SchemeApplicationTracker.objects.none()
    serializer_class = SchemeApplicationTrackerSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        return SchemeApplicationTracker.objects.filter(
            owner=self.request.user
        ).select_related("scheme_version__scheme", "startup_profile")

    def perform_create(self, serializer):
        serializer.save(
            owner=self.request.user,
            stage=SchemeApplicationTracker.Stage.DRAFT,
            submitted_at=None,
        )

    @action(detail=True, methods=["post"], url_path="generate-proposal")
    def generate_proposal(self, request, pk=None):
        tracker = self.get_object()
        proposal = generate_scheme_application_proposal(
            profile=tracker.startup_profile,
            scheme_version=tracker.scheme_version,
        )
        tracker.application_data["latest_proposal"] = proposal
        tracker.save(update_fields=["application_data"])
        return Response(proposal, status=status.HTTP_200_OK)
