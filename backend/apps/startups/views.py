from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.recommendations.models import RecommendationGenerationRun

from .models import (
    StartupProfile,
    StartupReadinessActionPlan,
    StartupReadinessAssessment,
    StartupStartingPlan,
)
from .serializers import (
    StartupDocumentAutofillRequestSerializer,
    StartupProfileSerializer,
    StartupReadinessActionPlanGenerationRequestSerializer,
    StartupReadinessActionPlanSerializer,
    StartupReadinessAssessmentSerializer,
    StartupReadinessEvaluationRequestSerializer,
    StartupReadinessRetrievalRequestSerializer,
    StartupStartingPlanGenerationRequestSerializer,
    StartupStartingPlanSerializer,
)
from .services import (
    StartingPlanSourceError,
    StartupDocumentAutofillError,
    build_startup_profile_autofill,
    create_startup_readiness_action_plan,
    create_startup_readiness_assessment,
    create_startup_starting_plan,
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


def _visible_starting_plans(user):
    queryset = StartupStartingPlan.objects.all()
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
        if getattr(self, "swagger_fake_view", False):
            return StartupProfile.objects.none()
        return _visible_profiles(self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)




class StartupProfileDocumentAutofillView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = StartupDocumentAutofillRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload = serializer.validated_data["file"]

        try:
            result = build_startup_profile_autofill(
                content=upload.read(),
                filename=upload.name,
                mime_type=serializer.validated_data["mime_type"],
                document_type_hint=serializer.validated_data["document_type"],
            )
        except StartupDocumentAutofillError as exc:
            raise ValidationError({"file": str(exc)}) from exc

        return Response(result, status=status.HTTP_200_OK)


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


class StartupReadinessActionPlanListView(APIView):
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
        action_plans = (
            _visible_readiness_action_plans(request.user)
            .filter(startup_profile=startup_profile)
            .select_related(
                "startup_profile",
                "source_assessment",
                "requested_by",
            )
            .order_by("-created_at", "-id")
        )
        data = StartupReadinessActionPlanSerializer(
            action_plans,
            many=True,
        ).data
        return Response(
            {
                "startup_profile_id": str(startup_profile.id),
                "count": len(data),
                "action_plans": data,
            },
            status=status.HTTP_200_OK,
        )


class StartupReadinessActionPlanDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, action_plan_id):
        action_plan = get_object_or_404(
            _visible_readiness_action_plans(request.user).select_related(
                "startup_profile",
                "source_assessment",
                "requested_by",
            ),
            pk=action_plan_id,
        )
        return Response(
            StartupReadinessActionPlanSerializer(action_plan).data,
            status=status.HTTP_200_OK,
        )


class StartupStartingPlanGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request_serializer = StartupStartingPlanGenerationRequestSerializer(
            data=request.data,
        )
        request_serializer.is_valid(raise_exception=True)

        startup_profile = get_object_or_404(
            _visible_profiles(request.user),
            pk=request_serializer.validated_data["startup_profile_id"],
        )
        source_action_plan = (
            _visible_readiness_action_plans(request.user)
            .filter(startup_profile=startup_profile)
            .select_related(
                "source_assessment",
                "startup_profile",
            )
            .order_by("-created_at", "-id")
            .first()
        )
        generation_run = (
            RecommendationGenerationRun.objects.filter(
                startup_profile=startup_profile,
                is_current=True,
            )
            .order_by("-completed_at", "-created_at")
            .first()
        )

        if source_action_plan is None:
            raise ValidationError(
                {
                    "startup_profile_id": (
                        "A persisted readiness action plan is required "
                        "before generating a starting plan."
                    )
                }
            )

        if generation_run is None:
            raise ValidationError(
                {
                    "startup_profile_id": (
                        "A current recommendation generation is required "
                        "before generating a starting plan."
                    )
                }
            )

        try:
            result = create_startup_starting_plan(
                source_assessment=source_action_plan.source_assessment,
                source_action_plan=source_action_plan,
                recommendation_generation_run=generation_run,
                requested_by=request.user,
            )
        except StartingPlanSourceError as exc:
            raise ValidationError({"startup_profile_id": str(exc)}) from exc

        payload = dict(StartupStartingPlanSerializer(result.plan).data)
        payload["created"] = result.created
        return Response(
            payload,
            status=(
                status.HTTP_201_CREATED
                if result.created
                else status.HTTP_200_OK
            ),
        )


class StartupStartingPlanCurrentView(APIView):
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
        plan = (
            _visible_starting_plans(request.user)
            .filter(
                startup_profile=startup_profile,
                is_current=True,
            )
            .select_related(
                "source_assessment",
                "source_action_plan",
                "recommendation_generation_run",
                "requested_by",
            )
            .first()
        )
        return Response(
            {
                "startup_profile_id": str(startup_profile.pk),
                "has_starting_plan": plan is not None,
                "starting_plan": (
                    StartupStartingPlanSerializer(plan).data
                    if plan is not None
                    else None
                ),
            },
            status=status.HTTP_200_OK,
        )


class StartupStartingPlanListView(APIView):
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
        plans = (
            _visible_starting_plans(request.user)
            .filter(startup_profile=startup_profile)
            .select_related(
                "source_assessment",
                "source_action_plan",
                "recommendation_generation_run",
                "requested_by",
            )
            .order_by("-created_at", "-id")
        )
        data = StartupStartingPlanSerializer(
            plans,
            many=True,
        ).data
        return Response(
            {
                "startup_profile_id": str(startup_profile.pk),
                "count": len(data),
                "starting_plans": data,
            },
            status=status.HTTP_200_OK,
        )


class StartupStartingPlanDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, starting_plan_id):
        plan = get_object_or_404(
            _visible_starting_plans(request.user).select_related(
                "startup_profile",
                "source_assessment",
                "source_action_plan",
                "recommendation_generation_run",
                "requested_by",
            ),
            pk=starting_plan_id,
        )
        return Response(
            StartupStartingPlanSerializer(plan).data,
            status=status.HTTP_200_OK,
        )
