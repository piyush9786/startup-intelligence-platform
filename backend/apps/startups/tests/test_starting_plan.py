from datetime import date

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.recommendations.models import RecommendationGenerationRun
from apps.startups.models import StartupStartingPlan
from apps.startups.services import (
    StartingPlanSourceError,
    create_startup_readiness_action_plan,
    create_startup_readiness_assessment,
    create_startup_starting_plan,
)
from apps.startups.tests.test_readiness_assessment_api import (
    authenticated_client,
    make_profile,
    make_user,
)

pytestmark = pytest.mark.django_db


def recommendation_snapshot(*, rank: int, scheme_name: str) -> dict:
    return {
        "recommendation_id": f"00000000-0000-0000-0000-{rank:012d}",
        "assessment_id": f"10000000-0000-0000-0000-{rank:012d}",
        "scheme_id": f"20000000-0000-0000-0000-{rank:012d}",
        "scheme_version_id": f"30000000-0000-0000-0000-{rank:012d}",
        "rank": rank,
        "score": f"0.{90 - rank:02d}0000",
        "score_breakdown": {
            "ranking_version": "recommendations-v1",
        },
        "evidence_snapshot": {
            "scheme_id": f"20000000-0000-0000-0000-{rank:012d}",
            "scheme_version_id": f"30000000-0000-0000-0000-{rank:012d}",
            "scheme_name": scheme_name,
            "eligibility_engine_version": "rules-v5",
        },
    }


def make_sources(*, owner, name: str = "Starting Plan Startup"):
    profile = make_profile(
        owner=owner,
        name=name,
    )
    profile.description = ""
    profile.save(
        update_fields=[
            "description",
            "updated_at",
        ]
    )
    assessment = create_startup_readiness_assessment(
        startup_profile=profile,
        requested_by=owner,
        assessment_date=date(2026, 7, 23),
    )
    action_plan = create_startup_readiness_action_plan(
        source_assessment=assessment,
        requested_by=owner,
    )
    snapshots = [
        recommendation_snapshot(
            rank=2,
            scheme_name="Second Scheme",
        ),
        recommendation_snapshot(
            rank=1,
            scheme_name="First Scheme",
        ),
    ]
    generation_run = RecommendationGenerationRun.objects.create(
        requested_by=owner,
        startup_profile=profile,
        assessment_date=date(2026, 7, 23),
        ranking_version="recommendations-v1",
        profile_snapshot=assessment.profile_snapshot,
        assessed_scheme_count=2,
        recommendation_count=2,
        excluded_schemes=[],
        recommendation_snapshot=snapshots,
        is_current=True,
    )
    return profile, assessment, action_plan, generation_run


def create_plan(*, owner, name: str = "Starting Plan Startup"):
    profile, assessment, action_plan, generation_run = make_sources(
        owner=owner,
        name=name,
    )
    result = create_startup_starting_plan(
        source_assessment=assessment,
        source_action_plan=action_plan,
        recommendation_generation_run=generation_run,
        requested_by=owner,
    )
    return profile, assessment, action_plan, generation_run, result


def test_plan_composes_deterministic_sources_with_provenance():
    owner = make_user(username="starting-plan-service-owner")
    profile, assessment, action_plan, generation_run, result = create_plan(
        owner=owner,
    )

    assert result.created is True
    plan = result.plan
    assert plan.startup_profile == profile
    assert plan.source_assessment == assessment
    assert plan.source_action_plan == action_plan
    assert plan.recommendation_generation_run == generation_run
    assert plan.plan_version == "startup-starting-plan-v1"
    assert plan.readiness_item_count == action_plan.total_action_count
    assert plan.recommendation_item_count == 2
    assert plan.total_item_count == (
        plan.readiness_item_count + plan.recommendation_item_count
    )
    assert plan.next_item == plan.items[0]
    assert all(
        item["dependency_status"] == "not_evaluated"
        for item in plan.items
    )

    readiness_items = plan.items[: plan.readiness_item_count]
    recommendation_items = plan.items[plan.readiness_item_count :]
    assert all(item["item_type"] == "readiness_action" for item in readiness_items)
    assert [item["title"] for item in recommendation_items] == [
        "Review First Scheme",
        "Review Second Scheme",
    ]
    assert recommendation_items[0]["source"]["generation_id"] == str(
        generation_run.id
    )
    assert recommendation_items[0]["source"]["ranking_version"] == (
        "recommendations-v1"
    )


def test_same_sources_are_idempotent():
    owner = make_user(username="starting-plan-idempotent-owner")
    _profile, assessment, action_plan, generation_run, first = create_plan(
        owner=owner,
    )

    second = create_startup_starting_plan(
        source_assessment=assessment,
        source_action_plan=action_plan,
        recommendation_generation_run=generation_run,
        requested_by=owner,
    )

    assert second.created is False
    assert second.plan.pk == first.plan.pk
    assert StartupStartingPlan.objects.count() == 1


def test_mismatched_sources_are_rejected():
    owner = make_user(username="starting-plan-mismatch-owner")
    _profile, assessment, action_plan, _generation_run = make_sources(
        owner=owner,
        name="Starting Plan Source One",
    )
    _other_profile, _other_assessment, _other_action_plan, other_generation = (
        make_sources(
            owner=owner,
            name="Starting Plan Source Two",
        )
    )

    with pytest.raises(StartingPlanSourceError):
        create_startup_starting_plan(
            source_assessment=assessment,
            source_action_plan=action_plan,
            recommendation_generation_run=other_generation,
            requested_by=owner,
        )

    assert StartupStartingPlan.objects.count() == 0


def test_generate_current_history_and_detail_apis():
    owner = make_user(username="starting-plan-api-owner")
    profile, _assessment, _action_plan, _generation_run = make_sources(
        owner=owner,
        name="Starting Plan API Startup",
    )
    client = authenticated_client(owner)

    first_response = client.post(
        reverse("startup-starting-plan-generate"),
        {
            "startup_profile_id": str(profile.id),
        },
        format="json",
    )
    second_response = client.post(
        reverse("startup-starting-plan-generate"),
        {
            "startup_profile_id": str(profile.id),
        },
        format="json",
    )

    assert first_response.status_code == status.HTTP_201_CREATED
    assert first_response.data["created"] is True
    assert second_response.status_code == status.HTTP_200_OK
    assert second_response.data["created"] is False
    assert second_response.data["id"] == first_response.data["id"]

    current_response = client.get(
        reverse("startup-starting-plan-current"),
        {
            "startup_profile_id": str(profile.id),
        },
    )
    history_response = client.get(
        reverse("startup-starting-plan-list"),
        {
            "startup_profile_id": str(profile.id),
        },
    )
    detail_response = client.get(
        reverse(
            "startup-starting-plan-detail",
            kwargs={
                "starting_plan_id": first_response.data["id"],
            },
        )
    )

    assert current_response.status_code == status.HTTP_200_OK
    assert current_response.data["has_starting_plan"] is True
    assert current_response.data["starting_plan"]["id"] == first_response.data["id"]
    assert history_response.status_code == status.HTTP_200_OK
    assert history_response.data["count"] == 1
    assert detail_response.status_code == status.HTTP_200_OK
    assert detail_response.data["items"] == first_response.data["items"]


def test_current_api_returns_empty_payload_before_generation():
    owner = make_user(username="starting-plan-empty-owner")
    profile = make_profile(
        owner=owner,
        name="Starting Plan Empty Startup",
    )

    response = authenticated_client(owner).get(
        reverse("startup-starting-plan-current"),
        {
            "startup_profile_id": str(profile.id),
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "startup_profile_id": str(profile.id),
        "has_starting_plan": False,
        "starting_plan": None,
    }


def test_other_founder_cannot_access_starting_plan():
    owner = make_user(username="starting-plan-private-owner")
    other = make_user(username="starting-plan-private-other")
    profile, _assessment, _action_plan, _generation_run, result = create_plan(
        owner=owner,
        name="Starting Plan Private Startup",
    )
    client = authenticated_client(other)

    current_response = client.get(
        reverse("startup-starting-plan-current"),
        {
            "startup_profile_id": str(profile.id),
        },
    )
    detail_response = client.get(
        reverse(
            "startup-starting-plan-detail",
            kwargs={
                "starting_plan_id": result.plan.id,
            },
        )
    )

    assert current_response.status_code == status.HTTP_404_NOT_FOUND
    assert detail_response.status_code == status.HTTP_404_NOT_FOUND


def test_generate_rejects_raw_plan_data_and_missing_sources():
    owner = make_user(username="starting-plan-validation-owner")
    profile = make_profile(
        owner=owner,
        name="Starting Plan Validation Startup",
    )
    client = authenticated_client(owner)

    raw_response = client.post(
        reverse("startup-starting-plan-generate"),
        {
            "startup_profile_id": str(profile.id),
            "recommendations": [],
        },
        format="json",
    )
    missing_response = client.post(
        reverse("startup-starting-plan-generate"),
        {
            "startup_profile_id": str(profile.id),
        },
        format="json",
    )

    assert raw_response.status_code == status.HTTP_400_BAD_REQUEST
    assert "recommendations" in raw_response.data
    assert missing_response.status_code == status.HTTP_400_BAD_REQUEST
    assert "startup_profile_id" in missing_response.data


def test_starting_plan_apis_require_authentication():
    owner = make_user(username="starting-plan-auth-owner")
    profile = make_profile(
        owner=owner,
        name="Starting Plan Auth Startup",
    )

    response = APIClient().get(
        reverse("startup-starting-plan-current"),
        {
            "startup_profile_id": str(profile.id),
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
