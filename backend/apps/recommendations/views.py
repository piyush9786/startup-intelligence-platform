from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.schemes.models import Scheme
from apps.startups.models import StartupProfile

from .serializers import (
    EligibilityAssessmentSerializer,
    EligibilityRequestSerializer,
    RecommendationGenerationRequestSerializer,
    RecommendationSerializer,
)
from .services import (
    create_eligibility_assessment,
    generate_recommendations,
)


def _visible_profiles(user):
    queryset = StartupProfile.objects.all()
    if not user.is_staff:
        queryset = queryset.filter(owner=user)
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
                "recommendations": recommendation_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )
