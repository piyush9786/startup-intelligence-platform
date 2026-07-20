from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .models import StartupProfile
from .serializers import (
    StartupProfileSerializer,
    StartupReadinessAssessmentSerializer,
    StartupReadinessEvaluationRequestSerializer,
)
from .services import (
    create_startup_readiness_assessment,
)


def _visible_profiles(user):
    queryset = StartupProfile.objects.all()
    if not user.is_staff:
        queryset = queryset.filter(owner=user)
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
        request_serializer.is_valid(
            raise_exception=True,
        )

        startup_profile = get_object_or_404(
            _visible_profiles(request.user),
            pk=request_serializer.validated_data["startup_profile_id"],
        )

        assessment = create_startup_readiness_assessment(
            startup_profile=startup_profile,
            requested_by=request.user,
            assessment_date=(request_serializer.validated_data["assessment_date"]),
        )
        response_serializer = StartupReadinessAssessmentSerializer(
            assessment,
        )
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )
