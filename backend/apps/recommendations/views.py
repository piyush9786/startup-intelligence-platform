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
)
from .services import create_eligibility_assessment


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

        profile_queryset = StartupProfile.objects.all()
        if not request.user.is_staff:
            profile_queryset = profile_queryset.filter(
                owner=request.user,
            )

        startup_profile = get_object_or_404(
            profile_queryset,
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
