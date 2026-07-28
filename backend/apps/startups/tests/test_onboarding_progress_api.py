import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.startups.models import (
    OnboardingProgress,
    StartupProfile,
)

pytestmark = pytest.mark.django_db


def make_user(*, username):
    user_model = get_user_model()
    return user_model.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="test-password",
    )


def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def make_profile(*, owner, name):
    return StartupProfile.objects.create(
        owner=owner,
        startup_name=name,
        stage=StartupProfile.Stage.IDEA,
    )


def current_url():
    return reverse("startup-onboarding-current")


def test_current_onboarding_requires_authentication():
    response = APIClient().get(current_url())

    assert response.status_code in {
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    }


def test_first_open_without_profile_uses_empty_variant():
    owner = make_user(
        username="onboarding-empty-founder",
    )

    response = authenticated_client(owner).get(
        current_url(),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["owner_id"] == str(owner.id)
    assert response.data["tour_version"] == "founder-onboarding-v1"
    assert response.data["variant"] == "empty_profile"
    assert response.data["status"] == "active"
    assert response.data["current_step"] == 1
    assert response.data["total_steps"] == 4
    assert response.data["should_show"] is True
    assert (
        OnboardingProgress.objects.filter(
            owner=owner,
        ).count()
        == 1
    )


def test_first_open_with_profile_uses_returning_variant():
    owner = make_user(
        username="onboarding-returning-founder",
    )
    make_profile(
        owner=owner,
        name="Returning Founder Startup",
    )

    response = authenticated_client(owner).get(
        current_url(),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["variant"] == "returning_founder"
    assert response.data["should_show"] is True


def test_current_step_persists_across_reload():
    owner = make_user(
        username="onboarding-resumable-founder",
    )
    client = authenticated_client(owner)

    first_response = client.get(current_url())

    assert first_response.status_code == status.HTTP_200_OK

    update_response = client.patch(
        current_url(),
        {
            "action": "set_step",
            "current_step": 3,
        },
        format="json",
    )

    assert update_response.status_code == status.HTTP_200_OK
    assert update_response.data["current_step"] == 3
    assert update_response.data["status"] == "active"

    reload_response = client.get(current_url())

    assert reload_response.status_code == status.HTTP_200_OK
    assert reload_response.data["current_step"] == 3
    assert (
        OnboardingProgress.objects.filter(
            owner=owner,
        ).count()
        == 1
    )


def test_founder_can_dismiss_and_resume_onboarding():
    owner = make_user(
        username="onboarding-dismiss-founder",
    )
    client = authenticated_client(owner)

    client.get(current_url())
    client.patch(
        current_url(),
        {
            "action": "set_step",
            "current_step": 2,
        },
        format="json",
    )

    dismiss_response = client.patch(
        current_url(),
        {"action": "dismiss"},
        format="json",
    )

    assert dismiss_response.status_code == status.HTTP_200_OK
    assert dismiss_response.data["status"] == "dismissed"
    assert dismiss_response.data["current_step"] == 2
    assert dismiss_response.data["should_show"] is False
    assert dismiss_response.data["dismissed_at"] is not None

    resume_response = client.patch(
        current_url(),
        {"action": "resume"},
        format="json",
    )

    assert resume_response.status_code == status.HTTP_200_OK
    assert resume_response.data["status"] == "active"
    assert resume_response.data["current_step"] == 2
    assert resume_response.data["should_show"] is True
    assert resume_response.data["dismissed_at"] is None


def test_completed_onboarding_does_not_repeat():
    owner = make_user(
        username="onboarding-complete-founder",
    )
    client = authenticated_client(owner)

    client.get(current_url())

    complete_response = client.patch(
        current_url(),
        {"action": "complete"},
        format="json",
    )

    assert complete_response.status_code == status.HTTP_200_OK
    assert complete_response.data["status"] == "completed"
    assert complete_response.data["current_step"] == 4
    assert complete_response.data["should_show"] is False
    assert complete_response.data["completed_at"] is not None

    reload_response = client.get(current_url())

    assert reload_response.status_code == status.HTTP_200_OK
    assert reload_response.data["status"] == "completed"
    assert reload_response.data["should_show"] is False

    resume_response = client.patch(
        current_url(),
        {"action": "resume"},
        format="json",
    )

    assert resume_response.status_code == status.HTTP_409_CONFLICT
    assert resume_response.data["detail"] == "Completed onboarding cannot be reopened."


def test_set_step_requires_a_valid_step():
    owner = make_user(
        username="onboarding-invalid-step",
    )
    client = authenticated_client(owner)

    missing_response = client.patch(
        current_url(),
        {"action": "set_step"},
        format="json",
    )
    high_response = client.patch(
        current_url(),
        {
            "action": "set_step",
            "current_step": 5,
        },
        format="json",
    )

    assert missing_response.status_code == status.HTTP_400_BAD_REQUEST
    assert "current_step" in missing_response.data

    assert high_response.status_code == status.HTTP_400_BAD_REQUEST
    assert "current_step" in high_response.data


def test_users_receive_separate_onboarding_progress():
    first_owner = make_user(
        username="onboarding-owner-one",
    )
    second_owner = make_user(
        username="onboarding-owner-two",
    )

    first_response = authenticated_client(
        first_owner,
    ).get(current_url())
    second_response = authenticated_client(
        second_owner,
    ).get(current_url())

    assert first_response.status_code == status.HTTP_200_OK
    assert second_response.status_code == status.HTTP_200_OK
    assert first_response.data["id"] != second_response.data["id"]
    assert OnboardingProgress.objects.count() == 2
