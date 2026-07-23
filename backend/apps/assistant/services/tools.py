from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from django.db import transaction
from rest_framework import serializers

from apps.startups.models import (
    StartupAssessmentDraft,
    StartupProfile,
)
from apps.startups.serializers import (
    StartupAssessmentDraftUpdateSerializer,
    StartupAssessmentSubmissionSerializer,
    StartupProfileSerializer,
)

from ..models import AgentSession
from .canonical import json_ready
from .concierge import get_concierge_state
from .tool_registry import (
    AgentToolContext,
    AgentToolDefinition,
    AgentToolInputError,
    AgentToolRegistry,
)

ASSESSMENT_DRAFT_UPDATE_CAPABILITY = "assessment_draft_update"
ASSESSMENT_DRAFT_UPDATE_TOOL = "update_startup_assessment_draft"
ASSESSMENT_DRAFT_UPDATE_VERSION = "v1"


def get_startup_profile(
    context: AgentToolContext,
    input_params: dict[str, Any],
) -> dict[str, Any]:
    if input_params:
        raise AgentToolInputError("get_startup_profile does not accept input parameters.")

    if context.startup_profile_id is None:
        return {
            "startup_profile": None,
            "scope": "global",
        }

    profile = StartupProfile.objects.filter(
        pk=context.startup_profile_id,
        owner_id=context.founder_id,
    ).first()

    if profile is None:
        raise AgentToolInputError("The session startup profile is unavailable.")

    return {
        "startup_profile": dict(StartupProfileSerializer(profile).data),
        "scope": "startup_profile",
    }


def _input_error_from_serializer(
    error: serializers.ValidationError,
) -> AgentToolInputError:
    detail = json_ready(error.detail)

    return AgentToolInputError(
        json.dumps(
            detail,
            sort_keys=True,
            separators=(",", ":"),
        )
    )


@transaction.atomic
def update_startup_assessment_draft(
    context: AgentToolContext,
    input_params: dict[str, Any],
) -> dict[str, Any]:
    accepted_keys = {
        "draft_id",
        "updates",
    }
    unknown_parameters = set(input_params) - accepted_keys

    if unknown_parameters:
        raise AgentToolInputError(f"Unsupported tool parameters: {sorted(unknown_parameters)!r}.")

    raw_draft_id = input_params.get("draft_id")
    updates = input_params.get("updates")

    if raw_draft_id in (None, ""):
        raise AgentToolInputError("draft_id is required.")

    try:
        draft_id = UUID(str(raw_draft_id))
    except (TypeError, ValueError) as exc:
        raise AgentToolInputError("draft_id must be a valid UUID.") from exc

    if not isinstance(updates, dict):
        raise AgentToolInputError("updates must be an object.")

    if not updates:
        raise AgentToolInputError("At least one draft field is required.")

    session = (
        AgentSession.objects.select_for_update()
        .filter(
            pk=context.session_id,
            founder_id=context.founder_id,
            agent_type=AgentSession.AgentType.CONCIERGE,
        )
        .first()
    )

    if session is None:
        raise AgentToolInputError("The concierge session is unavailable.")

    draft = (
        StartupAssessmentDraft.objects.select_for_update()
        .filter(
            pk=draft_id,
            owner_id=context.founder_id,
        )
        .first()
    )

    if draft is None:
        raise AgentToolInputError("The assessment draft is unavailable.")

    concierge_state = get_concierge_state(
        session=session,
        draft=draft,
    )
    current_state = concierge_state["current_state"]
    allowed_fields = set(concierge_state["allowed_fields"])

    unsupported_fields = set(updates) - allowed_fields

    if unsupported_fields:
        raise AgentToolInputError(
            "The current concierge state does not allow "
            "these fields: "
            f"{sorted(unsupported_fields)!r}."
        )

    value_serializer = StartupAssessmentSubmissionSerializer(
        data=updates,
        partial=True,
    )

    try:
        value_serializer.is_valid(raise_exception=True)
    except serializers.ValidationError as exc:
        raise _input_error_from_serializer(exc) from exc

    normalized_updates = dict(json_ready(value_serializer.validated_data))
    previous_data = dict(draft.data or {})
    previous_values = {field: previous_data.get(field) for field in sorted(normalized_updates)}
    previous_step = draft.current_step
    mapped_step = int(concierge_state["assessment_step"])
    target_step = max(
        previous_step,
        mapped_step,
    )

    update_serializer = StartupAssessmentDraftUpdateSerializer(
        instance=draft,
        data={
            "current_step": target_step,
            "data": normalized_updates,
        },
        partial=True,
    )

    try:
        update_serializer.is_valid(raise_exception=True)
        updated_draft = update_serializer.save()
    except serializers.ValidationError as exc:
        raise _input_error_from_serializer(exc) from exc

    new_data = dict(updated_draft.data or {})
    new_values = {field: new_data.get(field) for field in sorted(normalized_updates)}

    return {
        "draft_id": str(updated_draft.pk),
        "status": updated_draft.status,
        "concierge_state": current_state,
        "assessment_step": mapped_step,
        "previous_step": previous_step,
        "current_step": updated_draft.current_step,
        "changed_fields": sorted(normalized_updates),
        "previous_values": previous_values,
        "new_values": new_values,
    }


def register_default_tools(
    registry: AgentToolRegistry,
) -> None:
    registry.register(
        AgentToolDefinition(
            name="get_startup_profile",
            version="v1",
            description=(
                "Return the founder-owned startup profile "
                "associated with the current agent session."
            ),
            handler=get_startup_profile,
            allowed_agent_types=frozenset(AgentSession.AgentType.values),
            read_only=True,
        )
    )
    registry.register(
        AgentToolDefinition(
            name=ASSESSMENT_DRAFT_UPDATE_TOOL,
            version=ASSESSMENT_DRAFT_UPDATE_VERSION,
            description=(
                "Update only the founder-owned assessment "
                "draft fields allowed by the current "
                "concierge state."
            ),
            handler=update_startup_assessment_draft,
            allowed_agent_types=frozenset(
                {
                    AgentSession.AgentType.CONCIERGE,
                }
            ),
            read_only=False,
            write_capability=(ASSESSMENT_DRAFT_UPDATE_CAPABILITY),
        )
    )
