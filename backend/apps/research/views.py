"""REST API Views for research application."""
from __future__ import annotations

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.recommendations.services import (
    RecommendationSetIntegrityError,
)
from apps.startups.models import (
    StartupAdvisorBriefingJob,
    StartupProfile,
)
from apps.startups.services import (
    create_startup_advisor_snapshot,
)

from .models import (
    DecisionRecommendation,
    ResearchInsight,
    ResearchRequest,
    StartupResearchReport,
)
from .serializers import (
    DecisionRecommendationSerializer,
    ResearchInsightSerializer,
    ResearchRequestCreateSerializer,
    ResearchRequestDetailSerializer,
    StartupResearchReportSerializer,
)
from .tasks import generate_research_report_task
from .throttles import ResearchDailyThrottle, ResearchHourlyThrottle


def _resolve_profile(user, profile_id):
    if getattr(user, "is_staff", False):
        return get_object_or_404(StartupProfile, pk=profile_id)
    return get_object_or_404(StartupProfile, pk=profile_id, owner=user)


class ResearchRequestCreateView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ResearchHourlyThrottle, ResearchDailyThrottle]

    def post(self, request):
        serializer = ResearchRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = _resolve_profile(
            request.user,
            serializer.validated_data["startup_profile_id"],
        )
        generate_founder_advice = serializer.validated_data[
            "generate_founder_advice"
        ]

        active_job = ResearchRequest.objects.filter(
            startup_profile=profile,
            status__in=[ResearchRequest.Status.QUEUED, ResearchRequest.Status.RUNNING],
        ).first()

        if active_job:
            return Response(
                {
                    "detail": "A research job is already in progress for this startup profile.",
                    "job": ResearchRequestDetailSerializer(active_job).data,
                },
                status=status.HTTP_409_CONFLICT,
            )

        if generate_founder_advice:
            active_advisor_job = (
                StartupAdvisorBriefingJob.objects.filter(
                    startup_profile=profile,
                    status__in=[
                        StartupAdvisorBriefingJob.Status.QUEUED,
                        StartupAdvisorBriefingJob.Status.RUNNING,
                    ],
                )
                .order_by("-created_at", "-id")
                .first()
            )

            if active_advisor_job is not None:
                return Response(
                    {
                        "detail": (
                            "An advisor generation job is already "
                            "in progress for this startup profile."
                        ),
                        "advisor_job_id": str(
                            active_advisor_job.id
                        ),
                        "advisor_job_status": (
                            active_advisor_job.status
                        ),
                    },
                    status=status.HTTP_409_CONFLICT,
                )

        try:
            with transaction.atomic():
                advisor_snapshot = None
                workflow_type = (
                    ResearchRequest.WorkflowType.STANDALONE
                )

                if generate_founder_advice:
                    advisor_snapshot = (
                        create_startup_advisor_snapshot(
                            startup_profile=profile,
                            requested_by=request.user,
                        )
                    )
                    workflow_type = (
                        ResearchRequest.WorkflowType
                        .RESEARCH_FIRST_INTELLIGENCE
                    )

                req_obj = ResearchRequest.objects.create(
                    startup_profile=profile,
                    requested_by=request.user,
                    advisor_snapshot=advisor_snapshot,
                    workflow_type=workflow_type,
                    question=serializer.validated_data[
                        "question"
                    ],
                )
        except RecommendationSetIntegrityError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )
        except IntegrityError:
            active_job = ResearchRequest.objects.filter(
                startup_profile=profile,
                status__in=[
                    ResearchRequest.Status.QUEUED,
                    ResearchRequest.Status.RUNNING,
                ],
            ).first()
            return Response(
                {
                    "detail": (
                        "A research job is already in progress "
                        "for this startup profile."
                    ),
                    "job": (
                        ResearchRequestDetailSerializer(active_job).data
                        if active_job
                        else None
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )

        try:
            async_res = generate_research_report_task.delay(str(req_obj.id))
            req_obj.celery_task_id = str(async_res.id or "")
            req_obj.save(update_fields=["celery_task_id", "updated_at"])
        except Exception as exc:
            req_obj.status = ResearchRequest.Status.FAILED
            req_obj.completed_at = timezone.now()
            req_obj.error_code = "dispatch_failed"
            req_obj.error_message = (
                f"Failed to dispatch research worker: {exc}"
            )
            req_obj.save(
                update_fields=[
                    "status",
                    "completed_at",
                    "error_code",
                    "error_message",
                    "updated_at",
                ]
            )
            return Response(
                {
                    "detail": (
                        "The research worker is currently unavailable."
                    ),
                    "job": ResearchRequestDetailSerializer(req_obj).data,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "workflow_type": req_obj.workflow_type,
                "advisor_snapshot_id": (
                    str(req_obj.advisor_snapshot_id)
                    if req_obj.advisor_snapshot_id
                    else None
                ),
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


class CurrentResearchRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile_id = request.query_params.get("startup_profile_id")
        if not profile_id:
            return Response(
                {"detail": "startup_profile_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile = _resolve_profile(request.user, profile_id)
        queryset = ResearchRequest.objects.filter(
            startup_profile=profile,
        ).select_related(
            "generated_report",
            "source_advisor_briefing",
        )
        current = (
            queryset.filter(
                status__in=[
                    ResearchRequest.Status.QUEUED,
                    ResearchRequest.Status.RUNNING,
                ]
            )
            .order_by("-created_at", "-id")
            .first()
            or queryset.order_by("-created_at", "-id").first()
        )

        return Response(
            {
                "job": (
                    ResearchRequestDetailSerializer(current).data
                    if current is not None
                    else None
                )
            }
        )


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


class StartupResearchIntelligenceView(APIView):
    """Read reusable research memory for one founder-owned startup."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile_id = request.query_params.get("startup_profile_id")
        if not profile_id:
            return Response(
                {"detail": "startup_profile_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile = _resolve_profile(request.user, profile_id)
        insights = ResearchInsight.objects.filter(
            startup_profile=profile,
        ).order_by("-last_verified_at", "-created_at")

        insight_type = request.query_params.get("type")
        valid_types = {value for value, _label in ResearchInsight.InsightType.choices}
        if insight_type in valid_types:
            insights = insights.filter(insight_type=insight_type)

        decisions = DecisionRecommendation.objects.filter(
            startup_profile=profile,
        ).order_by("-generated_at", "-created_at")

        return Response({
            "startup_profile_id": str(profile.id),
            "insights": ResearchInsightSerializer(insights[:100], many=True).data,
            "decisions": DecisionRecommendationSerializer(decisions[:20], many=True).data,
        })
