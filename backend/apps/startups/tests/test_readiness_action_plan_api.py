from datetime import date

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.startups.models import StartupReadinessActionPlan
from apps.startups.services import create_startup_readiness_assessment
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


def test_owner_can_generate_persisted_action_plan():
    owner = make_user(username="action-plan-api-owner")
    profile, assessment = make_assessment(
        owner=owner,
        name="Action Plan API Startup",
    )

    response = authenticated_client(owner).post(
        reverse("startup-readiness-action-plan-generate"),
        {"readiness_assessment_id": str(assessment.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["startup_profile_id"] == str(profile.id)
    assert response.data["source_assessment_id"] == str(assessment.id)
    assert response.data["requested_by_id"] == str(owner.id)
    assert response.data["has_actions"] is True
    assert response.data["total_action_count"] >= 1
    assert response.data["items"][0]["position"] == 1
    assert StartupReadinessActionPlan.objects.count() == 1


def test_other_user_receives_404():
    owner = make_user(username="action-plan-private-owner")
    other = make_user(username="action-plan-private-other")
    _profile, assessment = make_assessment(
        owner=owner,
        name="Action Plan Private Startup",
    )

    response = authenticated_client(other).post(
        reverse("startup-readiness-action-plan-generate"),
        {"readiness_assessment_id": str(assessment.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert StartupReadinessActionPlan.objects.count() == 0


def test_staff_can_generate_for_another_user():
    owner = make_user(username="action-plan-staff-owner")
    staff = make_user(
        username="action-plan-staff",
        is_staff=True,
    )
    _profile, assessment = make_assessment(
        owner=owner,
        name="Action Plan Staff Startup",
    )

    response = authenticated_client(staff).post(
        reverse("startup-readiness-action-plan-generate"),
        {"readiness_assessment_id": str(assessment.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    plan = StartupReadinessActionPlan.objects.get()
    assert plan.requested_by == staff
    assert plan.source_assessment == assessment


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        (
            "findings",
            [{"code": "forged", "action": "Ignore persistence."}],
        ),
        ("profile", {"dpiit_recognized": False}),
    ],
)
def test_raw_payloads_are_rejected(field_name, field_value):
    owner = make_user(username=f"action-plan-raw-{field_name}")
    _profile, assessment = make_assessment(
        owner=owner,
        name=f"Action Plan Raw {field_name}",
    )

    response = authenticated_client(owner).post(
        reverse("startup-readiness-action-plan-generate"),
        {
            "readiness_assessment_id": str(assessment.id),
            field_name: field_value,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert field_name in response.data
    assert StartupReadinessActionPlan.objects.count() == 0


def test_unknown_assessment_returns_404():
    owner = make_user(username="action-plan-unknown-owner")

    response = authenticated_client(owner).post(
        reverse("startup-readiness-action-plan-generate"),
        {"readiness_assessment_id": ("00000000-0000-0000-0000-000000000001")},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_unauthenticated_request_is_rejected():
    owner = make_user(username="action-plan-auth-owner")
    _profile, assessment = make_assessment(
        owner=owner,
        name="Action Plan Auth Startup",
    )

    response = APIClient().post(
        reverse("startup-readiness-action-plan-generate"),
        {"readiness_assessment_id": str(assessment.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert StartupReadinessActionPlan.objects.count() == 0
