from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .models import (
    StartupProfile,
    StartupReadinessActionPlan,
    StartupReadinessAssessment,
)
from .serializers import (
    StartupProfileSerializer,
    StartupReadinessActionPlanGenerationRequestSerializer,
    StartupReadinessActionPlanSerializer,
    StartupReadinessAssessmentSerializer,
    StartupReadinessEvaluationRequestSerializer,
    StartupReadinessRetrievalRequestSerializer,
)
from .services import (
    create_startup_readiness_action_plan,
    create_startup_readiness_assessment,
)


def _visible_profiles(user):
    queryset = StartupProfile.objects.all()
    if not user.is_staff:
        queryset = queryset.filter(owner=user)
    return queryset


def _visible_readiness_assessments(user):
    queryset = StartupReadinessAssessment.objects.all()
    if not user.is_staff:
        queryset = queryset.filter(startup_profile__owner=user)
    return queryset


def _visible_readiness_action_plans(user):
    queryset = StartupReadinessActionPlan.objects.all()
    if not user.is_staff:
        queryset = queryset.filter(startup_profile__owner=user)
    return queryset


class StartupProfileViewSet(ModelViewSet):
    serializer_class = StartupProfileSerializer
    permission_classes = [IsAuthenticated]
    search_fields = [
        "startup_name",
        "description",
        "state",
    ]
    filterset_fields = [
        "stage",
        "state",
        "dpiit_recognized",
        "udyam_registered",
    ]

    def get_queryset(self):
        return _visible_profiles(self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class StartupReadinessEvaluateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request_serializer = StartupReadinessEvaluationRequestSerializer(
            data=request.data,
        )
        request_serializer.is_valid(raise_exception=True)

        startup_profile = get_object_or_404(
            _visible_profiles(request.user),
            pk=request_serializer.validated_data["startup_profile_id"],
        )
        assessment = create_startup_readiness_assessment(
            startup_profile=startup_profile,
            requested_by=request.user,
            assessment_date=request_serializer.validated_data["assessment_date"],
        )
        return Response(
            StartupReadinessAssessmentSerializer(assessment).data,
            status=status.HTTP_201_CREATED,
        )


class StartupReadinessCurrentView(APIView):
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
        assessment = (
            StartupReadinessAssessment.objects.filter(
                startup_profile=startup_profile,
            )
            .select_related("startup_profile", "requested_by")
            .order_by("-created_at", "-id")
            .first()
        )
        serialized_assessment = (
            StartupReadinessAssessmentSerializer(assessment).data
            if assessment is not None
            else None
        )
        return Response(
            {
                "startup_profile_id": str(startup_profile.id),
                "has_assessment": assessment is not None,
                "assessment": serialized_assessment,
            },
            status=status.HTTP_200_OK,
        )


class StartupReadinessAssessmentListView(APIView):
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
        assessments = (
            _visible_readiness_assessments(request.user)
            .filter(startup_profile=startup_profile)
            .select_related("startup_profile", "requested_by")
            .order_by("-created_at", "-id")
        )
        data = StartupReadinessAssessmentSerializer(
            assessments,
            many=True,
        ).data
        return Response(
            {
                "startup_profile_id": str(startup_profile.id),
                "count": len(data),
                "assessments": data,
            },
            status=status.HTTP_200_OK,
        )


class StartupReadinessAssessmentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, assessment_id):
        assessment = get_object_or_404(
            _visible_readiness_assessments(request.user).select_related(
                "startup_profile",
                "requested_by",
            ),
            pk=assessment_id,
        )
        return Response(
            StartupReadinessAssessmentSerializer(assessment).data,
            status=status.HTTP_200_OK,
        )


class StartupReadinessActionPlanGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request_serializer = StartupReadinessActionPlanGenerationRequestSerializer(
            data=request.data,
        )
        request_serializer.is_valid(raise_exception=True)

        source_assessment = get_object_or_404(
            _visible_readiness_assessments(request.user).select_related(
                "startup_profile",
                "requested_by",
            ),
            pk=request_serializer.validated_data["readiness_assessment_id"],
        )
        action_plan = create_startup_readiness_action_plan(
            source_assessment=source_assessment,
            requested_by=request.user,
        )
        return Response(
            StartupReadinessActionPlanSerializer(action_plan).data,
            status=status.HTTP_201_CREATED,
        )


class StartupReadinessActionPlanCurrentView(APIView):
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
        action_plan = (
            _visible_readiness_action_plans(request.user)
            .filter(startup_profile=startup_profile)
            .select_related(
                "startup_profile",
                "source_assessment",
                "requested_by",
            )
            .order_by("-created_at", "-id")
            .first()
        )
        serialized_action_plan = (
            StartupReadinessActionPlanSerializer(action_plan).data
            if action_plan is not None
            else None
        )
        return Response(
            {
                "startup_profile_id": str(startup_profile.id),
                "has_action_plan": action_plan is not None,
                "action_plan": serialized_action_plan,
            },
            status=status.HTTP_200_OK,
        )
