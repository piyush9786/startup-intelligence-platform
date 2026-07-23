import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def make_user(
    username,
    *,
    role=User.Role.FOUNDER,
    is_staff=False,
    is_superuser=False,
):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="test-password",
        role=role,
        is_staff=is_staff,
        is_superuser=is_superuser,
    )


def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_current_user_requires_authentication():
    response = APIClient().get(
        reverse("current-user"),
    )

    assert response.status_code == (
        status.HTTP_401_UNAUTHORIZED
    )


def test_founder_receives_authoritative_identity():
    founder = make_user("identity-founder")
    response = authenticated_client(founder).get(
        reverse("current-user"),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "id": str(founder.id),
        "username": founder.username,
        "email": founder.email,
        "role": User.Role.FOUNDER,
        "role_label": "Founder",
        "email_verified": False,
        "is_staff": False,
        "is_superuser": False,
        "can_review_eligibility": False,
    }


@pytest.mark.parametrize(
    "role",
    [
        User.Role.REVIEWER,
        User.Role.ADMIN,
    ],
)
def test_reviewer_roles_receive_review_capability(role):
    user = make_user(
        f"identity-{role}",
        role=role,
    )

    response = authenticated_client(user).get(
        reverse("current-user"),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["role"] == role
    assert response.data["can_review_eligibility"] is True


def test_staff_flag_alone_does_not_grant_review_capability():
    staff = make_user(
        "identity-staff",
        role=User.Role.FOUNDER,
        is_staff=True,
    )

    response = authenticated_client(staff).get(
        reverse("current-user"),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["is_staff"] is True
    assert response.data["can_review_eligibility"] is False


def test_superuser_receives_review_capability():
    superuser = make_user(
        "identity-superuser",
        role=User.Role.FOUNDER,
        is_staff=True,
        is_superuser=True,
    )

    response = authenticated_client(superuser).get(
        reverse("current-user"),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["can_review_eligibility"] is True
