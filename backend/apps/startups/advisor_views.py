from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.recommendations.serializers import (
    RecommendationGenerationRunDetailSerializer,
    RecommendationSerializer,
)
from apps.recommendations.services import (
    RecommendationSetIntegrityError,
    get_current_recommendation_set,
)

from .models import (
    StartupAdvisorBriefing,
    StartupAdvisorBriefingJob,
    StartupAdvisorSnapshot,
    StartupProfile,
    StartupReadinessActionPlan,
    StartupReadinessAssessment,
)
from .serializers import (
    StartupAdvisorBriefingGenerationRequestSerializer,
    StartupAdvisorBriefingJobSerializer,
    StartupAdvisorBriefingSerializer,
    StartupAdvisorSnapshotGenerationRequestSerializer,
    StartupAdvisorSnapshotSerializer,
    StartupReadinessActionPlanSerializer,
    StartupReadinessAssessmentSerializer,
    StartupReadinessRetrievalRequestSerializer,
)
from .services import (
    create_startup_advisor_snapshot,
)
from .services.advisor_briefing_jobs import (
    AdvisorBriefingJobDispatchError,
    queue_startup_advisor_briefing_job,
    reconcile_startup_advisor_briefing_job,
)


def _visible_profiles(user):
    return StartupProfile.objects.filter(owner=user)


def _visible_advisor_briefings(user):
    return StartupAdvisorBriefing.objects.filter(
        startup_profile__owner=user,
    )


def _visible_advisor_briefing_jobs(user):
    return StartupAdvisorBriefingJob.objects.filter(
        startup_profile__owner=user,
    )


def _visible_advisor_snapshots(user):
    return StartupAdvisorSnapshot.objects.filter(
        startup_profile__owner=user,
    )


def _resolve_target_profile(user, profile_id):
    if getattr(user, "is_staff", False):
        return get_object_or_404(StartupProfile.objects.all(), pk=profile_id)
    return get_object_or_404(StartupProfile.objects.filter(owner=user), pk=profile_id)


def _resolve_target_snapshot(user, snapshot_id):
    if getattr(user, "is_staff", False):
        return get_object_or_404(StartupAdvisorSnapshot.objects.all(), pk=snapshot_id)
    return get_object_or_404(
        StartupAdvisorSnapshot.objects.filter(startup_profile__owner=user),
        pk=snapshot_id,
    )


def _resolve_target_job(user, job_id):
    if getattr(user, "is_staff", False):
        return get_object_or_404(StartupAdvisorBriefingJob.objects.all(), pk=job_id)
    return get_object_or_404(
        StartupAdvisorBriefingJob.objects.filter(startup_profile__owner=user),
        pk=job_id,
    )


def _resolve_target_briefing(user, briefing_id):
    if getattr(user, "is_staff", False):
        return get_object_or_404(StartupAdvisorBriefing.objects.all(), pk=briefing_id)
    return get_object_or_404(
        StartupAdvisorBriefing.objects.filter(startup_profile__owner=user),
        pk=briefing_id,
    )


class StartupAdvisorCurrentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        request_serializer = StartupReadinessRetrievalRequestSerializer(
            data=request.query_params,
        )
        request_serializer.is_valid(raise_exception=True)

        startup_profile = _resolve_target_profile(
            request.user,
            request_serializer.validated_data["startup_profile_id"],
        )

        readiness_assessment = (
            StartupReadinessAssessment.objects.filter(
                startup_profile=startup_profile,
            )
            .select_related(
                "startup_profile",
                "requested_by",
            )
            .order_by(
                "-created_at",
                "-id",
            )
            .first()
        )
        readiness_action_plan = (
            StartupReadinessActionPlan.objects.filter(
                startup_profile=startup_profile,
            )
            .select_related(
                "startup_profile",
                "source_assessment",
                "requested_by",
            )
            .order_by(
                "-created_at",
                "-id",
            )
            .first()
        )

        try:
            current_recommendations = get_current_recommendation_set(
                startup_profile=startup_profile,
            )
        except RecommendationSetIntegrityError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        assessment_data = (
            StartupReadinessAssessmentSerializer(
                readiness_assessment,
            ).data
            if readiness_assessment is not None
            else None
        )
        action_plan_data = (
            StartupReadinessActionPlanSerializer(
                readiness_action_plan,
            ).data
            if readiness_action_plan is not None
            else None
        )
        generation_data = (
            RecommendationGenerationRunDetailSerializer(
                current_recommendations.generation_run,
            ).data
            if current_recommendations.generation_run is not None
            else None
        )
        recommendation_data = RecommendationSerializer(
            current_recommendations.recommendations,
            many=True,
        ).data

        return Response(
            {
                "startup_profile": {
                    "id": str(startup_profile.id),
                    "startup_name": startup_profile.startup_name,
                    "legal_name": startup_profile.legal_name,
                    "stage": startup_profile.stage,
                    "state": startup_profile.state,
                    "district": startup_profile.district,
                },
                "readiness": {
                    "has_assessment": (readiness_assessment is not None),
                    "assessment": assessment_data,
                },
                "action_plan": {
                    "has_action_plan": (readiness_action_plan is not None),
                    "action_plan": action_plan_data,
                },
                "recommendations": {
                    "has_generation": (current_recommendations.has_generation),
                    "generation": generation_data,
                    "recommendation_count": len(
                        current_recommendations.recommendations,
                    ),
                    "recommendations": recommendation_data,
                },
            },
            status=status.HTTP_200_OK,
        )


class StartupAdvisorSnapshotGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request_serializer = StartupAdvisorSnapshotGenerationRequestSerializer(
            data=request.data,
        )
        request_serializer.is_valid(raise_exception=True)

        startup_profile = _resolve_target_profile(
            request.user,
            request_serializer.validated_data["startup_profile_id"],
        )

        try:
            snapshot = create_startup_advisor_snapshot(
                startup_profile=startup_profile,
                requested_by=request.user,
            )
        except RecommendationSetIntegrityError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            StartupAdvisorSnapshotSerializer(snapshot).data,
            status=status.HTTP_201_CREATED,
        )


class StartupAdvisorBriefingGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request_serializer = StartupAdvisorBriefingGenerationRequestSerializer(
            data=request.data,
        )
        request_serializer.is_valid(raise_exception=True)

        source_snapshot = _resolve_target_snapshot(
            request.user,
            request_serializer.validated_data["advisor_snapshot_id"],
        )

        try:
            job, created = queue_startup_advisor_briefing_job(
                source_snapshot=source_snapshot,
                requested_by=request.user,
            )
        except AdvisorBriefingJobDispatchError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "created": created,
                "job": StartupAdvisorBriefingJobSerializer(job).data,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class StartupAdvisorBriefingJobCurrentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        request_serializer = StartupReadinessRetrievalRequestSerializer(
            data=request.query_params,
        )
        request_serializer.is_valid(raise_exception=True)

        startup_profile = _resolve_target_profile(
            request.user,
            request_serializer.validated_data["startup_profile_id"],
        )

        job = (
            _visible_advisor_briefing_jobs(request.user)
            .filter(startup_profile=startup_profile)
            .select_related(
                "startup_profile",
                "source_snapshot",
                "requested_by",
                "briefing",
            )
            .order_by("-created_at", "-id")
            .first()
        )

        if job is not None:
            job = reconcile_startup_advisor_briefing_job(
                job_id=job.id,
            )

        return Response(
            {
                "startup_profile_id": str(startup_profile.id),
                "has_job": job is not None,
                "job": (StartupAdvisorBriefingJobSerializer(job).data if job is not None else None),
            },
            status=status.HTTP_200_OK,
        )


class StartupAdvisorBriefingJobDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        job = _resolve_target_job(request.user, job_id)
        job = reconcile_startup_advisor_briefing_job(
            job_id=job.id,
        )

        return Response(
            StartupAdvisorBriefingJobSerializer(job).data,
            status=status.HTTP_200_OK,
        )


class StartupAdvisorBriefingCurrentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        request_serializer = StartupReadinessRetrievalRequestSerializer(
            data=request.query_params,
        )
        request_serializer.is_valid(raise_exception=True)

        startup_profile = _resolve_target_profile(
            request.user,
            request_serializer.validated_data["startup_profile_id"],
        )
        briefing = (
            _visible_advisor_briefings(request.user)
            .filter(startup_profile=startup_profile)
            .select_related(
                "startup_profile",
                "source_snapshot",
                "requested_by",
            )
            .order_by("-completed_at", "-created_at", "-id")
            .first()
        )
        data = StartupAdvisorBriefingSerializer(briefing).data if briefing is not None else None
        return Response(
            {
                "startup_profile_id": str(startup_profile.id),
                "has_briefing": briefing is not None,
                "briefing": data,
            },
            status=status.HTTP_200_OK,
        )


class StartupAdvisorBriefingListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        request_serializer = StartupReadinessRetrievalRequestSerializer(
            data=request.query_params,
        )
        request_serializer.is_valid(raise_exception=True)

        startup_profile = _resolve_target_profile(
            request.user,
            request_serializer.validated_data["startup_profile_id"],
        )
        briefings_qs = (
            StartupAdvisorBriefing.objects.all()
            if request.user.is_staff
            else _visible_advisor_briefings(request.user)
        )
        briefings = (
            briefings_qs.filter(startup_profile=startup_profile)
            .select_related(
                "startup_profile",
                "source_snapshot",
                "requested_by",
            )
            .order_by("-completed_at", "-created_at", "-id")
        )
        data = StartupAdvisorBriefingSerializer(
            briefings,
            many=True,
        ).data
        return Response(
            {
                "startup_profile_id": str(startup_profile.id),
                "count": len(data),
                "briefings": data,
            },
            status=status.HTTP_200_OK,
        )


class StartupAdvisorBriefingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, briefing_id):
        briefing = _resolve_target_briefing(request.user, briefing_id)
        return Response(
            StartupAdvisorBriefingSerializer(briefing).data,
            status=status.HTTP_200_OK,
        )
