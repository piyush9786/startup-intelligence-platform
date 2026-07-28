from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.assistant.models import AgentSession
from apps.assistant.services import (
    CONCIERGE_STATE_SEQUENCE,
    CONCIERGE_VERSION,
    ConciergeStateError,
    advance_concierge_session,
    create_or_get_active_session,
    get_concierge_state,
    initialize_concierge_session,
)
from apps.startups.models import (
    StartupAssessmentDraft,
    StartupProfile,
)

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
        stage=StartupProfile.Stage.IDEA,
    )


def make_concierge_session(
    *,
    founder,
    startup_profile=None,
) -> AgentSession:
    session, _created = create_or_get_active_session(
        founder=founder,
        startup_profile=startup_profile,
        agent_type=AgentSession.AgentType.CONCIERGE,
    )
    return session


def make_draft(
    *,
    owner,
    startup_profile=None,
    data=None,
) -> StartupAssessmentDraft:
    return StartupAssessmentDraft.objects.create(
        owner=owner,
        startup_profile=startup_profile,
        current_step=1,
        data=data or {},
    )


def test_initializes_owner_bound_concierge_state():
    founder = make_user("concierge-initialize")
    session = make_concierge_session(founder=founder)
    draft = make_draft(
        owner=founder,
        data={"startup_name": "Draft Startup"},
    )

    payload = initialize_concierge_session(
        session=session,
        draft=draft,
    )

    session.refresh_from_db()
    draft.refresh_from_db()

    assert payload["version"] == CONCIERGE_VERSION
    assert payload["current_state"] == "greeting"
    assert payload["state_index"] == 0
    assert payload["state_count"] == len(CONCIERGE_STATE_SEQUENCE)
    assert payload["draft"]["id"] == str(draft.pk)
    assert payload["draft"]["data"] == {
        "startup_name": "Draft Startup",
    }
    assert payload["confirmation_required"] is False
    assert payload["system_transition_required"] is False
    assert payload["is_terminal"] is False

    assert session.state["draft_id"] == str(draft.pk)
    assert draft.current_step == 1
    assert draft.data == {
        "startup_name": "Draft Startup",
    }


def test_initialization_is_idempotent_and_preserves_progress():
    founder = make_user("concierge-idempotent")
    session = make_concierge_session(founder=founder)
    draft = make_draft(owner=founder)

    initialize_concierge_session(
        session=session,
        draft=draft,
    )
    first_advance = advance_concierge_session(
        session=session,
        draft=draft,
        expected_state="greeting",
    )
    second_initialize = initialize_concierge_session(
        session=session,
        draft=draft,
    )

    assert first_advance["current_state"] == "basic_info"
    assert second_initialize["current_state"] == "basic_info"
    assert second_initialize["completed_states"] == [
        "greeting",
    ]


def test_non_concierge_session_is_rejected():
    founder = make_user("concierge-wrong-agent")
    session, _created = create_or_get_active_session(
        founder=founder,
        agent_type=AgentSession.AgentType.CHATBOT,
    )
    draft = make_draft(owner=founder)

    with pytest.raises(
        ConciergeStateError,
        match="not a concierge session",
    ):
        initialize_concierge_session(
            session=session,
            draft=draft,
        )


def test_other_founder_draft_is_rejected():
    founder = make_user("concierge-owner")
    other = make_user("concierge-other")
    session = make_concierge_session(founder=founder)
    private_draft = make_draft(owner=other)

    with pytest.raises(
        ConciergeStateError,
        match="does not belong",
    ):
        initialize_concierge_session(
            session=session,
            draft=private_draft,
        )

    session.refresh_from_db()

    assert session.state == {}


def test_startup_scoped_session_rejects_another_profile_draft():
    founder = make_user("concierge-profile-owner")
    selected_profile = make_profile(
        owner=founder,
        name="Selected Startup",
    )
    other_profile = make_profile(
        owner=founder,
        name="Other Startup",
    )
    session = make_concierge_session(
        founder=founder,
        startup_profile=selected_profile,
    )
    draft = make_draft(
        owner=founder,
        startup_profile=other_profile,
    )

    with pytest.raises(
        ConciergeStateError,
        match="startup scope",
    ):
        initialize_concierge_session(
            session=session,
            draft=draft,
        )


def test_state_machine_advances_in_declared_order():
    founder = make_user("concierge-order")
    session = make_concierge_session(founder=founder)
    draft = make_draft(owner=founder)

    payload = initialize_concierge_session(
        session=session,
        draft=draft,
    )

    expected_states = list(CONCIERGE_STATE_SEQUENCE[1:7])

    for expected_next in expected_states:
        payload = advance_concierge_session(
            session=session,
            draft=draft,
            expected_state=payload["current_state"],
        )

        assert payload["current_state"] == expected_next

    assert payload["current_state"] == "confirm_profile"
    assert payload["confirmation_required"] is True
    assert payload["allowed_fields"] == []
    assert payload["completed_states"] == list(CONCIERGE_STATE_SEQUENCE[:6])


def test_confirmation_and_system_transitions_are_explicit():
    founder = make_user("concierge-explicit")
    session = make_concierge_session(founder=founder)
    draft = make_draft(owner=founder)

    payload = initialize_concierge_session(
        session=session,
        draft=draft,
    )

    while payload["current_state"] != "confirm_profile":
        payload = advance_concierge_session(
            session=session,
            draft=draft,
            expected_state=payload["current_state"],
        )

    with pytest.raises(
        ConciergeStateError,
        match="Explicit assessment confirmation",
    ):
        advance_concierge_session(
            session=session,
            draft=draft,
            expected_state="confirm_profile",
        )

    payload = advance_concierge_session(
        session=session,
        draft=draft,
        expected_state="confirm_profile",
        confirmed=True,
    )

    assert payload["current_state"] == "generating_plan"
    assert payload["confirmation_required"] is False
    assert payload["system_transition_required"] is True

    with pytest.raises(
        ConciergeStateError,
        match="deterministic generation workflow",
    ):
        advance_concierge_session(
            session=session,
            draft=draft,
            expected_state="generating_plan",
        )

    payload = advance_concierge_session(
        session=session,
        draft=draft,
        expected_state="generating_plan",
        system_transition=True,
    )

    assert payload["current_state"] == "plan_ready"
    assert payload["is_terminal"] is True


def test_stale_expected_state_is_rejected_without_transition():
    founder = make_user("concierge-stale")
    session = make_concierge_session(founder=founder)
    draft = make_draft(owner=founder)

    initialize_concierge_session(
        session=session,
        draft=draft,
    )
    advance_concierge_session(
        session=session,
        draft=draft,
        expected_state="greeting",
    )

    with pytest.raises(
        ConciergeStateError,
        match="changed before this transition",
    ):
        advance_concierge_session(
            session=session,
            draft=draft,
            expected_state="greeting",
        )

    session.refresh_from_db()

    assert session.state["current_state"] == "basic_info"
    assert session.state["completed_states"] == [
        "greeting",
    ]


def test_terminal_state_cannot_advance():
    founder = make_user("concierge-terminal")
    session = make_concierge_session(founder=founder)
    draft = make_draft(owner=founder)

    initialize_concierge_session(
        session=session,
        draft=draft,
    )

    for state in CONCIERGE_STATE_SEQUENCE[:-1]:
        kwargs = {}

        if state == "confirm_profile":
            kwargs["confirmed"] = True

        if state == "generating_plan":
            kwargs["system_transition"] = True

        advance_concierge_session(
            session=session,
            draft=draft,
            expected_state=state,
            **kwargs,
        )

    with pytest.raises(
        ConciergeStateError,
        match="already complete",
    ):
        advance_concierge_session(
            session=session,
            draft=draft,
            expected_state="plan_ready",
        )


def test_submitted_draft_cannot_start_concierge_workflow():
    founder = make_user("concierge-submitted")
    session = make_concierge_session(founder=founder)
    draft = make_draft(owner=founder)
    draft.status = StartupAssessmentDraft.Status.SUBMITTED
    draft.save(update_fields=["status", "updated_at"])

    with pytest.raises(
        ConciergeStateError,
        match="Only open assessment drafts",
    ):
        initialize_concierge_session(
            session=session,
            draft=draft,
        )


def test_get_state_rejects_draft_rebinding():
    founder = make_user("concierge-rebind")
    session = make_concierge_session(founder=founder)
    first_draft = make_draft(owner=founder)

    initialize_concierge_session(
        session=session,
        draft=first_draft,
    )

    first_draft.status = StartupAssessmentDraft.Status.SUBMITTED
    first_draft.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    second_draft = make_draft(owner=founder)
    session.refresh_from_db()

    with pytest.raises(
        ConciergeStateError,
        match="bound to another assessment draft",
    ):
        get_concierge_state(
            session=session,
            draft=second_draft,
        )
