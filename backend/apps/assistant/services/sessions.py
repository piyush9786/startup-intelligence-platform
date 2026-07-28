from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.startups.models import StartupProfile

from ..models import (
    AgentClaimReference,
    AgentMessage,
    AgentSession,
    AgentToolCallLog,
)
from .canonical import canonical_sha256, json_ready


class AgentSessionError(ValidationError):
    pass


class AgentTurnLimitExceeded(AgentSessionError):
    pass


def _validate_founder(founder: Any) -> None:
    if (
        founder is None
        or not getattr(founder, "is_authenticated", False)
        or getattr(founder, "pk", None) is None
    ):
        raise AgentSessionError("An authenticated founder is required.")

    if not getattr(founder, "is_active", False):
        raise AgentSessionError("The founder account is inactive.")

    founder_role = getattr(
        get_user_model().Role,
        "FOUNDER",
        "founder",
    )

    if (
        not getattr(founder, "is_superuser", False)
        and getattr(founder, "role", None) != founder_role
    ):
        raise AgentSessionError("Founder access is required.")


def _validated_startup_profile(
    *,
    founder: Any,
    startup_profile: StartupProfile | None,
) -> StartupProfile | None:
    if startup_profile is None:
        return None

    profile = StartupProfile.objects.filter(
        pk=startup_profile.pk,
        owner_id=founder.pk,
    ).first()

    if profile is None:
        raise AgentSessionError("The startup profile does not belong to the founder.")

    return profile


@transaction.atomic
def create_or_get_active_session(
    *,
    founder: Any,
    agent_type: str,
    startup_profile: StartupProfile | None = None,
    state: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    max_turns: int = AgentSession.DEFAULT_MAX_TURNS,
) -> tuple[AgentSession, bool]:
    _validate_founder(founder)

    if agent_type not in AgentSession.AgentType.values:
        raise AgentSessionError(f"Unsupported agent type: {agent_type!r}.")

    if not isinstance(max_turns, int) or isinstance(
        max_turns,
        bool,
    ):
        raise AgentSessionError("max_turns must be an integer.")

    if not (1 <= max_turns <= AgentSession.MAX_ALLOWED_TURNS):
        raise AgentSessionError("max_turns is outside the supported range.")

    if state is not None and not isinstance(state, dict):
        raise AgentSessionError("Session state must be an object.")

    if context is not None and not isinstance(context, dict):
        raise AgentSessionError("Session context must be an object.")

    user_model = get_user_model()
    locked_founder = user_model.objects.select_for_update().get(pk=founder.pk)

    _validate_founder(locked_founder)

    profile = _validated_startup_profile(
        founder=locked_founder,
        startup_profile=startup_profile,
    )

    scope_key = AgentSession.GLOBAL_SCOPE_KEY if profile is None else str(profile.pk)

    existing = AgentSession.objects.filter(
        founder=locked_founder,
        agent_type=agent_type,
        scope_key=scope_key,
        status=AgentSession.Status.ACTIVE,
    ).first()

    if existing is not None:
        return existing, False

    session = AgentSession(
        founder=locked_founder,
        startup_profile=profile,
        agent_type=agent_type,
        status=AgentSession.Status.ACTIVE,
        state=json_ready(state or {}),
        context=json_ready(context or {}),
        max_turns=max_turns,
        last_activity_at=timezone.now(),
    )
    session.full_clean()
    session.save()

    return session, True


@transaction.atomic
def close_agent_session(
    *,
    session: AgentSession,
    status: str = AgentSession.Status.COMPLETED,
) -> AgentSession:
    if status not in {
        AgentSession.Status.COMPLETED,
        AgentSession.Status.ABANDONED,
    }:
        raise AgentSessionError("A session may be closed only as completed or abandoned.")

    locked_session = AgentSession.objects.select_for_update().get(pk=session.pk)

    if locked_session.status != AgentSession.Status.ACTIVE:
        return locked_session

    now = timezone.now()
    locked_session.status = status
    locked_session.completed_at = now
    locked_session.last_activity_at = now
    locked_session.full_clean()
    locked_session.save(
        update_fields=[
            "status",
            "completed_at",
            "last_activity_at",
            "updated_at",
        ]
    )

    return locked_session


@transaction.atomic
def append_agent_message(
    *,
    session: AgentSession,
    role: str,
    content: str = "",
    metadata: dict[str, Any] | None = None,
    token_count: int | None = None,
) -> AgentMessage:
    if role not in AgentMessage.Role.values:
        raise AgentSessionError(f"Unsupported message role: {role!r}.")

    if not isinstance(content, str):
        raise AgentSessionError("Message content must be text.")

    if metadata is not None and not isinstance(
        metadata,
        dict,
    ):
        raise AgentSessionError("Message metadata must be an object.")

    locked_session = AgentSession.objects.select_for_update().get(pk=session.pk)

    if locked_session.status != AgentSession.Status.ACTIVE:
        raise AgentSessionError("Messages cannot be appended to a closed session.")

    next_turn_count = locked_session.turn_count

    if role == AgentMessage.Role.USER:
        if locked_session.turn_count >= locked_session.max_turns:
            raise AgentTurnLimitExceeded(
                "The session has reached its maximum number of user turns."
            )
        next_turn_count += 1

    current_sequence = (
        locked_session.messages.aggregate(
            maximum=Max("sequence_number"),
        )["maximum"]
        or 0
    )

    message = AgentMessage(
        session=locked_session,
        sequence_number=current_sequence + 1,
        role=role,
        content=content,
        metadata=json_ready(metadata or {}),
        token_count=token_count,
    )
    message.full_clean()
    message.save()

    locked_session.turn_count = next_turn_count
    locked_session.last_activity_at = timezone.now()
    locked_session.full_clean()
    locked_session.save(
        update_fields=[
            "turn_count",
            "last_activity_at",
            "updated_at",
        ]
    )

    return message


@transaction.atomic
def record_tool_call(
    *,
    session: AgentSession,
    actor: Any,
    tool_name: str,
    tool_version: str,
    status: str,
    input_params: dict[str, Any],
    authorization_context: dict[str, Any],
    output_snapshot: Any,
    duration_ms: int,
    called_at: Any,
    triggering_message: AgentMessage | None = None,
    error_code: str = "",
    error_message: str = "",
) -> AgentToolCallLog:
    if status not in AgentToolCallLog.Status.values:
        raise AgentSessionError(f"Unsupported tool-call status: {status!r}.")

    if triggering_message is not None:
        if triggering_message.session_id != session.pk:
            raise AgentSessionError("The triggering message belongs to a different session.")

    locked_session = AgentSession.objects.select_for_update().get(pk=session.pk)

    current_sequence = (
        locked_session.tool_call_logs.aggregate(
            maximum=Max("sequence_number"),
        )["maximum"]
        or 0
    )

    normalized_output = json_ready(output_snapshot)

    log = AgentToolCallLog(
        session=locked_session,
        triggering_message=triggering_message,
        actor=(actor if getattr(actor, "pk", None) is not None else None),
        sequence_number=current_sequence + 1,
        tool_name=tool_name,
        tool_version=tool_version,
        status=status,
        input_params=json_ready(input_params),
        authorization_context=json_ready(authorization_context),
        output_snapshot=normalized_output,
        output_hash=canonical_sha256(normalized_output),
        error_code=error_code,
        error_message=error_message[:4000],
        duration_ms=max(0, int(duration_ms)),
        called_at=called_at,
    )
    log.full_clean()
    log.save()

    locked_session.last_activity_at = timezone.now()
    locked_session.save(
        update_fields=[
            "last_activity_at",
            "updated_at",
        ]
    )

    return log


@transaction.atomic
def add_claim_reference(
    *,
    message: AgentMessage,
    tool_call: AgentToolCallLog,
    claim_key: str,
    claim_text: str,
    output_path: str,
) -> AgentClaimReference:
    reference = AgentClaimReference(
        message=message,
        tool_call=tool_call,
        claim_key=claim_key.strip(),
        claim_text=claim_text.strip(),
        output_path=output_path.strip(),
    )
    reference.full_clean()
    reference.save()
    return reference
