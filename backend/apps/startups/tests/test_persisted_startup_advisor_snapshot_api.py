import uuid
from datetime import date

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.recommendations.models import (
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
from apps.startups.models import StartupAdvisorSnapshot
from apps.startups.services import (
    create_startup_readiness_action_plan,
    create_startup_readiness_assessment,
)

pytestmark = pytest.mark.django_db


def generate_url():
    return reverse("startup-advisor-snapshot-generate")


def create_guidance(*, owner, name: str):
    profile = make_profile(
        owner=owner,
        name=name,
    )
    assessment = create_startup_readiness_assessment(
        startup_profile=profile,
        requested_by=owner,
        assessment_date=date(2026, 7, 21),
    )
    action_plan = create_startup_readiness_action_plan(
        source_assessment=assessment,
        requested_by=owner,
    )
    make_scheme(key=f"advisor-api-{owner.username}")
    generate_recommendations(
        startup_profile=profile,
        requested_by=owner,
        assessment_date=date(2026, 7, 21),
    )
    generation_run = RecommendationGenerationRun.objects.get(
        startup_profile=profile,
        is_current=True,
    )
    recommendation = Recommendation.objects.get(
        generation_run=generation_run,
    )
    return (
        profile,
        assessment,
        action_plan,
        generation_run,
        recommendation,
    )


def test_owner_can_generate_persisted_advisor_snapshot():
    owner = make_user(username="advisor-snapshot-api-owner")
    (
        profile,
        assessment,
        action_plan,
        generation_run,
        recommendation,
    ) = create_guidance(
        owner=owner,
        name="Advisor Snapshot API Startup",
    )

    response = authenticated_client(owner).post(
        generate_url(),
        {"startup_profile_id": str(profile.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["startup_profile_id"] == str(profile.id)
    assert response.data["requested_by_id"] == str(owner.id)
    assert response.data["readiness_assessment_id"] == str(assessment.id)
    assert response.data["readiness_action_plan_id"] == str(action_plan.id)
    assert response.data["recommendation_generation_run_id"] == str(generation_run.id)
    assert response.data["has_readiness_assessment"] is True
    assert response.data["has_action_plan"] is True
    assert response.data["has_recommendation_generation"] is True
    assert response.data["recommendation_count"] == 1
    assert response.data["recommendations_snapshot"][0]["id"] == str(recommendation.id)
    assert StartupAdvisorSnapshot.objects.count() == 1


def test_empty_guidance_can_be_snapshotted():
    owner = make_user(username="advisor-snapshot-api-empty")
    profile = make_profile(
        owner=owner,
        name="Advisor Snapshot API Empty Startup",
    )

    response = authenticated_client(owner).post(
        generate_url(),
        {"startup_profile_id": str(profile.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["has_readiness_assessment"] is False
    assert response.data["readiness_snapshot"] == {}
    assert response.data["has_action_plan"] is False
    assert response.data["action_plan_snapshot"] == {}
    assert response.data["has_recommendation_generation"] is False
    assert response.data["recommendation_generation_snapshot"] == {}
    assert response.data["recommendations_snapshot"] == []


def test_other_user_receives_404():
    owner = make_user(username="advisor-snapshot-api-private-owner")
    other = make_user(username="advisor-snapshot-api-private-other")
    profile = make_profile(
        owner=owner,
        name="Advisor Snapshot API Private Startup",
    )

    response = authenticated_client(other).post(
        generate_url(),
        {"startup_profile_id": str(profile.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert StartupAdvisorSnapshot.objects.count() == 0


def test_staff_can_generate_for_another_user():
    owner = make_user(username="advisor-snapshot-api-staff-owner")
    staff = make_user(
        username="advisor-snapshot-api-staff",
        is_staff=True,
    )
    profile = make_profile(
        owner=owner,
        name="Advisor Snapshot API Staff Startup",
    )

    response = authenticated_client(staff).post(
        generate_url(),
        {"startup_profile_id": str(profile.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    snapshot = StartupAdvisorSnapshot.objects.get()
    assert snapshot.startup_profile == profile
    assert snapshot.requested_by == staff


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("profile", {"startup_name": "Forged"}),
        ("readiness", {"has_assessment": True}),
        ("assessment", {"score": 100}),
        ("action_plan", {"items": []}),
        ("recommendations", [{"rank": 1}]),
        ("generation", {"is_current": True}),
    ],
)
def test_raw_advisor_payloads_are_rejected(
    field_name,
    field_value,
):
    owner = make_user(username=f"advisor-snapshot-api-raw-{field_name}")
    profile = make_profile(
        owner=owner,
        name=f"Advisor Snapshot Raw {field_name}",
    )

    response = authenticated_client(owner).post(
        generate_url(),
        {
            "startup_profile_id": str(profile.id),
            field_name: field_value,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert field_name in response.data
    assert StartupAdvisorSnapshot.objects.count() == 0


def test_unknown_profile_returns_404():
    owner = make_user(username="advisor-snapshot-api-unknown")

    response = authenticated_client(owner).post(
        generate_url(),
        {"startup_profile_id": ("00000000-0000-0000-0000-000000000001")},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert StartupAdvisorSnapshot.objects.count() == 0


def test_inconsistent_recommendations_return_409():
    owner = make_user(username="advisor-snapshot-api-conflict")
    (
        profile,
        _assessment,
        _action_plan,
        _generation_run,
        recommendation,
    ) = create_guidance(
        owner=owner,
        name="Advisor Snapshot API Conflict Startup",
    )
    recommendation.generation_id = uuid.uuid4()
    recommendation.save(
        update_fields=[
            "generation_id",
            "updated_at",
        ]
    )

    response = authenticated_client(owner).post(
        generate_url(),
        {"startup_profile_id": str(profile.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert "do not match the run ID" in response.data["detail"]
    assert StartupAdvisorSnapshot.objects.count() == 0


def test_repeated_generation_retains_history():
    owner = make_user(username="advisor-snapshot-api-history")
    profile = make_profile(
        owner=owner,
        name="Advisor Snapshot API History Startup",
    )
    client = authenticated_client(owner)

    first = client.post(
        generate_url(),
        {"startup_profile_id": str(profile.id)},
        format="json",
    )
    second = client.post(
        generate_url(),
        {"startup_profile_id": str(profile.id)},
        format="json",
    )

    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_201_CREATED
    assert first.data["id"] != second.data["id"]
    assert StartupAdvisorSnapshot.objects.count() == 2


def test_unauthenticated_request_is_rejected():
    response = APIClient().post(
        generate_url(),
        {"startup_profile_id": str(uuid.uuid4())},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert StartupAdvisorSnapshot.objects.count() == 0
