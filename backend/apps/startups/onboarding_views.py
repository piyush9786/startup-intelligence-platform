from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.startups.onboarding_serializers import (
    OnboardingProgressActionSerializer,
    OnboardingProgressSerializer,
)
from apps.startups.services.onboarding import (
    OnboardingProgressCompletedError,
    apply_onboarding_action,
    get_or_create_onboarding_progress,
)


class StartupOnboardingCurrentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        progress, _ = get_or_create_onboarding_progress(
            owner=request.user,
        )

        return Response(
            OnboardingProgressSerializer(progress).data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request):
        request_serializer = OnboardingProgressActionSerializer(
            data=request.data,
        )
        request_serializer.is_valid(
            raise_exception=True,
        )

        try:
            progress = apply_onboarding_action(
                owner=request.user,
                **request_serializer.validated_data,
            )
        except OnboardingProgressCompletedError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            OnboardingProgressSerializer(progress).data,
            status=status.HTTP_200_OK,
        )
