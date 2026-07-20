from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.schemes.models import Scheme
from apps.startups.models import StartupProfile

from .models import RecommendationGenerationRun
from .serializers import (
    EligibilityAssessmentSerializer,
    EligibilityRequestSerializer,
    RecommendationGenerationRequestSerializer,
    RecommendationGenerationRunDetailSerializer,
    RecommendationGenerationRunListSerializer,
    RecommendationRetrievalRequestSerializer,
    RecommendationSerializer,
)
from .services import (
    RecommendationSetIntegrityError,
    create_eligibility_assessment,
    generate_recommendations,
    get_current_recommendation_set,
)


def _visible_profiles(user):
    queryset = StartupProfile.objects.all()
    if not user.is_staff:
        queryset = queryset.filter(owner=user)
    return queryset


def _visible_generation_runs(user):
    queryset = RecommendationGenerationRun.objects.all()
    if not user.is_staff:
        queryset = queryset.filter(
            startup_profile__owner=user,
        )
    return queryset


class EligibilityEvaluateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request_serializer = EligibilityRequestSerializer(
            data=request.data,
        )
        request_serializer.is_valid(raise_exception=True)

        scheme = get_object_or_404(
            Scheme.objects.select_related(
                "current_version",
            ),
            pk=request_serializer.validated_data["scheme_id"],
        )

        if scheme.current_version is None:
            return Response(
                {"detail": ("Scheme has no published current version.")},
                status=status.HTTP_409_CONFLICT,
            )

        startup_profile = get_object_or_404(
            _visible_profiles(request.user),
            pk=request_serializer.validated_data["startup_profile_id"],
        )

        assessment = create_eligibility_assessment(
            startup_profile=startup_profile,
            scheme_version=scheme.current_version,
            requested_by=request.user,
            assessment_date=request_serializer.validated_data["assessment_date"],
        )

        response_serializer = EligibilityAssessmentSerializer(
            assessment,
        )
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class RecommendationGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request_serializer = RecommendationGenerationRequestSerializer(
            data=request.data,
        )
        request_serializer.is_valid(raise_exception=True)

        startup_profile = get_object_or_404(
            _visible_profiles(request.user),
            pk=request_serializer.validated_data["startup_profile_id"],
        )

        generation = generate_recommendations(
            startup_profile=startup_profile,
            requested_by=request.user,
            assessment_date=request_serializer.validated_data["assessment_date"],
        )

        recommendation_serializer = RecommendationSerializer(
            generation.recommendations,
            many=True,
        )
        return Response(
            {
                "generation_id": str(
                    generation.generation_id,
                ),
                "ranking_version": generation.ranking_version,
                "startup_profile_id": str(
                    generation.startup_profile.id,
                ),
                "assessment_date": (generation.assessment_date.isoformat()),
                "assessed_scheme_count": len(
                    generation.assessments,
                ),
                "recommendation_count": len(
                    generation.recommendations,
                ),
                "excluded_scheme_count": len(
                    generation.excluded_schemes,
                ),
                "excluded_schemes": list(
                    generation.excluded_schemes,
                ),
                "recommendations": (recommendation_serializer.data),
            },
            status=status.HTTP_201_CREATED,
        )


class RecommendationCurrentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        request_serializer = RecommendationRetrievalRequestSerializer(
            data=request.query_params,
        )
        request_serializer.is_valid(raise_exception=True)

        startup_profile = get_object_or_404(
            _visible_profiles(request.user),
            pk=request_serializer.validated_data["startup_profile_id"],
        )

        try:
            current_set = get_current_recommendation_set(
                startup_profile=startup_profile,
            )
        except RecommendationSetIntegrityError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        recommendation_serializer = RecommendationSerializer(
            current_set.recommendations,
            many=True,
        )

        return Response(
            {
                "startup_profile_id": str(
                    current_set.startup_profile.id,
                ),
                "has_generation": (current_set.has_generation),
                "generation_id": (
                    str(current_set.generation_id) if current_set.generation_id else None
                ),
                "ranking_version": (current_set.ranking_version),
                "assessment_date": (
                    current_set.assessment_date.isoformat() if current_set.assessment_date else None
                ),
                "generated_at": (
                    current_set.generated_at.isoformat() if current_set.generated_at else None
                ),
                "assessed_scheme_count": (current_set.assessed_scheme_count),
                "recommendation_count": len(
                    current_set.recommendations,
                ),
                "excluded_scheme_count": len(
                    current_set.excluded_schemes,
                ),
                "excluded_schemes": (current_set.excluded_schemes),
                "recommendations": (recommendation_serializer.data),
            },
            status=status.HTTP_200_OK,
        )


class RecommendationRunListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        request_serializer = RecommendationRetrievalRequestSerializer(
            data=request.query_params,
        )
        request_serializer.is_valid(raise_exception=True)

        startup_profile = get_object_or_404(
            _visible_profiles(request.user),
            pk=request_serializer.validated_data["startup_profile_id"],
        )
        runs = (
            _visible_generation_runs(request.user)
            .filter(startup_profile=startup_profile)
            .select_related(
                "startup_profile",
                "requested_by",
            )
            .order_by(
                "-completed_at",
                "-created_at",
                "-id",
            )
        )
        response_serializer = RecommendationGenerationRunListSerializer(
            runs,
            many=True,
        )
        return Response(
            {
                "startup_profile_id": str(startup_profile.id),
                "count": len(response_serializer.data),
                "runs": response_serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class RecommendationRunDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, run_id):
        generation_run = get_object_or_404(
            _visible_generation_runs(request.user).select_related(
                "startup_profile",
                "requested_by",
            ),
            pk=run_id,
        )
        response_serializer = RecommendationGenerationRunDetailSerializer(
            generation_run,
        )
        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )
