from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.assistant.models import (
    AgentSession,
    AgentToolCallLog,
)
from apps.assistant.services import (
    advance_concierge_session,
    create_or_get_active_session,
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


def make_draft(
    *,
    owner,
    startup_profile=None,
    status_value=StartupAssessmentDraft.Status.DRAFT,
    data=None,
) -> StartupAssessmentDraft:
    return StartupAssessmentDraft.objects.create(
        owner=owner,
        startup_profile=startup_profile,
        status=status_value,
        current_step=1,
        data=data or {},
    )


def authenticated_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def current_url() -> str:
    return reverse("assistant-concierge-current")


def update_url() -> str:
    return reverse("assistant-concierge-draft-update")


def transition_url() -> str:
    return reverse("assistant-concierge-transition")


def make_bound_session(
    *,
    founder,
    draft,
    startup_profile=None,
    target_state="greeting",
) -> AgentSession:
    session, _created = create_or_get_active_session(
        founder=founder,
        startup_profile=startup_profile,
        agent_type=AgentSession.AgentType.CONCIERGE,
    )
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

    return session


def test_current_requires_authentication():
    response = APIClient().get(current_url())

    assert response.status_code == (status.HTTP_401_UNAUTHORIZED)


@pytest.mark.parametrize(
    "role",
    [
        "consultant",
        "incubator_manager",
        "reviewer",
        "admin",
    ],
)
def test_concierge_endpoints_are_founder_only(role):
    user = make_user(
        f"concierge-role-{role}",
        role=role,
    )
    draft = make_draft(owner=user)
    client = authenticated_client(user)

    current_response = client.get(current_url())
    update_response = client.post(
        update_url(),
        {
            "draft_id": str(draft.pk),
            "updates": {
                "startup_name": "Blocked Startup",
            },
        },
        format="json",
    )
    transition_response = client.post(
        transition_url(),
        {
            "draft_id": str(draft.pk),
            "expected_state": "greeting",
        },
        format="json",
    )

    assert current_response.status_code == (status.HTTP_403_FORBIDDEN)
    assert update_response.status_code == (status.HTTP_403_FORBIDDEN)
    assert transition_response.status_code == (status.HTTP_403_FORBIDDEN)
    assert AgentSession.objects.count() == 0
    assert AgentToolCallLog.objects.count() == 0


def test_current_initializes_and_resumes_open_draft():
    founder = make_user("concierge-api-current")
    draft = make_draft(
        owner=founder,
        data={
            "startup_name": "Current Startup",
        },
    )
    client = authenticated_client(founder)

    first_response = client.get(current_url())
    second_response = client.get(current_url())

    assert first_response.status_code == (status.HTTP_200_OK)
    assert second_response.status_code == (status.HTTP_200_OK)
    assert first_response.data["created"] is True
    assert second_response.data["created"] is False
    assert first_response.data["current_state"] == ("greeting")
    assert first_response.data["draft"]["id"] == str(draft.pk)
    assert first_response.data["draft"]["data"] == {
        "startup_name": "Current Startup",
    }
    assert (
        AgentSession.objects.filter(
            founder=founder,
            agent_type=AgentSession.AgentType.CONCIERGE,
            status=AgentSession.Status.ACTIVE,
        ).count()
        == 1
    )


def test_current_returns_not_found_without_open_draft():
    founder = make_user("concierge-api-no-draft")

    response = authenticated_client(founder).get(current_url())

    assert response.status_code == (status.HTTP_404_NOT_FOUND)
    assert AgentSession.objects.count() == 0


def test_current_rejects_another_founders_profile():
    founder = make_user("concierge-api-profile-founder")
    other = make_user("concierge-api-profile-other")
    profile = make_profile(
        owner=other,
        name="Private Startup",
    )

    response = authenticated_client(founder).get(
        current_url(),
        {
            "startup_profile_id": str(profile.pk),
        },
    )

    assert response.status_code == (status.HTTP_404_NOT_FOUND)
    assert AgentSession.objects.count() == 0


def test_transition_requires_expected_state():
    founder = make_user("concierge-api-transition-required")
    draft = make_draft(owner=founder)

    response = authenticated_client(founder).post(
        transition_url(),
        {
            "draft_id": str(draft.pk),
        },
        format="json",
    )

    assert response.status_code == (status.HTTP_400_BAD_REQUEST)
    assert "expected_state" in response.data


def test_transition_advances_in_declared_order():
    founder = make_user("concierge-api-transition")
    draft = make_draft(owner=founder)
    client = authenticated_client(founder)

    response = client.post(
        transition_url(),
        {
            "draft_id": str(draft.pk),
            "expected_state": "greeting",
        },
        format="json",
    )

    assert response.status_code == (status.HTTP_200_OK)
    assert response.data["current_state"] == ("basic_info")
    assert response.data["completed_states"] == [
        "greeting",
    ]


def test_stale_transition_returns_conflict():
    founder = make_user("concierge-api-stale")
    draft = make_draft(owner=founder)
    client = authenticated_client(founder)

    first_response = client.post(
        transition_url(),
        {
            "draft_id": str(draft.pk),
            "expected_state": "greeting",
        },
        format="json",
    )
    stale_response = client.post(
        transition_url(),
        {
            "draft_id": str(draft.pk),
            "expected_state": "greeting",
        },
        format="json",
    )

    assert first_response.status_code == (status.HTTP_200_OK)
    assert stale_response.status_code == (status.HTTP_409_CONFLICT)
    assert stale_response.data["code"] == ("concierge_state_conflict")


def test_public_transition_rejects_system_transition():
    founder = make_user("concierge-api-system-transition")
    draft = make_draft(owner=founder)

    response = authenticated_client(founder).post(
        transition_url(),
        {
            "draft_id": str(draft.pk),
            "expected_state": "greeting",
            "system_transition": True,
        },
        format="json",
    )

    assert response.status_code == (status.HTTP_400_BAD_REQUEST)
    assert response.data["system_transition"] == [
        "This field is not allowed.",
    ]


def test_confirmation_is_explicit():
    founder = make_user("concierge-api-confirm")
    draft = make_draft(owner=founder)
    make_bound_session(
        founder=founder,
        draft=draft,
        target_state="confirm_profile",
    )
    client = authenticated_client(founder)

    missing_confirmation = client.post(
        transition_url(),
        {
            "draft_id": str(draft.pk),
            "expected_state": "confirm_profile",
        },
        format="json",
    )
    confirmed = client.post(
        transition_url(),
        {
            "draft_id": str(draft.pk),
            "expected_state": "confirm_profile",
            "confirmed": True,
        },
        format="json",
    )

    assert missing_confirmation.status_code == (status.HTTP_409_CONFLICT)
    assert confirmed.status_code == (status.HTTP_200_OK)
    assert confirmed.data["current_state"] == ("generating_plan")
    assert confirmed.data["system_transition_required"] is True


def test_update_executes_bounded_audited_tool():
    founder = make_user("concierge-api-update")
    draft = make_draft(
        owner=founder,
        data={
            "startup_name": "Original Startup",
            "stage": "idea",
        },
    )
    client = authenticated_client(founder)

    transition_response = client.post(
        transition_url(),
        {
            "draft_id": str(draft.pk),
            "expected_state": "greeting",
        },
        format="json",
    )
    update_response = client.post(
        update_url(),
        {
            "draft_id": str(draft.pk),
            "updates": {
                "startup_name": "Updated Startup",
                "stage": "prototype",
            },
        },
        format="json",
    )

    assert transition_response.status_code == (status.HTTP_200_OK)
    assert update_response.status_code == (status.HTTP_200_OK)
    assert update_response.data["current_state"] == ("basic_info")
    assert update_response.data["update"]["changed_fields"] == [
        "stage",
        "startup_name",
    ]
    assert update_response.data["update"]["previous_values"] == {
        "stage": "idea",
        "startup_name": "Original Startup",
    }
    assert update_response.data["update"]["new_values"] == {
        "stage": "prototype",
        "startup_name": "Updated Startup",
    }

    draft.refresh_from_db()

    assert draft.data["startup_name"] == ("Updated Startup")
    assert draft.data["stage"] == "prototype"
    assert StartupProfile.objects.count() == 0

    log = AgentToolCallLog.objects.get()

    assert log.tool_name == ("update_startup_assessment_draft")
    assert log.tool_version == "v1"
    assert log.status == (AgentToolCallLog.Status.SUCCEEDED)
    assert log.authorization_context["granted_write_capabilities"] == [
        "assessment_draft_update",
    ]


def test_update_rejects_fields_outside_current_state():
    founder = make_user("concierge-api-update-fields")
    draft = make_draft(owner=founder)
    client = authenticated_client(founder)

    client.post(
        transition_url(),
        {
            "draft_id": str(draft.pk),
            "expected_state": "greeting",
        },
        format="json",
    )
    response = client.post(
        update_url(),
        {
            "draft_id": str(draft.pk),
            "updates": {
                "funding_required": "100000",
            },
        },
        format="json",
    )

    assert response.status_code == (status.HTTP_400_BAD_REQUEST)
    assert response.data["code"] == ("AgentToolInputError")

    draft.refresh_from_db()

    assert draft.data == {}


def test_update_cannot_access_another_founders_draft():
    founder = make_user("concierge-api-private-founder")
    other = make_user("concierge-api-private-other")
    own_draft = make_draft(owner=founder)
    private_draft = make_draft(owner=other)
    client = authenticated_client(founder)

    client.get(current_url())

    response = client.post(
        update_url(),
        {
            "draft_id": str(private_draft.pk),
            "updates": {
                "startup_name": "Private Mutation",
            },
        },
        format="json",
    )

    assert response.status_code == (status.HTTP_404_NOT_FOUND)

    private_draft.refresh_from_db()
    own_draft.refresh_from_db()

    assert private_draft.data == {}
    assert own_draft.data == {}


def test_submitted_generating_session_can_be_read():
    founder = make_user("concierge-api-submitted-resume")
    draft = make_draft(owner=founder)
    session = make_bound_session(
        founder=founder,
        draft=draft,
        target_state="confirm_profile",
    )
    advance_concierge_session(
        session=session,
        draft=draft,
        expected_state="confirm_profile",
        confirmed=True,
    )

    draft.status = StartupAssessmentDraft.Status.SUBMITTED
    draft.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    response = authenticated_client(founder).get(current_url())

    assert response.status_code == (status.HTTP_200_OK)
    assert response.data["current_state"] == ("generating_plan")
    assert response.data["draft"]["status"] == ("submitted")


def test_submitted_draft_cannot_start_new_flow():
    founder = make_user("concierge-api-submitted-new")
    make_draft(
        owner=founder,
        status_value=(StartupAssessmentDraft.Status.SUBMITTED),
    )

    response = authenticated_client(founder).get(current_url())

    assert response.status_code == (status.HTTP_404_NOT_FOUND)
    assert AgentSession.objects.count() == 0
