import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def registration_payload(**overrides):
    payload = {
        "username": "new-founder",
        "email": "new-founder@example.com",
        "first_name": "New",
        "last_name": "Founder",
        "password": "Safe-founder-password-2026!",
        "password_confirm": "Safe-founder-password-2026!",
    }
    payload.update(overrides)
    return payload


def test_public_founder_registration_creates_founder():
    response = APIClient().post(
        reverse("founder-register"),
        registration_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    founder = User.objects.get(
        username="new-founder",
    )

    assert founder.email == "new-founder@example.com"
    assert founder.first_name == "New"
    assert founder.last_name == "Founder"
    assert founder.role == User.Role.FOUNDER
    assert founder.email_verified is False
    assert founder.check_password(
        "Safe-founder-password-2026!"
    )

    assert response.data == {
        "id": str(founder.id),
        "username": "new-founder",
        "email": "new-founder@example.com",
        "first_name": "New",
        "last_name": "Founder",
        "role": User.Role.FOUNDER,
        "email_verified": False,
    }


def test_registration_rejects_password_mismatch():
    response = APIClient().post(
        reverse("founder-register"),
        registration_payload(
            password_confirm="Different-password-2026!",
        ),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "password_confirm" in response.data
    assert User.objects.count() == 0


def test_registration_rejects_duplicate_email_case_insensitively():
    User.objects.create_user(
        username="existing-founder",
        email="founder@example.com",
        password="Safe-founder-password-2026!",
    )

    response = APIClient().post(
        reverse("founder-register"),
        registration_payload(
            email="FOUNDER@example.com",
        ),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "email" in response.data


def test_public_registration_cannot_assign_privileged_role():
    payload = registration_payload(
        username="role-safe-founder",
        email="role-safe-founder@example.com",
    )
    payload["role"] = User.Role.ADMIN

    response = APIClient().post(
        reverse("founder-register"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    founder = User.objects.get(
        username="role-safe-founder",
    )
    assert founder.role == User.Role.FOUNDER
