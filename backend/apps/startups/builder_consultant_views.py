"""
DRF API View for AI Startup Consultant Master Strategy Package Generator.
"""
from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.startups.models import StartupBuilderSection, StartupProfile
from apps.startups.services.builder_consultant_service import (
    generate_master_startup_consultant_package,
)


class MasterConsultantGeneratorView(APIView):
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

        package = generate_master_startup_consultant_package(
            idea_description=idea,
            sector=sector,
            stage=stage,
            funding_required=funding,
            profile=profile,
        )

        # Auto-persist sections if profile exists
        if profile and package.get("business_plan"):
            for sec_type, content in package["business_plan"].items():
                StartupBuilderSection.objects.update_or_create(
                    owner=request.user,
                    startup_profile=profile,
                    section_type=sec_type,
                    defaults={
                        "content": content,
                        "ai_draft": content,
                        "status": StartupBuilderSection.Status.AI_DRAFTED,
                    },
                )

        return Response(package, status=status.HTTP_200_OK)
