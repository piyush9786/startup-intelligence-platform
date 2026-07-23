from __future__ import annotations

from typing import Any

from django.http import Http404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.startups.models import StartupProfile

from .chatbot_serializers import (
    ChatbotCurrentQuerySerializer,
    ChatbotMessageCreateSerializer,
    serialize_chatbot_session,
)
from .models import AgentSession
from .services.chatbot import process_chatbot_message
from .services.sessions import (
    AgentSessionError,
    AgentTurnLimitExceeded,
    create_or_get_active_session,
)


def _error_detail(error: Exception) -> str:
    messages = getattr(error, "messages", None)

    if messages:
        return " ".join(str(message) for message in messages)

    return str(error)


def _resolve_startup_profile(
    *,
    user: Any,
    startup_profile_id: Any,
) -> StartupProfile | None:
    if startup_profile_id is None:
        return None

    profile = StartupProfile.objects.filter(
        pk=startup_profile_id,
        owner=user,
    ).first()

    if profile is None:
        raise Http404

    return profile


def _active_chatbot_session(
    *,
    user: Any,
    startup_profile: StartupProfile | None,
) -> tuple[AgentSession, bool]:
    return create_or_get_active_session(
        founder=user,
        startup_profile=startup_profile,
        agent_type=AgentSession.AgentType.CHATBOT,
    )


class AssistantChatTurnThrottle(ScopedRateThrottle):
    """Resolve the configured scoped rate for every request.

    DRF stores DEFAULT_THROTTLE_RATES on the base throttle class at
    import time. Reading api_settings here keeps runtime configuration
    and override_settings-based tests authoritative.
    """

    def get_rate(self) -> str | None:
        scope = getattr(self, "scope", None)

        if scope is None:
            return None

        return api_settings.DEFAULT_THROTTLE_RATES.get(scope)


class ChatbotCurrentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(
        self,
        request,
    ) -> Response:
        serializer = ChatbotCurrentQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        startup_profile = _resolve_startup_profile(
            user=request.user,
            startup_profile_id=serializer.validated_data.get("startup_profile_id"),
        )

        try:
            session, created = _active_chatbot_session(
                user=request.user,
                startup_profile=startup_profile,
            )
        except AgentSessionError as exc:
            return Response(
                {
                    "detail": _error_detail(exc),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        payload = serialize_chatbot_session(session)
        payload["created"] = created

        return Response(payload)


class ChatbotMessageCreateView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AssistantChatTurnThrottle]
    throttle_scope = "assistant_chat_turn"

    def post(
        self,
        request,
    ) -> Response:
        serializer = ChatbotMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        startup_profile = _resolve_startup_profile(
            user=request.user,
            startup_profile_id=serializer.validated_data.get("startup_profile_id"),
        )

        try:
            session, created = _active_chatbot_session(
                user=request.user,
                startup_profile=startup_profile,
            )

            process_chatbot_message(
                session=session,
                actor=request.user,
                message=serializer.validated_data["message"],
                page_context=serializer.validated_data["page_context"],
            )
        except AgentTurnLimitExceeded as exc:
            return Response(
                {
                    "detail": _error_detail(exc),
                    "code": "turn_limit_reached",
                },
                status=status.HTTP_409_CONFLICT,
            )
        except AgentSessionError as exc:
            return Response(
                {
                    "detail": _error_detail(exc),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        payload = serialize_chatbot_session(session)
        payload["created"] = created

        return Response(
            payload,
            status=status.HTTP_201_CREATED,
        )
