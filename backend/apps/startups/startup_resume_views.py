"""
DRF API View for Startup Executive Resume & Master Plan Generator.
"""
from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.startups.models import StartupProfile
from apps.startups.services.startup_resume_generator import generate_startup_executive_resume


class StartupResumeGeneratorView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        idea = request.data.get("idea_description") or request.data.get("concept")
        if not idea:
            return Response(
                {"error": "idea_description or concept is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sector = request.data.get("sector", "Technology / General")
        stage = request.data.get("stage", "Idea / Prototype")
        funding = request.data.get("funding_required", "₹25 Lakhs")

        try:
            profile = StartupProfile.objects.get(owner=request.user)
        except StartupProfile.DoesNotExist:
            profile = None

        resume_data = generate_startup_executive_resume(
            idea_description=idea,
            sector=sector,
            stage=stage,
            funding_required=funding,
            profile=profile,
        )

        return Response(resume_data, status=status.HTTP_200_OK)
