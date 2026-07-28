from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.assistant.models import (
    AgentClaimReference,
    AgentMessage,
    AgentSession,
    AgentToolCallLog,
)
from apps.assistant.services import (
    AgentSessionError,
    AgentToolAuthorizationError,
    AgentToolDefinition,
    AgentToolExecutionError,
    AgentToolRegistry,
    AgentToolRegistryError,
    AgentTurnLimitExceeded,
    add_claim_reference,
    append_agent_message,
    canonical_sha256,
    close_agent_session,
    create_or_get_active_session,
    default_tool_registry,
    execute_registered_tool,
)
from apps.startups.models import StartupProfile

pytestmark = pytest.mark.django_db


def make_user(
    username: str,
    *,
    role: str | None = None,
):
    user_model = get_user_model()

    return user_model.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="test-password",
        role=role or user_model.Role.FOUNDER,
    )


def make_profile(
    *,
    owner,
    name: str,
) -> StartupProfile:
    return StartupProfile.objects.create(
        owner=owner,
        startup_name=name,
        stage=StartupProfile.Stage.MVP,
    )


def test_active_session_is_owner_scoped_and_idempotent():
    founder = make_user("agent-session-owner")
    profile = make_profile(
        owner=founder,
        name="Agent Session Startup",
    )

    first, first_created = create_or_get_active_session(
        founder=founder,
        startup_profile=profile,
        agent_type=AgentSession.AgentType.CHATBOT,
        state={"page": "dashboard"},
        context={"source": "test"},
    )
    second, second_created = create_or_get_active_session(
        founder=founder,
        startup_profile=profile,
        agent_type=AgentSession.AgentType.CHATBOT,
    )

    assert first_created is True
    assert second_created is False
    assert second.pk == first.pk
    assert first.scope_key == str(profile.pk)
    assert first.state == {"page": "dashboard"}
    assert first.context == {"source": "test"}
    assert AgentSession.objects.count() == 1


def test_global_active_session_has_database_uniqueness():
    founder = make_user("agent-global-owner")

    first = AgentSession.objects.create(
        founder=founder,
        agent_type=AgentSession.AgentType.CHATBOT,
    )

    assert first.scope_key == AgentSession.GLOBAL_SCOPE_KEY

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            AgentSession.objects.create(
                founder=founder,
                agent_type=AgentSession.AgentType.CHATBOT,
            )


def test_non_owner_profile_cannot_enter_session_scope():
    founder = make_user("agent-private-founder")
    other_founder = make_user("agent-private-other")
    private_profile = make_profile(
        owner=other_founder,
        name="Private Agent Startup",
    )

    with pytest.raises(
        AgentSessionError,
        match="does not belong",
    ):
        create_or_get_active_session(
            founder=founder,
            startup_profile=private_profile,
            agent_type=AgentSession.AgentType.CHATBOT,
        )

    assert AgentSession.objects.count() == 0


def test_non_founder_role_cannot_create_founder_session():
    user_model = get_user_model()
    reviewer = make_user(
        "agent-reviewer",
        role=user_model.Role.REVIEWER,
    )

    with pytest.raises(
        AgentSessionError,
        match="Founder access",
    ):
        create_or_get_active_session(
            founder=reviewer,
            agent_type=AgentSession.AgentType.CHATBOT,
        )


def test_closed_session_allows_new_active_session():
    founder = make_user("agent-replacement-owner")

    first, _created = create_or_get_active_session(
        founder=founder,
        agent_type=AgentSession.AgentType.CHATBOT,
    )

    closed = close_agent_session(
        session=first,
    )

    second, created = create_or_get_active_session(
        founder=founder,
        agent_type=AgentSession.AgentType.CHATBOT,
    )

    assert closed.status == AgentSession.Status.COMPLETED
    assert closed.completed_at is not None
    assert created is True
    assert second.pk != first.pk
    assert second.status == AgentSession.Status.ACTIVE


def test_messages_are_ordered_and_user_turns_are_bounded():
    founder = make_user("agent-turn-owner")
    session, _created = create_or_get_active_session(
        founder=founder,
        agent_type=AgentSession.AgentType.CHATBOT,
        max_turns=1,
    )

    user_message = append_agent_message(
        session=session,
        role=AgentMessage.Role.USER,
        content="What should I do next?",
    )
    agent_message = append_agent_message(
        session=session,
        role=AgentMessage.Role.AGENT,
        content="I will check your persisted profile.",
    )

    session.refresh_from_db()

    assert user_message.sequence_number == 1
    assert agent_message.sequence_number == 2
    assert session.turn_count == 1

    with pytest.raises(
        AgentTurnLimitExceeded,
        match="maximum",
    ):
        append_agent_message(
            session=session,
            role=AgentMessage.Role.USER,
            content="One more question.",
        )

    session.refresh_from_db()

    assert session.turn_count == 1
    assert session.messages.count() == 2


def test_messages_cannot_be_appended_to_closed_session():
    founder = make_user("agent-closed-message-owner")
    session, _created = create_or_get_active_session(
        founder=founder,
        agent_type=AgentSession.AgentType.CHATBOT,
    )
    close_agent_session(session=session)

    with pytest.raises(
        AgentSessionError,
        match="closed session",
    ):
        append_agent_message(
            session=session,
            role=AgentMessage.Role.USER,
            content="This should not be stored.",
        )


def test_default_registry_contains_bounded_founder_tools():
    registry = default_tool_registry()
    definitions = registry.list()

    assert [definition.name for definition in definitions] == [
        "get_startup_profile",
        "update_startup_assessment_draft",
    ]

    profile_tool = definitions[0]
    draft_update_tool = definitions[1]

    assert profile_tool.version == "v1"
    assert profile_tool.read_only is True
    assert profile_tool.write_capability is None
    assert profile_tool.allowed_agent_types == frozenset(AgentSession.AgentType.values)

    assert draft_update_tool.version == "v1"
    assert draft_update_tool.read_only is False
    assert draft_update_tool.write_capability == "assessment_draft_update"
    assert draft_update_tool.allowed_agent_types == frozenset(
        {
            AgentSession.AgentType.CONCIERGE,
        }
    )


def test_registry_rejects_duplicate_tool_names():
    registry = AgentToolRegistry()

    definition = AgentToolDefinition(
        name="test_read_tool",
        version="v1",
        description="Read deterministic test data.",
        handler=lambda _context, _params: {"ok": True},
        allowed_agent_types=frozenset(
            {
                AgentSession.AgentType.CHATBOT,
            }
        ),
        read_only=True,
    )

    registry.register(definition)

    with pytest.raises(
        AgentToolRegistryError,
        match="already registered",
    ):
        registry.register(definition)


def test_profile_tool_persists_auditable_success_log():
    founder = make_user("agent-tool-owner")
    profile = make_profile(
        owner=founder,
        name="Agent Tool Startup",
    )
    session, _created = create_or_get_active_session(
        founder=founder,
        startup_profile=profile,
        agent_type=AgentSession.AgentType.CHATBOT,
    )
    user_message = append_agent_message(
        session=session,
        role=AgentMessage.Role.USER,
        content="What startup profile are you using?",
    )

    result = execute_registered_tool(
        session=session,
        actor=founder,
        tool_name="get_startup_profile",
        input_params={},
        triggering_message=user_message,
    )

    log = result.log

    assert result.output["startup_profile"]["startup_name"] == "Agent Tool Startup"
    assert result.output["scope"] == "startup_profile"
    assert log.status == AgentToolCallLog.Status.SUCCEEDED
    assert log.tool_name == "get_startup_profile"
    assert log.tool_version == "v1"
    assert log.triggering_message == user_message
    assert log.actor == founder
    assert log.authorization_context["allowed"] is True
    assert log.authorization_context["session_founder_id"] == str(founder.pk)
    assert log.authorization_context["startup_profile_id"] == str(profile.pk)
    assert log.output_hash == canonical_sha256(result.output)
    assert len(log.output_hash) == 64
    assert log.error_code == ""
    assert log.error_message == ""


def test_global_profile_tool_returns_explicit_null_snapshot():
    founder = make_user("agent-global-tool-owner")
    session, _created = create_or_get_active_session(
        founder=founder,
        agent_type=AgentSession.AgentType.CONCIERGE,
    )

    result = execute_registered_tool(
        session=session,
        actor=founder,
        tool_name="get_startup_profile",
    )

    assert result.output == {
        "startup_profile": None,
        "scope": "global",
    }
    assert result.log.output_hash == canonical_sha256(result.output)


def test_non_owner_tool_execution_is_denied_and_logged():
    founder = make_user("agent-auth-owner")
    attacker = make_user("agent-auth-attacker")
    session, _created = create_or_get_active_session(
        founder=founder,
        agent_type=AgentSession.AgentType.CHATBOT,
    )

    with pytest.raises(
        AgentToolAuthorizationError,
        match="does not own",
    ) as error:
        execute_registered_tool(
            session=session,
            actor=attacker,
            tool_name="get_startup_profile",
        )

    log = error.value.log

    assert log.status == AgentToolCallLog.Status.DENIED
    assert log.actor == attacker
    assert log.error_code == "session_owner_required"
    assert log.authorization_context["allowed"] is False
    assert log.output_snapshot["denied"] is True


def test_unregistered_tool_is_denied_and_logged():
    founder = make_user("agent-unregistered-owner")
    session, _created = create_or_get_active_session(
        founder=founder,
        agent_type=AgentSession.AgentType.CHATBOT,
    )

    with pytest.raises(
        AgentToolAuthorizationError,
        match="not registered",
    ) as error:
        execute_registered_tool(
            session=session,
            actor=founder,
            tool_name="read_raw_database",
        )

    log = error.value.log

    assert log.status == AgentToolCallLog.Status.DENIED
    assert log.tool_version == "unregistered"
    assert log.error_code == "tool_not_registered"


def test_write_capable_tool_is_denied_in_foundation():
    founder = make_user("agent-write-denied-owner")
    session, _created = create_or_get_active_session(
        founder=founder,
        agent_type=AgentSession.AgentType.CONCIERGE,
    )
    registry = AgentToolRegistry()
    registry.register(
        AgentToolDefinition(
            name="submit_profile_field",
            version="v1",
            description="Attempt a draft write.",
            handler=lambda _context, _params: {"written": True},
            allowed_agent_types=frozenset(
                {
                    AgentSession.AgentType.CONCIERGE,
                }
            ),
            read_only=False,
        )
    )

    with pytest.raises(
        AgentToolAuthorizationError,
        match="Write-capable",
    ) as error:
        execute_registered_tool(
            session=session,
            actor=founder,
            tool_name="submit_profile_field",
            registry=registry,
        )

    assert error.value.log.error_code == "write_tool_disabled"
    assert error.value.log.status == AgentToolCallLog.Status.DENIED


def test_tool_failure_is_hashed_and_logged():
    founder = make_user("agent-failed-tool-owner")
    session, _created = create_or_get_active_session(
        founder=founder,
        agent_type=AgentSession.AgentType.CHATBOT,
    )
    registry = AgentToolRegistry()

    def failing_handler(_context, _params):
        raise RuntimeError("Deterministic tool failed.")

    registry.register(
        AgentToolDefinition(
            name="test_failing_tool",
            version="v3",
            description="Fail for audit testing.",
            handler=failing_handler,
            allowed_agent_types=frozenset(
                {
                    AgentSession.AgentType.CHATBOT,
                }
            ),
            read_only=True,
        )
    )

    with pytest.raises(
        AgentToolExecutionError,
        match="failed",
    ) as error:
        execute_registered_tool(
            session=session,
            actor=founder,
            tool_name="test_failing_tool",
            registry=registry,
        )

    log = error.value.log

    assert log.status == AgentToolCallLog.Status.FAILED
    assert log.error_code == "RuntimeError"
    assert log.output_hash == canonical_sha256(log.output_snapshot)


def test_claim_reference_links_agent_claim_to_tool_output():
    founder = make_user("agent-claim-owner")
    profile = make_profile(
        owner=founder,
        name="Claim Reference Startup",
    )
    session, _created = create_or_get_active_session(
        founder=founder,
        startup_profile=profile,
        agent_type=AgentSession.AgentType.CHATBOT,
    )
    user_message = append_agent_message(
        session=session,
        role=AgentMessage.Role.USER,
        content="Which startup is selected?",
    )
    result = execute_registered_tool(
        session=session,
        actor=founder,
        tool_name="get_startup_profile",
        triggering_message=user_message,
    )
    agent_message = append_agent_message(
        session=session,
        role=AgentMessage.Role.AGENT,
        content=("The selected startup is Claim Reference Startup."),
    )

    reference = add_claim_reference(
        message=agent_message,
        tool_call=result.log,
        claim_key="selected-startup-name",
        claim_text=("The selected startup is Claim Reference Startup."),
        output_path="startup_profile.startup_name",
    )

    assert reference.message == agent_message
    assert reference.tool_call == result.log
    assert reference.output_path == "startup_profile.startup_name"
    assert AgentClaimReference.objects.count() == 1


def test_cross_session_claim_reference_is_rejected():
    founder = make_user("agent-cross-claim-owner")
    first_session, _created = create_or_get_active_session(
        founder=founder,
        agent_type=AgentSession.AgentType.CHATBOT,
    )
    second_session, _created = create_or_get_active_session(
        founder=founder,
        agent_type=AgentSession.AgentType.CONCIERGE,
    )

    tool_result = execute_registered_tool(
        session=first_session,
        actor=founder,
        tool_name="get_startup_profile",
    )
    second_message = append_agent_message(
        session=second_session,
        role=AgentMessage.Role.AGENT,
        content="Unsupported cross-session claim.",
    )

    with pytest.raises(
        ValidationError,
        match="same agent session",
    ):
        add_claim_reference(
            message=second_message,
            tool_call=tool_result.log,
            claim_key="cross-session",
            claim_text="Unsupported cross-session claim.",
            output_path="startup_profile",
        )


def test_messages_logs_and_claims_are_append_only():
    founder = make_user("agent-immutable-owner")
    session, _created = create_or_get_active_session(
        founder=founder,
        agent_type=AgentSession.AgentType.CHATBOT,
    )
    user_message = append_agent_message(
        session=session,
        role=AgentMessage.Role.USER,
        content="Read my profile.",
    )
    result = execute_registered_tool(
        session=session,
        actor=founder,
        tool_name="get_startup_profile",
        triggering_message=user_message,
    )
    agent_message = append_agent_message(
        session=session,
        role=AgentMessage.Role.AGENT,
        content="No profile is selected.",
    )
    reference = add_claim_reference(
        message=agent_message,
        tool_call=result.log,
        claim_key="profile-state",
        claim_text="No profile is selected.",
        output_path="startup_profile",
    )

    user_message.content = "Mutated message"

    with pytest.raises(
        ValidationError,
        match="append-only",
    ):
        user_message.save()

    result.log.output_snapshot = {"changed": True}

    with pytest.raises(
        ValidationError,
        match="append-only",
    ):
        result.log.save()

    reference.claim_text = "Mutated claim"

    with pytest.raises(
        ValidationError,
        match="append-only",
    ):
        reference.save()

    with pytest.raises(
        ValidationError,
        match="append-only",
    ):
        result.log.delete()
