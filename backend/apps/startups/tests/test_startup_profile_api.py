import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.startups.models import StartupProfile

pytestmark = pytest.mark.django_db


def test_authenticated_founder_can_patch_profile():
    founder = User.objects.create_user(
        username="profile-founder",
        email="founder@example.com",
        password="Safe-password-2026!",
        role=User.Role.FOUNDER,
    )

    profile = StartupProfile.objects.create(
        owner=founder,
        startup_name="Acme BioTech",
        stage=StartupProfile.Stage.EARLY_REVENUE,
        state="Karnataka",
    )

    client = APIClient()
    client.force_authenticate(user=founder)

    response = client.patch(
        reverse("startup-profile-detail", kwargs={"pk": str(profile.id)}),
        {
            "legal_name": "Acme BioTech Private Limited",
            "dpiit_recognized": True,
            "annual_turnover": "2500000.00",
            "profile_data": {
                "gstin": "29ABCDE1234F1Z5",
                "target_market": "Pharma & Biotech",
            },
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    profile.refresh_from_db()
    assert profile.legal_name == "Acme BioTech Private Limited"
    assert profile.dpiit_recognized is True
    assert profile.profile_data.get("gstin") == "29ABCDE1234F1Z5"
    assert profile.profile_data.get("target_market") == "Pharma & Biotech"


def test_founder_cannot_patch_other_founders_profile():
    owner = User.objects.create_user(
        username="owner-founder",
        email="owner@example.com",
        password="Safe-password-2026!",
        role=User.Role.FOUNDER,
    )
    other = User.objects.create_user(
        username="other-founder",
        email="other@example.com",
        password="Safe-password-2026!",
        role=User.Role.FOUNDER,
    )

    profile = StartupProfile.objects.create(
        owner=owner,
        startup_name="Owner Startup",
        stage=StartupProfile.Stage.IDEA,
    )

    client = APIClient()
    client.force_authenticate(user=other)

    response = client.patch(
        reverse("startup-profile-detail", kwargs={"pk": str(profile.id)}),
        {"startup_name": "Hacked Name"},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
