from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.startups.models import (
    StartupProfile,
    StartupReadinessAssessment,
)

pytestmark = pytest.mark.django_db


def make_user(*, username: str, is_staff: bool = False):
    user_model = get_user_model()
    return user_model.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="test-password",
        is_staff=is_staff,
    )


def make_profile(*, owner, name: str):
    return StartupProfile.objects.create(
        owner=owner,
        startup_name=name,
        legal_name=f"{name} Private Limited",
        description=(
            "A technology startup solving a clearly "
            "defined customer problem with a scalable "
            "digital product."
        ),
        incorporation_type="private_limited",
        incorporation_date=date(2025, 1, 15),
        state="Karnataka",
        district="Bengaluru Urban",
        stage=StartupProfile.Stage.MVP,
        sectors=["software"],
        technologies=["artificial intelligence"],
        dpiit_recognized=True,
        udyam_registered=False,
        annual_turnover=Decimal("1000000.00"),
        revenue_stage="early_revenue",
        funding_required=Decimal("5000000.00"),
        funding_purpose=("Product development and market expansion."),
        team_size=8,
        profile_data={},
    )


def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_owner_can_create_readiness_assessment():
    owner = make_user(username="readiness-api-owner")
    profile = make_profile(
        owner=owner,
        name="Readiness API Startup",
    )

    response = authenticated_client(owner).post(
        reverse("startup-readiness-evaluate"),
        {
            "startup_profile_id": str(profile.id),
            "assessment_date": "2026-07-21",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["startup_profile_id"] == str(profile.id)
    assert response.data["requested_by_id"] == str(owner.id)
    assert response.data["assessment_date"] == ("2026-07-21")
    assert response.data["status"] == "ready"
    assert response.data["score"] == 100
    assert response.data["engine_version"] == ("startup-readiness-v1")
    assert StartupReadinessAssessment.objects.count() == 1


def test_other_user_receives_404_for_unowned_profile():
    owner = make_user(username="readiness-private-owner")
    other = make_user(username="readiness-private-other")
    profile = make_profile(
        owner=owner,
        name="Readiness Private Startup",
    )

    response = authenticated_client(other).post(
        reverse("startup-readiness-evaluate"),
        {
            "startup_profile_id": str(profile.id),
            "assessment_date": "2026-07-21",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert StartupReadinessAssessment.objects.count() == 0


def test_staff_can_assess_another_users_profile():
    owner = make_user(username="readiness-staff-owner")
    staff = make_user(
        username="readiness-staff",
        is_staff=True,
    )
    profile = make_profile(
        owner=owner,
        name="Readiness Staff Startup",
    )

    response = authenticated_client(staff).post(
        reverse("startup-readiness-evaluate"),
        {
            "startup_profile_id": str(profile.id),
            "assessment_date": "2026-07-21",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assessment = StartupReadinessAssessment.objects.get()
    assert assessment.requested_by == staff
    assert assessment.startup_profile == profile


def test_raw_profile_payload_is_rejected():
    owner = make_user(username="readiness-raw-owner")
    profile = make_profile(
        owner=owner,
        name="Readiness Raw Startup",
    )

    response = authenticated_client(owner).post(
        reverse("startup-readiness-evaluate"),
        {
            "startup_profile_id": str(profile.id),
            "assessment_date": "2026-07-21",
            "profile": {
                "dpiit_recognized": False,
            },
        },
        format="json",
    )

    assert response.status_code == (status.HTTP_400_BAD_REQUEST)
    assert "profile" in response.data
    assert StartupReadinessAssessment.objects.count() == 0


def test_unauthenticated_request_is_rejected():
    owner = make_user(username="readiness-auth-owner")
    profile = make_profile(
        owner=owner,
        name="Readiness Auth Startup",
    )

    response = APIClient().post(
        reverse("startup-readiness-evaluate"),
        {
            "startup_profile_id": str(profile.id),
            "assessment_date": "2026-07-21",
        },
        format="json",
    )

    assert response.status_code == (status.HTTP_401_UNAUTHORIZED)
    assert StartupReadinessAssessment.objects.count() == 0
