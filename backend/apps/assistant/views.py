from __future__ import annotations

from typing import Any

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.startups.models import (
    StartupAssessmentDraft,
    StartupProfile,
)

from .chatbot_serializers import (
    ChatbotCurrentQuerySerializer,
    ChatbotMessageCreateSerializer,
    serialize_chatbot_session,
)
from .concierge_serializers import (
    ConciergeCurrentQuerySerializer,
    ConciergeDraftUpdateSerializer,
    ConciergeTransitionSerializer,
)
from .models import AgentSession
from .services.chatbot import process_chatbot_message
from .services.concierge import (
    ConciergeStateError,
    advance_concierge_session,
    get_concierge_state,
    initialize_concierge_session,
)
from .services.sessions import (
    AgentSessionError,
    AgentTurnLimitExceeded,
    create_or_get_active_session,
)
from .services.tool_registry import (
    AgentToolAuthorizationError,
    AgentToolExecutionError,
    execute_registered_tool,
)
from .services.tools import (
    ASSESSMENT_DRAFT_UPDATE_CAPABILITY,
    ASSESSMENT_DRAFT_UPDATE_TOOL,
)


def _error_detail(error: Exception) -> str:
    messages = getattr(error, "messages", None)

    if messages:
        return " ".join(str(message) for message in messages)

    return str(error)


def _require_founder(
    user: Any,
) -> None:
    if getattr(user, "role", None) != "founder":
        raise PermissionDenied("Founder access is required.")


def _resolve_startup_profile(
    *,
    user: Any,
    startup_profile_id: Any,
) -> StartupProfile | None:
    if startup_profile_id is None:
        return None

    if getattr(user, "is_staff", False):
        profile = StartupProfile.objects.filter(pk=startup_profile_id).first()
    else:
        profile = StartupProfile.objects.filter(
            pk=startup_profile_id,
            owner=user,
        ).first()

    if profile is None:
        raise Http404("The startup profile was not found.")

    return profile


def _active_session_for_scope(
    *,
    user: Any,
    startup_profile: StartupProfile | None,
    agent_type: str,
) -> AgentSession | None:
    return (
        AgentSession.objects.filter(
            founder=user,
            startup_profile=startup_profile,
            agent_type=agent_type,
            status=AgentSession.Status.ACTIVE,
        )
        .order_by(
            "-last_activity_at",
            "-created_at",
        )
        .first()
    )


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


def _active_concierge_session(
    *,
    user: Any,
    startup_profile: StartupProfile | None,
) -> tuple[AgentSession, bool]:
    return create_or_get_active_session(
        founder=user,
        startup_profile=startup_profile,
        agent_type=AgentSession.AgentType.CONCIERGE,
    )


def _scoped_draft_queryset(
    *,
    user: Any,
    startup_profile: StartupProfile | None,
):
    return StartupAssessmentDraft.objects.filter(
        owner=user,
        startup_profile=startup_profile,
    )


def _resolve_scoped_draft(
    *,
    user: Any,
    startup_profile: StartupProfile | None,
    draft_id: Any,
) -> StartupAssessmentDraft:
    draft = (
        _scoped_draft_queryset(
            user=user,
            startup_profile=startup_profile,
        )
        .filter(pk=draft_id)
        .first()
    )

    if draft is None:
        raise Http404("The assessment draft was not found.")

    return draft


def _resolve_bound_or_open_draft(
    *,
    user: Any,
    startup_profile: StartupProfile | None,
    session: AgentSession | None,
) -> StartupAssessmentDraft:
    if session is not None:
        bound_draft_id = dict(session.state or {}).get("draft_id")

        if bound_draft_id:
            bound_draft = (
                _scoped_draft_queryset(
                    user=user,
                    startup_profile=startup_profile,
                )
                .filter(pk=bound_draft_id)
                .first()
            )

            if bound_draft is None:
                raise Http404("The concierge assessment draft was not found.")

            return bound_draft

    draft = (
        _scoped_draft_queryset(
            user=user,
            startup_profile=startup_profile,
        )
        .filter(
            status=StartupAssessmentDraft.Status.DRAFT,
        )
        .order_by(
            "-updated_at",
            "-id",
        )
        .first()
    )

    if draft is None:
        raise Http404("An open assessment draft was not found.")

    return draft


def _concierge_state_error_response(
    error: ConciergeStateError,
) -> Response:
    return Response(
        {
            "detail": _error_detail(error),
            "code": "concierge_state_conflict",
        },
        status=status.HTTP_409_CONFLICT,
    )


def _tool_authorization_error_response(
    error: AgentToolAuthorizationError,
) -> Response:
    return Response(
        {
            "detail": (error.log.error_message or _error_detail(error)),
            "code": error.log.error_code,
        },
        status=status.HTTP_403_FORBIDDEN,
    )


def _tool_execution_error_response(
    error: AgentToolExecutionError,
) -> Response:
    response_status = status.HTTP_400_BAD_REQUEST

    if error.log.error_code == "ConciergeStateError":
        response_status = status.HTTP_409_CONFLICT

    return Response(
        {
            "detail": (error.log.error_message or _error_detail(error)),
            "code": error.log.error_code,
        },
        status=response_status,
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

    def allow_request(self, request, view) -> bool:
        self.scope = getattr(view, "throttle_scope", None)
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)
        return super().allow_request(request, view)


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
            startup_profile_id=(serializer.validated_data.get("startup_profile_id")),
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
            startup_profile_id=(serializer.validated_data.get("startup_profile_id")),
        )

        try:
            session, created = _active_chatbot_session(
                user=request.user,
                startup_profile=startup_profile,
            )

            process_chatbot_message(
                session=session,
                actor=request.user,
                message=(serializer.validated_data["message"]),
                page_context=(serializer.validated_data["page_context"]),
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


class ConciergeCurrentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(
        self,
        request,
    ) -> Response:
        _require_founder(request.user)

        serializer = ConciergeCurrentQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        startup_profile = _resolve_startup_profile(
            user=request.user,
            startup_profile_id=(serializer.validated_data.get("startup_profile_id")),
        )
        existing_session = _active_session_for_scope(
            user=request.user,
            startup_profile=startup_profile,
            agent_type=AgentSession.AgentType.CONCIERGE,
        )
        draft = _resolve_bound_or_open_draft(
            user=request.user,
            startup_profile=startup_profile,
            session=existing_session,
        )

        try:
            session, created = _active_concierge_session(
                user=request.user,
                startup_profile=startup_profile,
            )
            payload = initialize_concierge_session(
                session=session,
                draft=draft,
            )
        except AgentSessionError as exc:
            return Response(
                {
                    "detail": _error_detail(exc),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        except ConciergeStateError as exc:
            return _concierge_state_error_response(exc)

        payload["created"] = created

        return Response(payload)


class ConciergeDraftUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(
        self,
        request,
    ) -> Response:
        _require_founder(request.user)

        serializer = ConciergeDraftUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        startup_profile = _resolve_startup_profile(
            user=request.user,
            startup_profile_id=(serializer.validated_data.get("startup_profile_id")),
        )
        draft = _resolve_scoped_draft(
            user=request.user,
            startup_profile=startup_profile,
            draft_id=serializer.validated_data["draft_id"],
        )

        try:
            session, created = _active_concierge_session(
                user=request.user,
                startup_profile=startup_profile,
            )
            initialize_concierge_session(
                session=session,
                draft=draft,
            )
            result = execute_registered_tool(
                session=session,
                actor=request.user,
                tool_name=(ASSESSMENT_DRAFT_UPDATE_TOOL),
                input_params={
                    "draft_id": str(draft.pk),
                    "updates": (serializer.validated_data["updates"]),
                },
                write_capabilities={
                    ASSESSMENT_DRAFT_UPDATE_CAPABILITY,
                },
            )
            session.refresh_from_db()
            draft.refresh_from_db()
            payload = get_concierge_state(
                session=session,
                draft=draft,
            )
        except AgentSessionError as exc:
            return Response(
                {
                    "detail": _error_detail(exc),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        except ConciergeStateError as exc:
            return _concierge_state_error_response(exc)
        except AgentToolAuthorizationError as exc:
            return _tool_authorization_error_response(exc)
        except AgentToolExecutionError as exc:
            return _tool_execution_error_response(exc)

        payload["created"] = created
        payload["update"] = result.output

        return Response(payload)


class ConciergeTransitionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(
        self,
        request,
    ) -> Response:
        _require_founder(request.user)

        serializer = ConciergeTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        startup_profile = _resolve_startup_profile(
            user=request.user,
            startup_profile_id=(serializer.validated_data.get("startup_profile_id")),
        )
        draft = _resolve_scoped_draft(
            user=request.user,
            startup_profile=startup_profile,
            draft_id=serializer.validated_data["draft_id"],
        )

        try:
            session, created = _active_concierge_session(
                user=request.user,
                startup_profile=startup_profile,
            )
            initialize_concierge_session(
                session=session,
                draft=draft,
            )
            payload = advance_concierge_session(
                session=session,
                draft=draft,
                expected_state=(serializer.validated_data["expected_state"]),
                confirmed=serializer.validated_data["confirmed"],
            )
        except AgentSessionError as exc:
            return Response(
                {
                    "detail": _error_detail(exc),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        except ConciergeStateError as exc:
            return _concierge_state_error_response(exc)

        payload["created"] = created

        return Response(payload)
