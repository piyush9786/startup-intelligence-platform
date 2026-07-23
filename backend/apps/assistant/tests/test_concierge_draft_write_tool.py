from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.assistant.models import (
    AgentSession,
    AgentToolCallLog,
)
from apps.assistant.services import (
    AgentToolAuthorizationError,
    AgentToolDefinition,
    AgentToolExecutionError,
    AgentToolRegistry,
    advance_concierge_session,
    canonical_sha256,
    create_or_get_active_session,
    execute_registered_tool,
    initialize_concierge_session,
)
from apps.startups.models import (
    StartupAssessmentDraft,
    StartupProfile,
)

pytestmark = pytest.mark.django_db

TOOL_NAME = "update_startup_assessment_draft"
WRITE_CAPABILITY = "assessment_draft_update"


def make_user(username: str):
    user_model = get_user_model()

    return user_model.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="test-password",
        role=user_model.Role.FOUNDER,
    )


def make_profile(
    *,
    owner,
    name: str,
) -> StartupProfile:
    return StartupProfile.objects.create(
        owner=owner,
        startup_name=name,
        stage=StartupProfile.Stage.IDEA,
    )


def make_draft(
    *,
    owner,
    startup_profile=None,
    current_step=1,
    data=None,
) -> StartupAssessmentDraft:
    return StartupAssessmentDraft.objects.create(
        owner=owner,
        startup_profile=startup_profile,
        current_step=current_step,
        data=data or {},
    )


def make_session(
    *,
    founder,
    agent_type=AgentSession.AgentType.CONCIERGE,
    startup_profile=None,
) -> AgentSession:
    session, _created = create_or_get_active_session(
        founder=founder,
        startup_profile=startup_profile,
        agent_type=agent_type,
    )
    return session


def bind_session(
    *,
    session,
    draft,
    target_state="basic_info",
):
    payload = initialize_concierge_session(
        session=session,
        draft=draft,
    )

    while payload["current_state"] != target_state:
        payload = advance_concierge_session(
            session=session,
            draft=draft,
            expected_state=payload["current_state"],
        )

    session.refresh_from_db()
    draft.refresh_from_db()

    return payload


def execute_update(
    *,
    session,
    founder,
    draft,
    updates,
    write_capabilities=None,
):
    return execute_registered_tool(
        session=session,
        actor=founder,
        tool_name=TOOL_NAME,
        input_params={
            "draft_id": str(draft.pk),
            "updates": updates,
        },
        write_capabilities=write_capabilities,
    )


def test_draft_write_requires_explicit_capability():
    founder = make_user("concierge-write-capability")
    session = make_session(founder=founder)
    draft = make_draft(owner=founder)
    bind_session(
        session=session,
        draft=draft,
    )

    with pytest.raises(
        AgentToolAuthorizationError,
        match="not authorized",
    ) as error:
        execute_update(
            session=session,
            founder=founder,
            draft=draft,
            updates={
                "startup_name": "Blocked Startup",
            },
        )

    draft.refresh_from_db()

    assert draft.data == {}
    assert error.value.log.status == (AgentToolCallLog.Status.DENIED)
    assert error.value.log.error_code == ("write_tool_disabled")
    assert error.value.log.authorization_context["tool_write_capability"] == WRITE_CAPABILITY
    assert error.value.log.authorization_context["granted_write_capabilities"] == []


def test_chatbot_cannot_use_draft_write_tool():
    founder = make_user("chatbot-write-blocked")
    session = make_session(
        founder=founder,
        agent_type=AgentSession.AgentType.CHATBOT,
    )
    draft = make_draft(owner=founder)

    with pytest.raises(
        AgentToolAuthorizationError,
        match="agent type",
    ) as error:
        execute_update(
            session=session,
            founder=founder,
            draft=draft,
            updates={
                "startup_name": "Blocked Startup",
            },
            write_capabilities={
                WRITE_CAPABILITY,
            },
        )

    assert error.value.log.error_code == ("agent_type_not_allowed")
    assert draft.data == {}


def test_unrelated_write_tool_remains_denied():
    founder = make_user("unrelated-write-blocked")
    session = make_session(founder=founder)
    registry = AgentToolRegistry()
    registry.register(
        AgentToolDefinition(
            name="submit_profile_field",
            version="v1",
            description=("An unrelated write-capable test tool."),
            handler=lambda _context, _params: {
                "written": True,
            },
            allowed_agent_types=frozenset(
                {
                    AgentSession.AgentType.CONCIERGE,
                }
            ),
            read_only=False,
            write_capability=WRITE_CAPABILITY,
        )
    )

    with pytest.raises(
        AgentToolAuthorizationError,
        match="not authorized",
    ) as error:
        execute_registered_tool(
            session=session,
            actor=founder,
            tool_name="submit_profile_field",
            registry=registry,
            write_capabilities={
                WRITE_CAPABILITY,
            },
        )

    assert error.value.log.error_code == ("write_tool_disabled")


def test_allowed_update_merges_and_is_audited():
    founder = make_user("concierge-write-success")
    session = make_session(founder=founder)
    draft = make_draft(
        owner=founder,
        data={
            "startup_name": "Existing Startup",
            "legal_name": "Old Legal Name",
        },
    )
    bind_session(
        session=session,
        draft=draft,
        target_state="location_legal",
    )

    result = execute_update(
        session=session,
        founder=founder,
        draft=draft,
        updates={
            "legal_name": "New Legal Name",
            "state": "Karnataka",
        },
        write_capabilities={
            WRITE_CAPABILITY,
        },
    )

    draft.refresh_from_db()

    assert draft.status == (StartupAssessmentDraft.Status.DRAFT)
    assert draft.current_step == 2
    assert draft.data["startup_name"] == ("Existing Startup")
    assert draft.data["legal_name"] == ("New Legal Name")
    assert draft.data["state"] == "Karnataka"
    assert StartupProfile.objects.count() == 0

    assert result.output == {
        "draft_id": str(draft.pk),
        "status": "draft",
        "concierge_state": "location_legal",
        "assessment_step": 2,
        "previous_step": 1,
        "current_step": 2,
        "changed_fields": [
            "legal_name",
            "state",
        ],
        "previous_values": {
            "legal_name": "Old Legal Name",
            "state": None,
        },
        "new_values": {
            "legal_name": "New Legal Name",
            "state": "Karnataka",
        },
    }

    log = result.log

    assert log.status == (AgentToolCallLog.Status.SUCCEEDED)
    assert log.tool_name == TOOL_NAME
    assert log.tool_version == "v1"
    assert log.output_hash == canonical_sha256(result.output)
    assert log.authorization_context["tool_write_capability"] == WRITE_CAPABILITY
    assert log.authorization_context["granted_write_capabilities"] == [WRITE_CAPABILITY]
    assert log.authorization_context["allowed"] is True


def test_current_state_rejects_unrelated_fields():
    founder = make_user("concierge-field-blocked")
    session = make_session(founder=founder)
    draft = make_draft(
        owner=founder,
        data={
            "legal_name": "Unchanged Legal Name",
        },
    )
    bind_session(
        session=session,
        draft=draft,
        target_state="location_legal",
    )

    with pytest.raises(
        AgentToolExecutionError,
        match="AgentToolInputError",
    ) as error:
        execute_update(
            session=session,
            founder=founder,
            draft=draft,
            updates={
                "funding_required": "100000",
            },
            write_capabilities={
                WRITE_CAPABILITY,
            },
        )

    draft.refresh_from_db()

    assert draft.data == {
        "legal_name": "Unchanged Legal Name",
    }
    assert error.value.log.status == (AgentToolCallLog.Status.FAILED)
    assert error.value.log.error_code == ("AgentToolInputError")


def test_field_values_use_assessment_validation():
    founder = make_user("concierge-value-validation")
    session = make_session(founder=founder)
    draft = make_draft(
        owner=founder,
        data={
            "startup_name": "Validated Startup",
            "stage": "idea",
        },
    )
    bind_session(
        session=session,
        draft=draft,
        target_state="basic_info",
    )

    with pytest.raises(
        AgentToolExecutionError,
        match="AgentToolInputError",
    ) as error:
        execute_update(
            session=session,
            founder=founder,
            draft=draft,
            updates={
                "stage": "not-a-real-stage",
            },
            write_capabilities={
                WRITE_CAPABILITY,
            },
        )

    draft.refresh_from_db()

    assert draft.data["stage"] == "idea"
    assert error.value.log.status == (AgentToolCallLog.Status.FAILED)
    assert "stage" in error.value.log.error_message


def test_other_founder_draft_is_not_available():
    founder = make_user("concierge-private-founder")
    other = make_user("concierge-private-other")
    session = make_session(founder=founder)
    own_draft = make_draft(owner=founder)
    private_draft = make_draft(owner=other)
    bind_session(
        session=session,
        draft=own_draft,
        target_state="basic_info",
    )

    with pytest.raises(
        AgentToolExecutionError,
        match="AgentToolInputError",
    ):
        execute_update(
            session=session,
            founder=founder,
            draft=private_draft,
            updates={
                "startup_name": "Private Mutation",
            },
            write_capabilities={
                WRITE_CAPABILITY,
            },
        )

    private_draft.refresh_from_db()

    assert private_draft.data == {}


def test_session_cannot_rebind_to_another_draft():
    founder = make_user("concierge-write-rebind")
    session = make_session(founder=founder)
    first_draft = make_draft(owner=founder)
    bind_session(
        session=session,
        draft=first_draft,
        target_state="basic_info",
    )

    first_draft.status = StartupAssessmentDraft.Status.SUBMITTED
    first_draft.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )
    second_draft = make_draft(owner=founder)

    with pytest.raises(
        AgentToolExecutionError,
        match="ConciergeStateError",
    ):
        execute_update(
            session=session,
            founder=founder,
            draft=second_draft,
            updates={
                "startup_name": "Rebound Startup",
            },
            write_capabilities={
                WRITE_CAPABILITY,
            },
        )

    second_draft.refresh_from_db()

    assert second_draft.data == {}


def test_submitted_draft_cannot_be_updated():
    founder = make_user("concierge-submitted-write")
    session = make_session(founder=founder)
    draft = make_draft(owner=founder)
    bind_session(
        session=session,
        draft=draft,
        target_state="basic_info",
    )

    draft.status = StartupAssessmentDraft.Status.SUBMITTED
    draft.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    with pytest.raises(
        AgentToolExecutionError,
        match="ConciergeStateError",
    ):
        execute_update(
            session=session,
            founder=founder,
            draft=draft,
            updates={
                "startup_name": "Submitted Mutation",
            },
            write_capabilities={
                WRITE_CAPABILITY,
            },
        )

    draft.refresh_from_db()

    assert draft.data == {}
