"""
Copilot context injection endpoint for the Universal AI Copilot.

POST /api/v1/assistant/chatbot/current/copilot-context/
    Accepts { workspace, context } and writes it to the active session's
    copilot_context field. Validates the workspace slug against an
    explicit whitelist.
"""
from __future__ import annotations

import logging

from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.assistant.models import AgentSession
from apps.assistant.services.sessions import create_or_get_active_session
from apps.startups.models import StartupProfile

logger = logging.getLogger(__name__)

# Whitelist of known workspace slugs the frontend can inject context for.
ALLOWED_WORKSPACES = frozenset(
    {
        # Current frontend workspace slugs
        "dashboard",
        "startup",
        "builder",
        "capital-planner",
        "tracker",
        "roadmap",
        "milestones",
        "schemes",
        "requirements",
        "funding",
        "advisor",
        "research",
        "intelligence",
        "reviewer-verifications",
        "onboarding",
        "documents",

        # Backward-compatible aliases
        "overview",
        "document-intake",
        "assessment",
        "starting-plan",
        "funding-plan",
        "scheme-detail",
        "verification",
    }
)

class CopilotContextSerializer(serializers.Serializer):
    workspace = serializers.CharField(max_length=64)
    context = serializers.JSONField(required=False, default=dict)

    def validate_workspace(self, value: str) -> str:
        slug = value.strip().lower()
        if slug not in ALLOWED_WORKSPACES:
            raise serializers.ValidationError(
                f"Unknown workspace slug '{slug}'. "
                "Context can only be set for known platform workspaces."
            )
        return slug


class CopilotContextView(APIView):
    """
    Injects the active workspace context into the current chatbot session.
    Called by the frontend ChatbotDrawer whenever the drawer opens or the
    active workspace changes.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CopilotContextSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        workspace = serializer.validated_data["workspace"]
        context = serializer.validated_data.get("context", {})

        # Find the active startup profile for context (if any)
        profile = (
            StartupProfile.objects.filter(owner=request.user)
            .order_by("-created_at")
            .first()
        )

        try:
            session, _ = create_or_get_active_session(
                founder=request.user,
                agent_type=AgentSession.AgentType.CHATBOT,
                startup_profile=profile,
            )
        except Exception as exc:
            logger.warning("Could not get chatbot session for copilot context: %s", exc)
            return Response(
                {"detail": "Could not locate active chatbot session."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Update copilot_context on the session
        AgentSession.objects.filter(pk=session.pk).update(
            copilot_context={
                "workspace": workspace,
                "context": context,
            }
        )

        return Response(
            {
                "workspace": workspace,
                "context_injected": True,
            },
            status=status.HTTP_200_OK,
        )
