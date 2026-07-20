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


def make_history(*, owner, profile):
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
    return first, second


def test_owner_lists_assessments_newest_first_without_writes():
    owner = make_user(username="readiness-history-list-owner")
    profile = make_profile(
        owner=owner,
        name="Readiness History List Startup",
    )
    first, second = make_history(
        owner=owner,
        profile=profile,
    )
    assessment_count = StartupReadinessAssessment.objects.count()

    response = authenticated_client(owner).get(
        reverse("startup-readiness-assessment-list"),
        {
            "startup_profile_id": str(profile.id),
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["startup_profile_id"] == str(profile.id)
    assert response.data["count"] == 2
    assert [item["id"] for item in response.data["assessments"]] == [
        str(second.id),
        str(first.id),
    ]
    assert response.data["assessments"][0]["profile_snapshot"]["district"] == ""
    assert response.data["assessments"][1]["profile_snapshot"]["district"] == "Bengaluru Urban"
    assert StartupReadinessAssessment.objects.count() == assessment_count


def test_owner_lists_empty_assessment_history():
    owner = make_user(username="readiness-history-empty")
    profile = make_profile(
        owner=owner,
        name="Readiness History Empty Startup",
    )

    response = authenticated_client(owner).get(
        reverse("startup-readiness-assessment-list"),
        {
            "startup_profile_id": str(profile.id),
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "startup_profile_id": str(profile.id),
        "count": 0,
        "assessments": [],
    }


def test_other_user_cannot_list_profile_history():
    owner = make_user(username="readiness-history-private-owner")
    other = make_user(username="readiness-history-private-other")
    profile = make_profile(
        owner=owner,
        name="Readiness History Private Startup",
    )
    make_history(
        owner=owner,
        profile=profile,
    )

    response = authenticated_client(other).get(
        reverse("startup-readiness-assessment-list"),
        {
            "startup_profile_id": str(profile.id),
        },
    )

    assert response.status_code == (status.HTTP_404_NOT_FOUND)


def test_staff_can_list_another_users_history():
    owner = make_user(username="readiness-history-staff-owner")
    staff = make_user(
        username="readiness-history-staff",
        is_staff=True,
    )
    profile = make_profile(
        owner=owner,
        name="Readiness History Staff Startup",
    )
    make_history(
        owner=owner,
        profile=profile,
    )

    response = authenticated_client(staff).get(
        reverse("startup-readiness-assessment-list"),
        {
            "startup_profile_id": str(profile.id),
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2


def test_owner_retrieves_historical_assessment_detail():
    owner = make_user(username="readiness-history-detail-owner")
    profile = make_profile(
        owner=owner,
        name="Readiness History Detail Startup",
    )
    first, _second = make_history(
        owner=owner,
        profile=profile,
    )

    response = authenticated_client(owner).get(
        reverse(
            "startup-readiness-assessment-detail",
            kwargs={
                "assessment_id": first.id,
            },
        )
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(first.id)
    assert response.data["startup_profile_id"] == str(profile.id)
    assert response.data["requested_by_id"] == str(owner.id)
    assert response.data["assessment_date"] == ("2026-07-20")
    assert response.data["status"] == "ready"
    assert response.data["profile_snapshot"]["district"] == "Bengaluru Urban"
    assert response.data["engine_version"] == ("startup-readiness-v1")


def test_other_user_cannot_retrieve_assessment_detail():
    owner = make_user(username="readiness-history-detail-private-owner")
    other = make_user(username="readiness-history-detail-private-other")
    profile = make_profile(
        owner=owner,
        name="Readiness Detail Private Startup",
    )
    first, _second = make_history(
        owner=owner,
        profile=profile,
    )

    response = authenticated_client(other).get(
        reverse(
            "startup-readiness-assessment-detail",
            kwargs={
                "assessment_id": first.id,
            },
        )
    )

    assert response.status_code == (status.HTTP_404_NOT_FOUND)


def test_staff_can_retrieve_another_users_assessment():
    owner = make_user(username="readiness-history-detail-staff-owner")
    staff = make_user(
        username="readiness-history-detail-staff",
        is_staff=True,
    )
    profile = make_profile(
        owner=owner,
        name="Readiness Detail Staff Startup",
    )
    first, _second = make_history(
        owner=owner,
        profile=profile,
    )

    response = authenticated_client(staff).get(
        reverse(
            "startup-readiness-assessment-detail",
            kwargs={
                "assessment_id": first.id,
            },
        )
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(first.id)


def test_history_endpoints_require_authentication():
    owner = make_user(username="readiness-history-auth-owner")
    profile = make_profile(
        owner=owner,
        name="Readiness History Auth Startup",
    )
    first, _second = make_history(
        owner=owner,
        profile=profile,
    )
    client = APIClient()

    list_response = client.get(
        reverse("startup-readiness-assessment-list"),
        {
            "startup_profile_id": str(profile.id),
        },
    )
    detail_response = client.get(
        reverse(
            "startup-readiness-assessment-detail",
            kwargs={
                "assessment_id": first.id,
            },
        )
    )

    assert list_response.status_code == (status.HTTP_401_UNAUTHORIZED)
    assert detail_response.status_code == (status.HTTP_401_UNAUTHORIZED)
