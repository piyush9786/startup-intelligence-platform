from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.assistant.models import AgentSession
from apps.assistant.services import (
    advance_concierge_session,
    create_or_get_active_session,
    initialize_concierge_session,
)
from apps.startups.models import (
    StartupAssessmentDraft,
    StartupProfile,
)
from apps.startups.tests.test_startup_assessment_draft_api import (
    recommendation_generation,
    valid_draft_data,
)

pytestmark = pytest.mark.django_db


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
    data=None,
) -> StartupAssessmentDraft:
    return StartupAssessmentDraft.objects.create(
        owner=owner,
        startup_profile=startup_profile,
        current_step=8,
        data=data or valid_draft_data(),
    )


def authenticated_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def submission_url(
    draft: StartupAssessmentDraft,
) -> str:
    return reverse(
        "startup-assessment-draft-submit",
        kwargs={
            "draft_id": draft.pk,
        },
    )


def make_concierge_session_at_state(
    *,
    founder,
    draft,
    startup_profile=None,
    target_state="generating_plan",
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
        current_state = payload["current_state"]
        kwargs = {}

        if current_state == "confirm_profile":
            kwargs["confirmed"] = True

        if current_state == "generating_plan":
            kwargs["system_transition"] = True

        payload = advance_concierge_session(
            session=session,
            draft=draft,
            expected_state=current_state,
            **kwargs,
        )

    session.refresh_from_db()

    return session


@patch("apps.startups.services.assessment_submission.generate_recommendations")
def test_successful_submission_completes_generating_session(
    mock_generate,
):
    founder = make_user("concierge-bridge-success")
    draft = make_draft(owner=founder)
    session = make_concierge_session_at_state(
        founder=founder,
        draft=draft,
    )
    mock_generate.side_effect = recommendation_generation

    response = authenticated_client(founder).post(
        submission_url(draft),
        {},
        format="json",
    )

    assert response.status_code == (status.HTTP_201_CREATED)
    assert "concierge" not in response.data
    assert set(response.data) == {
        "draft",
        "startup_profile",
        "readiness_assessment",
        "action_plan",
        "starting_plan",
        "recommendations",
    }

    session.refresh_from_db()
    draft.refresh_from_db()

    assert draft.status == (StartupAssessmentDraft.Status.SUBMITTED)
    assert session.state["current_state"] == ("plan_ready")
    assert session.state["completed_states"][-1] == ("generating_plan")


@patch("apps.startups.services.assessment_submission.generate_recommendations")
def test_normal_submission_without_concierge_is_unchanged(
    mock_generate,
):
    founder = make_user("concierge-bridge-no-session")
    draft = make_draft(owner=founder)
    mock_generate.side_effect = recommendation_generation

    response = authenticated_client(founder).post(
        submission_url(draft),
        {},
        format="json",
    )

    assert response.status_code == (status.HTTP_201_CREATED)
    assert AgentSession.objects.count() == 0
    assert "concierge" not in response.data


def test_validation_failure_does_not_advance_session():
    founder = make_user("concierge-bridge-validation-failure")
    invalid_data = {
        **valid_draft_data(),
        "incorporation_date": (timezone.localdate() + timedelta(days=1)).isoformat(),
    }
    draft = make_draft(
        owner=founder,
        data=invalid_data,
    )
    session = make_concierge_session_at_state(
        founder=founder,
        draft=draft,
    )

    response = authenticated_client(founder).post(
        submission_url(draft),
        {},
        format="json",
    )

    assert response.status_code == (status.HTTP_400_BAD_REQUEST)

    session.refresh_from_db()
    draft.refresh_from_db()

    assert session.state["current_state"] == ("generating_plan")
    assert draft.status == (StartupAssessmentDraft.Status.DRAFT)
    assert StartupProfile.objects.count() == 0


@patch("apps.startups.services.assessment_submission.generate_recommendations")
def test_generation_failure_rolls_back_submission_and_state(
    mock_generate,
):
    founder = make_user("concierge-bridge-generation-failure")
    draft = make_draft(owner=founder)
    session = make_concierge_session_at_state(
        founder=founder,
        draft=draft,
    )
    mock_generate.side_effect = RuntimeError("Deterministic generation failed.")

    with pytest.raises(
        RuntimeError,
        match="Deterministic generation failed",
    ):
        authenticated_client(founder).post(
            submission_url(draft),
            {},
            format="json",
        )

    session.refresh_from_db()
    draft.refresh_from_db()

    assert session.state["current_state"] == ("generating_plan")
    assert draft.status == (StartupAssessmentDraft.Status.DRAFT)
    assert draft.startup_profile_id is None
    assert StartupProfile.objects.count() == 0


@patch("apps.startups.services.assessment_submission.generate_recommendations")
def test_submission_does_not_advance_unconfirmed_session(
    mock_generate,
):
    founder = make_user("concierge-bridge-unconfirmed")
    draft = make_draft(owner=founder)
    session = make_concierge_session_at_state(
        founder=founder,
        draft=draft,
        target_state="confirm_profile",
    )
    mock_generate.side_effect = recommendation_generation

    response = authenticated_client(founder).post(
        submission_url(draft),
        {},
        format="json",
    )

    assert response.status_code == (status.HTTP_201_CREATED)

    session.refresh_from_db()

    assert session.state["current_state"] == ("confirm_profile")


@patch("apps.startups.services.assessment_submission.generate_recommendations")
def test_plan_ready_bridge_is_idempotent(
    mock_generate,
):
    founder = make_user("concierge-bridge-idempotent")
    draft = make_draft(owner=founder)
    session = make_concierge_session_at_state(
        founder=founder,
        draft=draft,
        target_state="plan_ready",
    )
    completed_before = list(session.state["completed_states"])
    mock_generate.side_effect = recommendation_generation

    response = authenticated_client(founder).post(
        submission_url(draft),
        {},
        format="json",
    )

    assert response.status_code == (status.HTTP_201_CREATED)

    session.refresh_from_db()

    assert session.state["current_state"] == ("plan_ready")
    assert session.state["completed_states"] == (completed_before)


@patch("apps.startups.services.assessment_submission.generate_recommendations")
def test_linked_profile_scope_completes_matching_session(
    mock_generate,
):
    founder = make_user("concierge-bridge-linked")
    profile = make_profile(
        owner=founder,
        name="Linked Bridge Startup",
    )
    draft = make_draft(
        owner=founder,
        startup_profile=profile,
    )
    session = make_concierge_session_at_state(
        founder=founder,
        draft=draft,
        startup_profile=profile,
    )
    mock_generate.side_effect = recommendation_generation

    response = authenticated_client(founder).post(
        submission_url(draft),
        {},
        format="json",
    )

    assert response.status_code == (status.HTTP_201_CREATED)

    session.refresh_from_db()
    draft.refresh_from_db()

    assert draft.startup_profile_id == profile.pk
    assert session.startup_profile_id == profile.pk
    assert session.state["current_state"] == ("plan_ready")


@patch("apps.startups.services.assessment_submission.generate_recommendations")
def test_other_founders_session_is_unchanged(
    mock_generate,
):
    first_founder = make_user("concierge-bridge-first-founder")
    second_founder = make_user("concierge-bridge-second-founder")
    first_draft = make_draft(
        owner=first_founder,
    )
    second_draft = make_draft(
        owner=second_founder,
    )
    first_session = make_concierge_session_at_state(
        founder=first_founder,
        draft=first_draft,
    )
    mock_generate.side_effect = recommendation_generation

    response = authenticated_client(second_founder).post(
        submission_url(second_draft),
        {},
        format="json",
    )

    assert response.status_code == (status.HTTP_201_CREATED)

    first_session.refresh_from_db()

    assert first_session.state["current_state"] == ("generating_plan")
