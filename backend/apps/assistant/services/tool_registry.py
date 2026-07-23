from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from time import perf_counter
from typing import Any

from django.utils import timezone

from ..models import (
    AgentMessage,
    AgentSession,
    AgentToolCallLog,
)
from .canonical import json_ready
from .sessions import record_tool_call

TOOL_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,99}$")

WRITE_TOOL_CAPABILITY_ALLOWLIST = frozenset(
    {
        (
            "update_startup_assessment_draft",
            "v1",
            "assessment_draft_update",
        ),
    }
)


class AgentToolRegistryError(RuntimeError):
    pass


class AgentToolNotRegistered(AgentToolRegistryError):
    pass


class AgentToolAuthorizationError(AgentToolRegistryError):
    def __init__(
        self,
        message: str,
        *,
        log: AgentToolCallLog,
    ) -> None:
        super().__init__(message)
        self.log = log


class AgentToolExecutionError(AgentToolRegistryError):
    def __init__(
        self,
        message: str,
        *,
        log: AgentToolCallLog,
    ) -> None:
        super().__init__(message)
        self.log = log


class AgentToolInputError(ValueError):
    pass


@dataclass(frozen=True)
class AgentToolContext:
    actor_id: str
    actor_role: str
    founder_id: str
    startup_profile_id: str | None
    session_id: str
    agent_type: str


AgentToolHandler = Callable[
    [
        AgentToolContext,
        dict[str, Any],
    ],
    Any,
]


@dataclass(frozen=True)
class AgentToolDefinition:
    name: str
    version: str
    description: str
    handler: AgentToolHandler
    allowed_agent_types: frozenset[str]
    read_only: bool = True
    write_capability: str | None = None

    def __post_init__(self) -> None:
        if not TOOL_NAME_PATTERN.fullmatch(self.name):
            raise AgentToolRegistryError(f"Invalid tool name: {self.name!r}.")

        if not self.version.strip():
            raise AgentToolRegistryError("A tool version is required.")

        if not self.description.strip():
            raise AgentToolRegistryError("A tool description is required.")

        if not self.allowed_agent_types:
            raise AgentToolRegistryError("At least one allowed agent type is required.")

        invalid_types = set(self.allowed_agent_types) - set(AgentSession.AgentType.values)

        if invalid_types:
            raise AgentToolRegistryError(f"Unsupported agent types: {sorted(invalid_types)!r}.")

        if self.write_capability is not None:
            if not TOOL_NAME_PATTERN.fullmatch(self.write_capability):
                raise AgentToolRegistryError(
                    f"Invalid write capability: {self.write_capability!r}."
                )

            if self.read_only:
                raise AgentToolRegistryError("Read-only tools cannot declare a write capability.")

        if not callable(self.handler):
            raise AgentToolRegistryError("A callable tool handler is required.")


@dataclass(frozen=True)
class AgentToolExecutionResult:
    output: Any
    log: AgentToolCallLog


class AgentToolRegistry:
    def __init__(self) -> None:
        self._definitions: dict[
            str,
            AgentToolDefinition,
        ] = {}

    def register(
        self,
        definition: AgentToolDefinition,
    ) -> None:
        if definition.name in self._definitions:
            raise AgentToolRegistryError(f"Tool {definition.name!r} is already registered.")

        self._definitions[definition.name] = definition

    def get(
        self,
        name: str,
    ) -> AgentToolDefinition:
        try:
            return self._definitions[name]
        except KeyError as exc:
            raise AgentToolNotRegistered(f"Tool {name!r} is not registered.") from exc

    def list(
        self,
        *,
        agent_type: str | None = None,
    ) -> tuple[AgentToolDefinition, ...]:
        definitions = self._definitions.values()

        if agent_type is not None:
            definitions = (
                definition
                for definition in definitions
                if agent_type in definition.allowed_agent_types
            )

        return tuple(
            sorted(
                definitions,
                key=lambda definition: definition.name,
            )
        )


def _authorization_context(
    *,
    session: AgentSession,
    actor: Any,
    definition: AgentToolDefinition | None,
    allowed: bool,
    reason: str,
    granted_write_capabilities: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    return {
        "actor_id": (str(actor.pk) if getattr(actor, "pk", None) is not None else None),
        "actor_role": getattr(actor, "role", ""),
        "actor_is_active": bool(getattr(actor, "is_active", False)),
        "session_id": str(session.pk),
        "session_founder_id": str(session.founder_id),
        "startup_profile_id": (
            str(session.startup_profile_id) if session.startup_profile_id is not None else None
        ),
        "agent_type": session.agent_type,
        "session_status": session.status,
        "tool_read_only": (definition.read_only if definition is not None else None),
        "tool_write_capability": (definition.write_capability if definition is not None else None),
        "granted_write_capabilities": sorted(granted_write_capabilities),
        "allowed": allowed,
        "reason": reason,
    }


def _denied(
    *,
    session: AgentSession,
    actor: Any,
    tool_name: str,
    tool_version: str,
    input_params: dict[str, Any],
    definition: AgentToolDefinition | None,
    reason: str,
    error_code: str,
    triggering_message: AgentMessage | None,
    called_at: Any,
    granted_write_capabilities: frozenset[str] = frozenset(),
) -> AgentToolAuthorizationError:
    output = {
        "denied": True,
        "reason": reason,
    }

    log = record_tool_call(
        session=session,
        actor=actor,
        tool_name=tool_name,
        tool_version=tool_version,
        status=AgentToolCallLog.Status.DENIED,
        input_params=input_params,
        authorization_context=_authorization_context(
            session=session,
            actor=actor,
            definition=definition,
            allowed=False,
            reason=reason,
            granted_write_capabilities=(granted_write_capabilities),
        ),
        output_snapshot=output,
        duration_ms=0,
        called_at=called_at,
        triggering_message=triggering_message,
        error_code=error_code,
        error_message=reason,
    )

    return AgentToolAuthorizationError(
        reason,
        log=log,
    )


def execute_registered_tool(
    *,
    session: AgentSession,
    actor: Any,
    tool_name: str,
    input_params: dict[str, Any] | None = None,
    triggering_message: AgentMessage | None = None,
    registry: AgentToolRegistry | None = None,
    write_capabilities: (set[str] | frozenset[str] | tuple[str, ...] | list[str] | None) = None,
) -> AgentToolExecutionResult:
    selected_registry = registry if registry is not None else default_tool_registry()

    params = input_params or {}

    if not isinstance(params, dict):
        raise AgentToolInputError("Tool input parameters must be an object.")

    if write_capabilities is None:
        normalized_write_capabilities = frozenset()
    else:
        if isinstance(write_capabilities, str):
            raise AgentToolInputError("Write capabilities must be a collection.")

        try:
            normalized_write_capabilities = frozenset(write_capabilities)
        except TypeError as exc:
            raise AgentToolInputError("Write capabilities must be a collection.") from exc

        if any(
            not isinstance(capability, str) or not TOOL_NAME_PATTERN.fullmatch(capability)
            for capability in normalized_write_capabilities
        ):
            raise AgentToolInputError("Write capabilities contain an invalid value.")

    called_at = timezone.now()

    try:
        definition = selected_registry.get(tool_name)
    except AgentToolNotRegistered:
        raise _denied(
            session=session,
            actor=actor,
            tool_name=tool_name,
            tool_version="unregistered",
            input_params=params,
            definition=None,
            reason="The requested tool is not registered.",
            error_code="tool_not_registered",
            triggering_message=triggering_message,
            called_at=called_at,
        ) from None

    if (
        actor is None
        or not getattr(actor, "is_authenticated", False)
        or getattr(actor, "pk", None) is None
    ):
        raise _denied(
            session=session,
            actor=actor,
            tool_name=definition.name,
            tool_version=definition.version,
            input_params=params,
            definition=definition,
            reason="An authenticated actor is required.",
            error_code="authentication_required",
            triggering_message=triggering_message,
            called_at=called_at,
        )

    if not getattr(actor, "is_active", False):
        raise _denied(
            session=session,
            actor=actor,
            tool_name=definition.name,
            tool_version=definition.version,
            input_params=params,
            definition=definition,
            reason="The actor account is inactive.",
            error_code="actor_inactive",
            triggering_message=triggering_message,
            called_at=called_at,
        )

    if actor.pk != session.founder_id:
        raise _denied(
            session=session,
            actor=actor,
            tool_name=definition.name,
            tool_version=definition.version,
            input_params=params,
            definition=definition,
            reason=("The actor does not own the agent session."),
            error_code="session_owner_required",
            triggering_message=triggering_message,
            called_at=called_at,
        )

    if session.status != AgentSession.Status.ACTIVE:
        raise _denied(
            session=session,
            actor=actor,
            tool_name=definition.name,
            tool_version=definition.version,
            input_params=params,
            definition=definition,
            reason="The agent session is closed.",
            error_code="session_closed",
            triggering_message=triggering_message,
            called_at=called_at,
        )

    if session.agent_type not in definition.allowed_agent_types:
        raise _denied(
            session=session,
            actor=actor,
            tool_name=definition.name,
            tool_version=definition.version,
            input_params=params,
            definition=definition,
            reason=("The tool is not allowed for this agent type."),
            error_code="agent_type_not_allowed",
            triggering_message=triggering_message,
            called_at=called_at,
        )

    if not definition.read_only:
        required_capability = definition.write_capability
        allowlist_key = (
            definition.name,
            definition.version,
            required_capability,
        )
        write_allowed = (
            required_capability is not None
            and required_capability in normalized_write_capabilities
            and allowlist_key in WRITE_TOOL_CAPABILITY_ALLOWLIST
        )

        if not write_allowed:
            raise _denied(
                session=session,
                actor=actor,
                tool_name=definition.name,
                tool_version=definition.version,
                input_params=params,
                definition=definition,
                reason=("Write-capable tool access is not authorized for this tool."),
                error_code="write_tool_disabled",
                triggering_message=triggering_message,
                called_at=called_at,
                granted_write_capabilities=(normalized_write_capabilities),
            )

    context = AgentToolContext(
        actor_id=str(actor.pk),
        actor_role=getattr(actor, "role", ""),
        founder_id=str(session.founder_id),
        startup_profile_id=(
            str(session.startup_profile_id) if session.startup_profile_id is not None else None
        ),
        session_id=str(session.pk),
        agent_type=session.agent_type,
    )

    start = perf_counter()

    try:
        output = json_ready(
            definition.handler(
                context,
                params,
            )
        )
    except Exception as exc:
        duration_ms = round((perf_counter() - start) * 1000)
        error_code = exc.__class__.__name__
        error_message = str(exc) or error_code
        failure_output = {
            "error": {
                "code": error_code,
                "message": error_message[:1000],
            }
        }

        log = record_tool_call(
            session=session,
            actor=actor,
            tool_name=definition.name,
            tool_version=definition.version,
            status=AgentToolCallLog.Status.FAILED,
            input_params=params,
            authorization_context=_authorization_context(
                session=session,
                actor=actor,
                definition=definition,
                allowed=True,
                reason="authorized",
                granted_write_capabilities=(normalized_write_capabilities),
            ),
            output_snapshot=failure_output,
            duration_ms=duration_ms,
            called_at=called_at,
            triggering_message=triggering_message,
            error_code=error_code,
            error_message=error_message,
        )

        raise AgentToolExecutionError(
            (f"Tool {definition.name!r} failed with {error_code}."),
            log=log,
        ) from exc

    duration_ms = round((perf_counter() - start) * 1000)

    log = record_tool_call(
        session=session,
        actor=actor,
        tool_name=definition.name,
        tool_version=definition.version,
        status=AgentToolCallLog.Status.SUCCEEDED,
        input_params=params,
        authorization_context=_authorization_context(
            session=session,
            actor=actor,
            definition=definition,
            allowed=True,
            reason="authorized",
            granted_write_capabilities=(normalized_write_capabilities),
        ),
        output_snapshot=output,
        duration_ms=duration_ms,
        called_at=called_at,
        triggering_message=triggering_message,
    )

    return AgentToolExecutionResult(
        output=output,
        log=log,
    )


@lru_cache(maxsize=1)
def default_tool_registry() -> AgentToolRegistry:
    registry = AgentToolRegistry()

    from .tools import register_default_tools

    register_default_tools(registry)
    return registry
