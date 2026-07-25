"""
DRF API view for AI-drafted startup one-page documents.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.startups.models import StartupProfile
from apps.startups.services.startup_resume_generator import (
    generate_startup_executive_resume,
)
from apps.startups.utils import get_current_startup_profile


def _resolve_profile(request) -> tuple[StartupProfile | None, bool]:
    profile_id = request.data.get("startup_profile_id")

    if not profile_id:
        return get_current_startup_profile(request.user), False

    try:
        profile = StartupProfile.objects.filter(
            id=profile_id,
            owner=request.user,
        ).first()
    except (ValidationError, ValueError):
        profile = None

    return profile, True


class StartupResumeGeneratorView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        idea = request.data.get("idea_description") or request.data.get("concept")
        if not idea:
            return Response(
                {"error": "idea_description or concept is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile, was_explicit = _resolve_profile(request)
        if was_explicit and profile is None:
            return Response(
                {"detail": "Startup profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        sector = request.data.get("sector", "Technology / General")
        stage = request.data.get("stage", "Idea / Prototype")
        funding = request.data.get("funding_required", "₹25 Lakhs")

        resume_data = generate_startup_executive_resume(
            idea_description=idea,
            sector=sector,
            stage=stage,
            funding_required=funding,
            profile=profile,
        )

        return Response(resume_data, status=status.HTTP_200_OK)
