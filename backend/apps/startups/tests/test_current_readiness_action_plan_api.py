from datetime import date

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.startups.models import StartupReadinessActionPlan
from apps.startups.services import (
    create_startup_readiness_action_plan,
    create_startup_readiness_assessment,
)
from apps.startups.tests.test_readiness_assessment_api import (
    authenticated_client,
    make_profile,
    make_user,
)

pytestmark = pytest.mark.django_db


def make_assessment(*, owner, name: str):
    profile = make_profile(owner=owner, name=name)
    profile.description = ""
    profile.save(update_fields=["description", "updated_at"])
    assessment = create_startup_readiness_assessment(
        startup_profile=profile,
        requested_by=owner,
        assessment_date=date(2026, 7, 21),
    )
    return profile, assessment


def make_action_plan(*, owner, name: str):
    profile, assessment = make_assessment(
        owner=owner,
        name=name,
    )
    plan = create_startup_readiness_action_plan(
        source_assessment=assessment,
        requested_by=owner,
    )
    return profile, assessment, plan


def current_url(profile_id):
    return reverse("startup-readiness-action-plan-current") + f"?startup_profile_id={profile_id}"


def test_owner_receives_latest_persisted_action_plan():
    owner = make_user(username="current-plan-owner")
    profile, assessment = make_assessment(
        owner=owner,
        name="Current Plan Startup",
    )
    first = create_startup_readiness_action_plan(
        source_assessment=assessment,
        requested_by=owner,
    )
    second = create_startup_readiness_action_plan(
        source_assessment=assessment,
        requested_by=owner,
    )

    response = authenticated_client(owner).get(current_url(profile.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["startup_profile_id"] == str(profile.id)
    assert response.data["has_action_plan"] is True
    assert response.data["action_plan"]["id"] == str(second.id)
    assert response.data["action_plan"]["id"] != str(first.id)
    assert response.data["action_plan"]["items"] == second.items
    assert (
        response.data["action_plan"]["source_assessment_snapshot"]
        == second.source_assessment_snapshot
    )


def test_profile_without_plan_returns_empty_200():
    owner = make_user(username="current-plan-empty-owner")
    profile = make_profile(
        owner=owner,
        name="Current Plan Empty Startup",
    )

    response = authenticated_client(owner).get(current_url(profile.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "startup_profile_id": str(profile.id),
        "has_action_plan": False,
        "action_plan": None,
    }


def test_other_user_cannot_access_profile_plan():
    owner = make_user(username="current-plan-private-owner")
    other = make_user(username="current-plan-private-other")
    profile, _assessment, _plan = make_action_plan(
        owner=owner,
        name="Current Plan Private Startup",
    )

    response = authenticated_client(other).get(current_url(profile.id))

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_staff_can_access_another_users_plan():
    owner = make_user(username="current-plan-staff-owner")
    staff = make_user(
        username="current-plan-staff",
        is_staff=True,
    )
    profile, _assessment, plan = make_action_plan(
        owner=owner,
        name="Current Plan Staff Startup",
    )

    response = authenticated_client(staff).get(current_url(profile.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["has_action_plan"] is True
    assert response.data["action_plan"]["id"] == str(plan.id)


def test_missing_profile_id_returns_400():
    owner = make_user(username="current-plan-missing-owner")

    response = authenticated_client(owner).get(reverse("startup-readiness-action-plan-current"))

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "startup_profile_id" in response.data


def test_unauthenticated_request_is_rejected():
    owner = make_user(username="current-plan-auth-owner")
    profile = make_profile(
        owner=owner,
        name="Current Plan Auth Startup",
    )

    response = APIClient().get(current_url(profile.id))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_current_endpoint_is_read_only_and_uses_stored_data(
    monkeypatch,
):
    owner = make_user(username="current-plan-stored-owner")
    profile, assessment, plan = make_action_plan(
        owner=owner,
        name="Current Plan Stored Startup",
    )
    stored_items = plan.items
    stored_snapshot = plan.source_assessment_snapshot

    profile.description = "Changed after plan generation."
    profile.save(update_fields=["description", "updated_at"])
    assessment.findings = []
    assessment.summary = "Changed after plan generation."
    assessment.save(
        update_fields=[
            "findings",
            "summary",
            "updated_at",
        ]
    )

    def fail_write(*args, **kwargs):
        raise AssertionError("Current action-plan retrieval must not write.")

    monkeypatch.setattr(
        "apps.startups.views.create_startup_readiness_action_plan",
        fail_write,
    )
    monkeypatch.setattr(
        "apps.startups.views.create_startup_readiness_assessment",
        fail_write,
    )

    count_before = StartupReadinessActionPlan.objects.count()

    response = authenticated_client(owner).get(current_url(profile.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["action_plan"]["items"] == stored_items
    assert response.data["action_plan"]["source_assessment_snapshot"] == stored_snapshot
    assert StartupReadinessActionPlan.objects.count() == count_before
