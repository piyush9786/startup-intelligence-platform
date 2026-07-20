from datetime import date

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.recommendations.models import (
    EligibilityAssessment,
    Recommendation,
    RecommendationGenerationRun,
)
from apps.recommendations.services import generate_recommendations
from apps.recommendations.tests.test_recommendation_api import (
    authenticated_client,
    make_profile,
    make_scheme,
    make_user,
)

pytestmark = pytest.mark.django_db


def make_run_history(*, owner, profile):
    make_scheme(key=f"history-{owner.username}")
    first = generate_recommendations(
        startup_profile=profile,
        requested_by=owner,
        assessment_date=date(2026, 7, 20),
    )
    second = generate_recommendations(
        startup_profile=profile,
        requested_by=owner,
        assessment_date=date(2026, 7, 21),
    )
    first.generation_run.refresh_from_db()
    second.generation_run.refresh_from_db()
    return first.generation_run, second.generation_run


def test_owner_lists_runs_newest_first_without_writes():
    owner = make_user(username="history-list-owner")
    profile = make_profile(owner=owner, name="History List Startup")
    first, second = make_run_history(owner=owner, profile=profile)
    client = authenticated_client(owner)

    run_count = RecommendationGenerationRun.objects.count()
    assessment_count = EligibilityAssessment.objects.count()
    recommendation_count = Recommendation.objects.count()

    response = client.get(
        reverse("recommendation-run-list"),
        {"startup_profile_id": str(profile.id)},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["startup_profile_id"] == str(profile.id)
    assert response.data["count"] == 2
    assert [item["generation_id"] for item in response.data["runs"]] == [
        str(second.id),
        str(first.id),
    ]
    assert response.data["runs"][0]["is_current"] is True
    assert response.data["runs"][1]["is_current"] is False
    assert RecommendationGenerationRun.objects.count() == run_count
    assert EligibilityAssessment.objects.count() == assessment_count
    assert Recommendation.objects.count() == recommendation_count


def test_owner_lists_empty_history():
    owner = make_user(username="history-empty-owner")
    profile = make_profile(owner=owner, name="History Empty Startup")

    response = authenticated_client(owner).get(
        reverse("recommendation-run-list"),
        {"startup_profile_id": str(profile.id)},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "startup_profile_id": str(profile.id),
        "count": 0,
        "runs": [],
    }


def test_other_user_cannot_list_profile_history():
    owner = make_user(username="history-private-owner")
    other = make_user(username="history-private-other")
    profile = make_profile(owner=owner, name="History Private Startup")
    make_run_history(owner=owner, profile=profile)

    response = authenticated_client(other).get(
        reverse("recommendation-run-list"),
        {"startup_profile_id": str(profile.id)},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_staff_can_list_another_users_history():
    owner = make_user(username="history-staff-owner")
    staff = make_user(username="history-staff", is_staff=True)
    profile = make_profile(owner=owner, name="History Staff Startup")
    make_run_history(owner=owner, profile=profile)

    response = authenticated_client(staff).get(
        reverse("recommendation-run-list"),
        {"startup_profile_id": str(profile.id)},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2


def test_owner_retrieves_historical_run_detail():
    owner = make_user(username="history-detail-owner")
    profile = make_profile(owner=owner, name="History Detail Startup")
    first, _ = make_run_history(owner=owner, profile=profile)

    response = authenticated_client(owner).get(
        reverse(
            "recommendation-run-detail",
            kwargs={"run_id": first.id},
        )
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["generation_id"] == str(first.id)
    assert response.data["startup_profile_id"] == str(profile.id)
    assert response.data["requested_by_id"] == str(owner.id)
    assert response.data["assessment_date"] == "2026-07-20"
    assert response.data["is_current"] is False
    assert response.data["assessed_scheme_count"] == 1
    assert response.data["recommendation_count"] == 1
    assert response.data["excluded_scheme_count"] == 0
    assert response.data["profile_snapshot"]["startup_name"] == profile.startup_name
    assert len(response.data["recommendation_snapshot"]) == 1


def test_other_user_cannot_retrieve_run_detail():
    owner = make_user(username="history-detail-private-owner")
    other = make_user(username="history-detail-private-other")
    profile = make_profile(owner=owner, name="History Detail Private Startup")
    first, _ = make_run_history(owner=owner, profile=profile)

    response = authenticated_client(other).get(
        reverse(
            "recommendation-run-detail",
            kwargs={"run_id": first.id},
        )
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_staff_can_retrieve_another_users_run_detail():
    owner = make_user(username="history-detail-staff-owner")
    staff = make_user(username="history-detail-staff", is_staff=True)
    profile = make_profile(owner=owner, name="History Detail Staff Startup")
    first, _ = make_run_history(owner=owner, profile=profile)

    response = authenticated_client(staff).get(
        reverse(
            "recommendation-run-detail",
            kwargs={"run_id": first.id},
        )
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["generation_id"] == str(first.id)


def test_history_endpoints_require_authentication():
    owner = make_user(username="history-auth-owner")
    profile = make_profile(owner=owner, name="History Auth Startup")
    first, _ = make_run_history(owner=owner, profile=profile)
    client = APIClient()

    list_response = client.get(
        reverse("recommendation-run-list"),
        {"startup_profile_id": str(profile.id)},
    )
    detail_response = client.get(
        reverse(
            "recommendation-run-detail",
            kwargs={"run_id": first.id},
        )
    )

    assert list_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert detail_response.status_code == status.HTTP_401_UNAUTHORIZED
