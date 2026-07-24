"""
API views for the AI Startup Builder section workspaces.

Endpoints:
  GET  /api/v1/startup-builder/sections/
       List all builder sections for the founder's current startup profile.

  GET  /api/v1/startup-builder/sections/{section_type}/
       Retrieve a single section (returns empty content if not yet created).

  PUT  /api/v1/startup-builder/sections/{section_type}/
       Create or update section content. Set confirm=true to confirm the section.

  POST /api/v1/startup-builder/sections/{section_type}/draft/
       Request an AI-generated draft for the section. Best-effort; requires
       an active startup profile with sufficient data.
"""
from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.startups.models import StartupBuilderSection, StartupProfile
from apps.startups.utils import get_current_startup_profile

from .builder_serializers import (
    PHASE_54_SECTION_TYPES,
    StartupBuilderSectionSerializer,
    StartupBuilderSectionUpdateSerializer,
)
from .services.builder_draft_service import (
    BuilderDraftError,
    apply_ai_draft_to_section,
    generate_builder_section_draft,
    upsert_builder_section,
)

logger = logging.getLogger(__name__)


def _get_current_profile(user) -> StartupProfile | None:
    return get_current_startup_profile(user)



def _allowed_section_types() -> list[str]:
    return [s.value for s in StartupBuilderSection.SectionType]


class StartupBuilderSectionListView(APIView):
    """
    GET /api/v1/startup-builder/sections/

    List all persisted builder sections for the founder's current startup
    profile. Returns an empty list if no sections have been saved yet.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = _get_current_profile(request.user)
        if profile is None:
            return Response({"sections": []})

        sections = StartupBuilderSection.objects.filter(
            owner=request.user,
            startup_profile=profile,
        ).order_by("section_type")

        serializer = StartupBuilderSectionSerializer(sections, many=True)
        return Response({"sections": serializer.data})


class StartupBuilderSectionDetailView(APIView):
    """
    GET  /api/v1/startup-builder/sections/{section_type}/
    PUT  /api/v1/startup-builder/sections/{section_type}/
    """

    permission_classes = [IsAuthenticated]

    def _validate_section_type(self, section_type: str) -> str | None:
        allowed = _allowed_section_types()
        if section_type not in allowed:
            return None
        return section_type

    def get(self, request, section_type: str):
        if not self._validate_section_type(section_type):
            return Response(
                {"detail": f"Unknown section type '{section_type}'."},
                status=status.HTTP_404_NOT_FOUND,
            )

        profile = _get_current_profile(request.user)
        if profile is None:
            return Response(
                {"detail": "No startup profile found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        section = StartupBuilderSection.objects.filter(
            owner=request.user,
            startup_profile=profile,
            section_type=section_type,
        ).first()

        if section is None:
            return Response(
                {
                    "section_type": section_type,
                    "status": StartupBuilderSection.Status.DRAFT,
                    "content": {},
                    "ai_draft": {},
                    "confirmed_at": None,
                }
            )

        serializer = StartupBuilderSectionSerializer(section)
        return Response(serializer.data)

    def put(self, request, section_type: str):
        if not self._validate_section_type(section_type):
            return Response(
                {"detail": f"Unknown section type '{section_type}'."},
                status=status.HTTP_404_NOT_FOUND,
            )

        profile = _get_current_profile(request.user)
        if profile is None:
            return Response(
                {"detail": "No startup profile found. Complete your startup profile first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = StartupBuilderSectionUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        content = serializer.validated_data["content"]
        confirm = serializer.validated_data["confirm"]

        section_status = (
            StartupBuilderSection.Status.CONFIRMED
            if confirm
            else StartupBuilderSection.Status.DRAFT
        )

        section = upsert_builder_section(
            owner=request.user,
            profile=profile,
            section_type=section_type,
            content=content,
            status=section_status,
        )

        out = StartupBuilderSectionSerializer(section)
        response_status = (
            status.HTTP_201_CREATED
            if section.created_at == section.updated_at
            else status.HTTP_200_OK
        )
        return Response(out.data, status=response_status)


class StartupBuilderSectionDraftView(APIView):
    """
    POST /api/v1/startup-builder/sections/{section_type}/draft/

    Request an AI-generated draft for a builder section.
    Returns the draft immediately (synchronous). The draft is persisted
    against the section but does not overwrite confirmed founder content.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, section_type: str):
        allowed = _allowed_section_types()
        if section_type not in allowed:
            return Response(
                {"detail": f"Unknown section type '{section_type}'."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Only Phase 54.1 section types support AI drafting currently
        if section_type not in PHASE_54_SECTION_TYPES:
            return Response(
                {"detail": f"AI drafting is not available for '{section_type}' yet."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile = _get_current_profile(request.user)
        if profile is None:
            return Response(
                {"detail": "No startup profile found. Complete your startup profile first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = generate_builder_section_draft(
                section_type=section_type,
                profile=profile,
            )
        except BuilderDraftError as exc:
            logger.warning(
                "Builder draft generation failed for %s / %s: %s",
                request.user,
                section_type,
                exc,
            )
            return Response(
                {
                    "detail": (
                        "AI draft generation is currently unavailable. "
                        "Please fill in the section manually."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        section = apply_ai_draft_to_section(
            owner=request.user,
            profile=profile,
            section_type=section_type,
            draft=result.draft,
            model_name=result.model_name,
            prompt_version=result.prompt_version,
        )

        out = StartupBuilderSectionSerializer(section)
        return Response(out.data, status=status.HTTP_200_OK)
