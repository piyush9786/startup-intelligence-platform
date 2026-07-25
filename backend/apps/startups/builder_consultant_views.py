"""
DRF API view for AI Startup Consultant strategy package generation.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.startups.models import StartupBuilderSection, StartupProfile
from apps.startups.services.builder_consultant_service import (
    generate_master_startup_consultant_package,
)
from apps.startups.utils import get_current_startup_profile


def _resolve_profile(request) -> tuple[StartupProfile | None, bool]:
    """
    Resolve an explicitly requested owner-scoped profile.

    The current-profile fallback is retained for backward compatibility.
    """
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


class MasterConsultantGeneratorView(APIView):
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

        package = generate_master_startup_consultant_package(
            idea_description=idea,
            sector=sector,
            stage=stage,
            funding_required=funding,
            profile=profile,
        )

        # AI output is stored only as an unconfirmed draft. Existing founder
        # content and confirmed status are never overwritten.
        if profile and package.get("business_plan"):
            for section_type, draft_content in package["business_plan"].items():
                section, created = StartupBuilderSection.objects.get_or_create(
                    owner=request.user,
                    startup_profile=profile,
                    section_type=section_type,
                    defaults={
                        "content": {},
                        "ai_draft": draft_content,
                        "status": StartupBuilderSection.Status.AI_DRAFTED,
                    },
                )

                if created:
                    continue

                section.ai_draft = draft_content
                update_fields = ["ai_draft", "updated_at"]

                if section.status != StartupBuilderSection.Status.CONFIRMED:
                    section.status = StartupBuilderSection.Status.AI_DRAFTED
                    update_fields.append("status")

                section.save(update_fields=update_fields)

        return Response(package, status=status.HTTP_200_OK)
