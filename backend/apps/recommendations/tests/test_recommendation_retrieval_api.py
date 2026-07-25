import uuid
from datetime import date

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.recommendations.models import (
    EligibilityAssessment,
    Recommendation,
)
from apps.recommendations.services import (
    RANKING_VERSION,
    generate_recommendations,
)
from apps.recommendations.tests.test_recommendation_api import (
    authenticated_client,
    make_profile,
    make_scheme,
    make_user,
)
from apps.schemes.models import SchemeVersion

pytestmark = pytest.mark.django_db


def generate_current_set(*, owner, profile, scheme_count=1):
    for index in range(scheme_count):
        make_scheme(
            key=f"retrieval-{owner.username}-{index}",
        )
    return generate_recommendations(
        startup_profile=profile,
        requested_by=owner,
        assessment_date=date(2026, 7, 20),
    )


def test_owner_retrieves_current_set_without_database_writes():
    owner = make_user(username="retrieval-owner")
    profile = make_profile(
        owner=owner,
        name="Retrieval Owner Startup",
    )
    generation = generate_current_set(
        owner=owner,
        profile=profile,
        scheme_count=2,
    )
    client = authenticated_client(owner)

    assessment_count = EligibilityAssessment.objects.count()
    recommendation_count = Recommendation.objects.count()

    response = client.get(
        reverse("recommendation-current"),
        {"startup_profile_id": str(profile.id)},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["startup_profile_id"] == str(profile.id)
    assert response.data["has_generation"] is True
    assert response.data["generation_id"] == str(generation.generation_id)
    assert response.data["ranking_version"] == RANKING_VERSION
    assert response.data["assessment_date"] == "2026-07-20"
    assert response.data["generated_at"] is not None
    assert response.data["assessed_scheme_count"] == 2
    assert response.data["recommendation_count"] == 2
    assert response.data["excluded_scheme_count"] == 0
    assert response.data["excluded_schemes"] == []
    assert [item["rank"] for item in response.data["recommendations"]] == [1, 2]
    assert EligibilityAssessment.objects.count() == assessment_count
    assert Recommendation.objects.count() == recommendation_count


def test_never_generated_empty_state_returns_200():
    owner = make_user(username="retrieval-empty-owner")
    profile = make_profile(
        owner=owner,
        name="Retrieval Empty Startup",
    )

    response = authenticated_client(owner).get(
        reverse("recommendation-current"),
        {"startup_profile_id": str(profile.id)},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "startup_profile_id": str(profile.id),
        "has_generation": False,
        "generation_id": None,
        "ranking_version": None,
        "assessment_date": None,
        "generated_at": None,
        "assessed_scheme_count": 0,
        "recommendation_count": 0,
        "excluded_scheme_count": 0,
        "excluded_schemes": [],
        "recommendations": [],
    }


def test_zero_result_generation_is_not_never_generated():
    owner = make_user(username="retrieval-zero-owner")
    profile = make_profile(
        owner=owner,
        name="Retrieval Zero Startup",
    )
    make_scheme(key="retrieval-zero")
    version = SchemeVersion.objects.get()
    version.application_status = SchemeVersion.ApplicationStatus.UPCOMING
    version.save(
        update_fields=[
            "application_status",
            "updated_at",
        ]
    )
    generation = generate_recommendations(
        startup_profile=profile,
        requested_by=owner,
        assessment_date=date(2026, 7, 20),
    )

    response = authenticated_client(owner).get(
        reverse("recommendation-current"),
        {"startup_profile_id": str(profile.id)},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["has_generation"] is True
    assert response.data["generation_id"] == str(generation.generation_id)
    assert response.data["assessed_scheme_count"] == 1
    assert response.data["recommendation_count"] == 0
    assert response.data["excluded_scheme_count"] == 1
    assert response.data["recommendations"] == []


def test_other_user_receives_404_for_unowned_profile():
    owner = make_user(username="retrieval-private-owner")
    other = make_user(username="retrieval-private-other")
    profile = make_profile(
        owner=owner,
        name="Retrieval Private Startup",
    )
    generate_current_set(owner=owner, profile=profile)

    response = authenticated_client(other).get(
        reverse("recommendation-current"),
        {"startup_profile_id": str(profile.id)},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_staff_can_retrieve_another_users_profile():
    owner = make_user(username="retrieval-staff-owner")
    staff = make_user(
        username="retrieval-staff",
        is_staff=True,
    )
    profile = make_profile(
        owner=owner,
        name="Retrieval Staff Startup",
    )
    generate_current_set(owner=owner, profile=profile)

    response = authenticated_client(staff).get(
        reverse("recommendation-current"),
        {"startup_profile_id": str(profile.id)},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["recommendation_count"] == 1


def test_missing_profile_id_is_rejected():
    owner = make_user(username="retrieval-missing-owner")

    response = authenticated_client(owner).get(
        reverse("recommendation-current"),
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "startup_profile_id" in response.data


def test_inconsistent_current_set_returns_409():
    owner = make_user(username="retrieval-conflict-owner")
    profile = make_profile(
        owner=owner,
        name="Retrieval Conflict Startup",
    )
    generate_current_set(
        owner=owner,
        profile=profile,
        scheme_count=2,
    )
    second = Recommendation.objects.get(rank=2)
    second.generation_id = uuid.uuid4()
    second.save(
        update_fields=[
            "generation_id",
            "updated_at",
        ]
    )

    response = authenticated_client(owner).get(
        reverse("recommendation-current"),
        {"startup_profile_id": str(profile.id)},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert "do not match the run ID" in response.data["detail"]


def test_unauthenticated_request_is_rejected():
    response = APIClient().get(
        reverse("recommendation-current"),
        {"startup_profile_id": str(uuid.uuid4())},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
