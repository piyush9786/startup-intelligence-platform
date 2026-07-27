"""REST API Views for research application."""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.startups.models import StartupProfile

from .models import ResearchRequest, StartupResearchReport
from .serializers import (
    ResearchRequestCreateSerializer,
    ResearchRequestDetailSerializer,
    StartupResearchReportSerializer,
)
from .tasks import generate_research_report_task


def _resolve_profile(user, profile_id):
    if getattr(user, "is_staff", False):
        return get_object_or_404(StartupProfile, pk=profile_id)
    return get_object_or_404(StartupProfile, pk=profile_id, owner=user)


class ResearchRequestCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ResearchRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = _resolve_profile(
            request.user,
            serializer.validated_data["startup_profile_id"],
        )

        req_obj = ResearchRequest.objects.create(
            startup_profile=profile,
            requested_by=request.user,
            question=serializer.validated_data["question"],
        )

        try:
            async_res = generate_research_report_task.delay(str(req_obj.id))
            req_obj.celery_task_id = str(async_res.id or "")
            req_obj.save(update_fields=["celery_task_id", "updated_at"])
        except Exception as exc:
            req_obj.status = ResearchRequest.Status.FAILED
            req_obj.error_code = "dispatch_failed"
            req_obj.error_message = f"Failed to dispatch research worker: {exc}"
            req_obj.save(update_fields=["status", "error_code", "error_message", "updated_at"])

        return Response(
            {
                "job": ResearchRequestDetailSerializer(req_obj).data,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class ResearchRequestDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if getattr(request.user, "is_staff", False):
            req_obj = get_object_or_404(ResearchRequest, pk=pk)
        else:
            req_obj = get_object_or_404(ResearchRequest, pk=pk, requested_by=request.user)

        return Response(ResearchRequestDetailSerializer(req_obj).data)


class StartupResearchReportListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile_id = request.query_params.get("startup_profile_id")
        if not profile_id:
            return Response(
                {"detail": "startup_profile_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile = _resolve_profile(request.user, profile_id)
        reports = StartupResearchReport.objects.filter(startup_profile=profile)
        return Response(StartupResearchReportSerializer(reports, many=True).data)


class StartupResearchReportDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if getattr(request.user, "is_staff", False):
            report = get_object_or_404(StartupResearchReport, pk=pk)
        else:
            report = get_object_or_404(
                StartupResearchReport,
                pk=pk,
                startup_profile__owner=request.user,
            )

        return Response(StartupResearchReportSerializer(report).data)
