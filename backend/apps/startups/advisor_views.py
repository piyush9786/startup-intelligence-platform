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
    StartupProfile,
    StartupReadinessActionPlan,
    StartupReadinessAssessment,
)
from .serializers import (
    StartupAdvisorSnapshotGenerationRequestSerializer,
    StartupAdvisorSnapshotSerializer,
    StartupReadinessActionPlanSerializer,
    StartupReadinessAssessmentSerializer,
    StartupReadinessRetrievalRequestSerializer,
)
from .services import create_startup_advisor_snapshot


def _visible_profiles(user):
    queryset = StartupProfile.objects.all()
    if not user.is_staff:
        queryset = queryset.filter(owner=user)
    return queryset


class StartupAdvisorCurrentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        request_serializer = StartupReadinessRetrievalRequestSerializer(
            data=request.query_params,
        )
        request_serializer.is_valid(raise_exception=True)

        startup_profile = get_object_or_404(
            _visible_profiles(request.user),
            pk=request_serializer.validated_data["startup_profile_id"],
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

        startup_profile = get_object_or_404(
            _visible_profiles(request.user),
            pk=request_serializer.validated_data["startup_profile_id"],
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
