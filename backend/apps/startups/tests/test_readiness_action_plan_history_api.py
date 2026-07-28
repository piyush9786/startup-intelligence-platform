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
    action_plan = create_startup_readiness_action_plan(
        source_assessment=assessment,
        requested_by=owner,
    )
    return profile, assessment, action_plan


def list_url(profile_id):
    return reverse("startup-readiness-action-plan-list") + f"?startup_profile_id={profile_id}"


def test_owner_receives_historical_plans_newest_first():
    owner = make_user(username="plan-history-owner")
    profile, assessment = make_assessment(
        owner=owner,
        name="Plan History Startup",
    )
    first = create_startup_readiness_action_plan(
        source_assessment=assessment,
        requested_by=owner,
    )
    second = create_startup_readiness_action_plan(
        source_assessment=assessment,
        requested_by=owner,
    )

    response = authenticated_client(owner).get(list_url(profile.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["startup_profile_id"] == str(profile.id)
    assert response.data["count"] == 2
    assert [item["id"] for item in response.data["action_plans"]] == [
        str(second.id),
        str(first.id),
    ]
    assert response.data["action_plans"][0]["items"] == second.items
    assert (
        response.data["action_plans"][1]["source_assessment_snapshot"]
        == first.source_assessment_snapshot
    )


def test_empty_history_returns_empty_list():
    owner = make_user(username="plan-history-empty-owner")
    profile = make_profile(
        owner=owner,
        name="Plan History Empty Startup",
    )

    response = authenticated_client(owner).get(list_url(profile.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "startup_profile_id": str(profile.id),
        "count": 0,
        "action_plans": [],
    }


def test_other_user_cannot_list_history():
    owner = make_user(username="plan-history-private-owner")
    other = make_user(username="plan-history-private-other")
    profile, _assessment, _plan = make_action_plan(
        owner=owner,
        name="Plan History Private Startup",
    )

    response = authenticated_client(other).get(list_url(profile.id))

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_staff_can_list_another_users_history():
    owner = make_user(username="plan-history-staff-owner")
    staff = make_user(
        username="plan-history-staff",
        is_staff=True,
    )
    profile, _assessment, plan = make_action_plan(
        owner=owner,
        name="Plan History Staff Startup",
    )

    response = authenticated_client(staff).get(list_url(profile.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["action_plans"][0]["id"] == str(plan.id)


def test_owner_can_retrieve_historical_plan_detail():
    owner = make_user(username="plan-detail-owner")
    _profile, _assessment, plan = make_action_plan(
        owner=owner,
        name="Plan Detail Startup",
    )

    response = authenticated_client(owner).get(
        reverse(
            "startup-readiness-action-plan-detail",
            kwargs={"action_plan_id": plan.id},
        )
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(plan.id)
    assert response.data["items"] == plan.items
    assert response.data["source_assessment_snapshot"] == (plan.source_assessment_snapshot)


def test_other_user_cannot_retrieve_plan_detail():
    owner = make_user(username="plan-detail-private-owner")
    other = make_user(username="plan-detail-private-other")
    _profile, _assessment, plan = make_action_plan(
        owner=owner,
        name="Plan Detail Private Startup",
    )

    response = authenticated_client(other).get(
        reverse(
            "startup-readiness-action-plan-detail",
            kwargs={"action_plan_id": plan.id},
        )
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_unknown_plan_detail_returns_404():
    owner = make_user(username="plan-detail-unknown-owner")

    response = authenticated_client(owner).get(
        reverse(
            "startup-readiness-action-plan-detail",
            kwargs={"action_plan_id": ("00000000-0000-0000-0000-000000000001")},
        )
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_history_endpoints_are_read_only_and_use_stored_data(
    monkeypatch,
):
    owner = make_user(username="plan-history-stored-owner")
    profile, assessment, plan = make_action_plan(
        owner=owner,
        name="Plan History Stored Startup",
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
        raise AssertionError("Action-plan history retrieval must not write.")

    monkeypatch.setattr(
        "apps.startups.views.create_startup_readiness_action_plan",
        fail_write,
    )
    monkeypatch.setattr(
        "apps.startups.views.create_startup_readiness_assessment",
        fail_write,
    )

    count_before = StartupReadinessActionPlan.objects.count()

    list_response = authenticated_client(owner).get(list_url(profile.id))
    detail_response = authenticated_client(owner).get(
        reverse(
            "startup-readiness-action-plan-detail",
            kwargs={"action_plan_id": plan.id},
        )
    )

    assert list_response.status_code == status.HTTP_200_OK
    assert detail_response.status_code == status.HTTP_200_OK
    assert list_response.data["action_plans"][0]["items"] == (stored_items)
    assert detail_response.data["source_assessment_snapshot"] == (stored_snapshot)
    assert StartupReadinessActionPlan.objects.count() == count_before


def test_unauthenticated_history_requests_are_rejected():
    owner = make_user(username="plan-history-auth-owner")
    profile, _assessment, plan = make_action_plan(
        owner=owner,
        name="Plan History Auth Startup",
    )

    list_response = APIClient().get(list_url(profile.id))
    detail_response = APIClient().get(
        reverse(
            "startup-readiness-action-plan-detail",
            kwargs={"action_plan_id": plan.id},
        )
    )

    assert list_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert detail_response.status_code == status.HTTP_401_UNAUTHORIZED
