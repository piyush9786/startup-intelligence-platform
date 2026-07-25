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
            "stage",
            "submission_reference",
            "notes",
            "submitted_at",
            "application_data",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner", "created_at", "updated_at"]

    def to_representation(self, instance: SchemeApplicationTracker):
        ret = super().to_representation(instance)
        ret["scheme_name"] = instance.scheme_version.scheme.canonical_name
        ret["support_amount"] = instance.scheme_version.funding_amount
        return ret


class SchemeApplicationTrackerViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SchemeApplicationTrackerSerializer

    def get_queryset(self):
        return SchemeApplicationTracker.objects.filter(
            owner=self.request.user
        ).select_related("scheme_version__scheme", "startup_profile")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

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
