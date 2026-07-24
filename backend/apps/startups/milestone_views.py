"""
API views for the Execution & Milestones Engine.

Endpoints:
  GET  /api/v1/startup-milestones/
       List all milestones for the current profile (optional category/status query params).

  POST /api/v1/startup-milestones/
       Create a new milestone.

  GET/PUT/DELETE /api/v1/startup-milestones/{id}/
       Retrieve, update, or delete a milestone.

  POST /api/v1/startup-milestones/{id}/complete/
       Mark milestone as completed with evidence (checks dependency prerequisites).

  POST /api/v1/startup-milestones/{id}/log-update/
       Append a founder update log entry to the milestone.
"""
from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.startups.models import StartupMilestone, StartupProfile

from .milestone_serializers import (
    StartupMilestoneCompleteSerializer,
    StartupMilestoneLogUpdateSerializer,
    StartupMilestoneSerializer,
)
from .services.milestone_service import (
    MilestoneDependencyError,
    append_milestone_log,
    complete_milestone,
    detect_dependency_cycle,
)

logger = logging.getLogger(__name__)


def _get_current_profile(user) -> StartupProfile | None:
    return (
        StartupProfile.objects.filter(owner=user)
        .order_by("-created_at")
        .first()
    )


class StartupMilestoneListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = _get_current_profile(request.user)
        if profile is None:
            return Response({"milestones": []})

        qs = StartupMilestone.objects.filter(
            owner=request.user,
            startup_profile=profile,
        ).prefetch_related("dependencies")

        category = request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)

        status_param = request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        serializer = StartupMilestoneSerializer(qs, many=True)
        return Response({"milestones": serializer.data})

    def post(self, request):
        profile = _get_current_profile(request.user)
        if profile is None:
            return Response(
                {"detail": "No startup profile found. Complete your startup profile first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = StartupMilestoneSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        deps = serializer.validated_data.get("dependencies", [])
        dep_ids = [str(d.id) for d in deps]
        if detect_dependency_cycle(None, dep_ids):
            return Response(
                {"detail": "Circular milestone dependency detected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        milestone = serializer.save(owner=request.user, startup_profile=profile)
        out = StartupMilestoneSerializer(milestone)
        return Response(out.data, status=status.HTTP_201_CREATED)


class StartupMilestoneDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_milestone(self, request, milestone_id) -> StartupMilestone | None:
        profile = _get_current_profile(request.user)
        if profile is None:
            return None
        return StartupMilestone.objects.filter(
            id=milestone_id,
            owner=request.user,
            startup_profile=profile,
        ).first()

    def get(self, request, milestone_id):
        m = self._get_milestone(request, milestone_id)
        if not m:
            return Response(
                {"detail": "Milestone not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(StartupMilestoneSerializer(m).data)

    def put(self, request, milestone_id):
        m = self._get_milestone(request, milestone_id)
        if not m:
            return Response(
                {"detail": "Milestone not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = StartupMilestoneSerializer(m, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if "dependencies" in serializer.validated_data:
            deps = serializer.validated_data["dependencies"]
            dep_ids = [str(d.id) for d in deps]
            if detect_dependency_cycle(str(m.id), dep_ids):
                return Response(
                    {"detail": "Circular milestone dependency detected."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        updated = serializer.save()
        return Response(StartupMilestoneSerializer(updated).data)

    def delete(self, request, milestone_id):
        m = self._get_milestone(request, milestone_id)
        if not m:
            return Response(
                {"detail": "Milestone not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        m.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class StartupMilestoneCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, milestone_id):
        profile = _get_current_profile(request.user)
        if profile is None:
            return Response(
                {"detail": "No startup profile found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        m = StartupMilestone.objects.filter(
            id=milestone_id,
            owner=request.user,
            startup_profile=profile,
        ).first()

        if not m:
            return Response(
                {"detail": "Milestone not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = StartupMilestoneCompleteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        evidence = serializer.validated_data.get("evidence", {})
        force = serializer.validated_data.get("force", False)

        try:
            completed = complete_milestone(milestone=m, evidence=evidence, force=force)
        except MilestoneDependencyError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        out = StartupMilestoneSerializer(completed)
        return Response(out.data, status=status.HTTP_200_OK)


class StartupMilestoneLogUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, milestone_id):
        profile = _get_current_profile(request.user)
        if profile is None:
            return Response(
                {"detail": "No startup profile found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        m = StartupMilestone.objects.filter(
            id=milestone_id,
            owner=request.user,
            startup_profile=profile,
        ).first()

        if not m:
            return Response(
                {"detail": "Milestone not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = StartupMilestoneLogUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        note = serializer.validated_data["note"]
        updated = append_milestone_log(milestone=m, note=note, author="founder")

        out = StartupMilestoneSerializer(updated)
        return Response(out.data, status=status.HTTP_200_OK)
