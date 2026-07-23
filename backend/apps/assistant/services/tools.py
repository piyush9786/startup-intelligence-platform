from __future__ import annotations

from typing import Any

from apps.startups.models import StartupProfile
from apps.startups.serializers import StartupProfileSerializer

from ..models import AgentSession
from .tool_registry import (
    AgentToolContext,
    AgentToolDefinition,
    AgentToolInputError,
    AgentToolRegistry,
)


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
