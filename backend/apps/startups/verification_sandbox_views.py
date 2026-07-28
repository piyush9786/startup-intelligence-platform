"""
DRF View for Instant Verification Sandbox (GSTIN checksum & DPIIT validation).
"""
from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.startups.models import StartupProfile
from apps.startups.services.verification_sandbox import run_instant_verification_sandbox


class InstantVerificationSandboxView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        field_name = request.data.get("field_name")
        field_value = request.data.get("field_value")

        if not field_name or not field_value:
            return Response(
                {"error": "field_name and field_value are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            profile = StartupProfile.objects.get(owner=request.user)
        except StartupProfile.DoesNotExist:
            return Response(
                {"error": "Startup profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        result = run_instant_verification_sandbox(
            profile,
            field_name=field_name,
            field_value=field_value,
        )

        return Response(result, status=status.HTTP_200_OK)
