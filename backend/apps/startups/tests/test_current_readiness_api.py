from datetime import date

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.startups.models import (
    StartupReadinessAssessment,
)
from apps.startups.services import (
    create_startup_readiness_assessment,
)
from apps.startups.tests.test_readiness_assessment_api import (
    authenticated_client,
    make_profile,
    make_user,
)

pytestmark = pytest.mark.django_db


def create_assessment(
    *,
    profile,
    requested_by,
    assessment_date,
):
    return create_startup_readiness_assessment(
        startup_profile=profile,
        requested_by=requested_by,
        assessment_date=assessment_date,
    )


def test_owner_retrieves_latest_persisted_assessment_without_writes():
    owner = make_user(username="readiness-current-owner")
    profile = make_profile(
        owner=owner,
        name="Readiness Current Startup",
    )
    first = create_assessment(
        profile=profile,
        requested_by=owner,
        assessment_date=date(2026, 7, 20),
    )
    profile.district = ""
    profile.save(
        update_fields=[
            "district",
            "updated_at",
        ]
    )
    second = create_assessment(
        profile=profile,
        requested_by=owner,
        assessment_date=date(2026, 7, 21),
    )

    profile.dpiit_recognized = None
    profile.save(
        update_fields=[
            "dpiit_recognized",
            "updated_at",
        ]
    )

    assessment_count = StartupReadinessAssessment.objects.count()
    response = authenticated_client(owner).get(
        reverse("startup-readiness-current"),
        {
            "startup_profile_id": str(profile.id),
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["startup_profile_id"] == str(profile.id)
    assert response.data["has_assessment"] is True
    assessment = response.data["assessment"]
    assert assessment["id"] == str(second.id)
    assert assessment["id"] != str(first.id)
    assert assessment["assessment_date"] == ("2026-07-21")
    assert assessment["status"] == ("ready_with_recommendations")
    assert assessment["profile_snapshot"]["district"] == ""
    assert assessment["profile_snapshot"]["dpiit_recognized"] is True
    assert StartupReadinessAssessment.objects.count() == assessment_count


def test_never_assessed_profile_returns_explicit_empty_state():
    owner = make_user(username="readiness-current-empty")
    profile = make_profile(
        owner=owner,
        name="Readiness Current Empty Startup",
    )

    response = authenticated_client(owner).get(
        reverse("startup-readiness-current"),
        {
            "startup_profile_id": str(profile.id),
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "startup_profile_id": str(profile.id),
        "has_assessment": False,
        "assessment": None,
    }


def test_other_user_receives_404_for_unowned_profile():
    owner = make_user(username="readiness-current-private-owner")
    other = make_user(username="readiness-current-private-other")
    profile = make_profile(
        owner=owner,
        name="Readiness Current Private Startup",
    )
    create_assessment(
        profile=profile,
        requested_by=owner,
        assessment_date=date(2026, 7, 21),
    )

    response = authenticated_client(other).get(
        reverse("startup-readiness-current"),
        {
            "startup_profile_id": str(profile.id),
        },
    )

    assert response.status_code == (status.HTTP_404_NOT_FOUND)


def test_staff_can_retrieve_another_users_assessment():
    owner = make_user(username="readiness-current-staff-owner")
    staff = make_user(
        username="readiness-current-staff",
        is_staff=True,
    )
    profile = make_profile(
        owner=owner,
        name="Readiness Current Staff Startup",
    )
    assessment = create_assessment(
        profile=profile,
        requested_by=owner,
        assessment_date=date(2026, 7, 21),
    )

    response = authenticated_client(staff).get(
        reverse("startup-readiness-current"),
        {
            "startup_profile_id": str(profile.id),
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["has_assessment"] is True
    assert response.data["assessment"]["id"] == str(assessment.id)


def test_missing_profile_id_is_rejected():
    user = make_user(username="readiness-current-missing")

    response = authenticated_client(user).get(
        reverse("startup-readiness-current"),
    )

    assert response.status_code == (status.HTTP_400_BAD_REQUEST)
    assert "startup_profile_id" in response.data


def test_unknown_profile_returns_404():
    user = make_user(username="readiness-current-unknown")

    response = authenticated_client(user).get(
        reverse("startup-readiness-current"),
        {
            "startup_profile_id": ("00000000-0000-0000-0000-000000000001"),
        },
    )

    assert response.status_code == (status.HTTP_404_NOT_FOUND)


def test_unauthenticated_request_is_rejected():
    owner = make_user(username="readiness-current-auth-owner")
    profile = make_profile(
        owner=owner,
        name="Readiness Current Auth Startup",
    )

    response = APIClient().get(
        reverse("startup-readiness-current"),
        {
            "startup_profile_id": str(profile.id),
        },
    )

    assert response.status_code == (status.HTTP_401_UNAUTHORIZED)
