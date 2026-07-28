import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.sources.models import (
    Source,
    SourceDocument,
)
from apps.startups.models import (
    StartupFundingPlan,
)
from apps.startups.tests.test_funding_plan_persistence import (
    source_plan,
)
from apps.startups.tests.test_readiness_assessment_api import (
    authenticated_client,
    make_profile,
    make_user,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner():
    return make_user(
        username="funding-plan-api-owner",
    )


@pytest.fixture
def other_founder():
    return make_user(
        username="funding-plan-api-other",
    )


@pytest.fixture
def reviewer():
    return get_user_model().objects.create_user(
        username="funding-plan-api-reviewer",
        email=("funding-plan-api-reviewer@example.com"),
        password="test-password",
        role="reviewer",
    )


@pytest.fixture
def source_document():
    source = Source.objects.create(
        name="Funding plan API source",
        official_domain=("funding-api.example.gov.in"),
        listing_url=("https://funding-api.example.gov.in/schemes"),
        authority_tier=(Source.AuthorityTier.OFFICIAL_PROGRAMME),
    )

    return SourceDocument.objects.create(
        source=source,
        source_url=("https://funding-api.example.gov.in/rules"),
        final_url=("https://funding-api.example.gov.in/rules"),
        title="Funding plan API rules",
        mime_type="text/html",
        content_hash=("funding-plan-api-hash"),
        retrieved_at=timezone.now(),
        status=(SourceDocument.Status.VERIFIED),
    )


def test_generate_is_idempotent_and_returns_plan(
    owner,
    reviewer,
    source_document,
):
    starting_plan, _version = source_plan(
        owner=owner,
        reviewer=reviewer,
        source_document=source_document,
    )
    client = authenticated_client(owner)
    payload = {
        "startup_profile_id": str(starting_plan.startup_profile_id),
        "as_of_date": "2026-07-24",
    }

    first_response = client.post(
        reverse("startup-funding-plan-generate"),
        payload,
        format="json",
    )
    second_response = client.post(
        reverse("startup-funding-plan-generate"),
        payload,
        format="json",
    )

    assert first_response.status_code == status.HTTP_201_CREATED
    assert first_response.data["created"] is True
    assert second_response.status_code == status.HTTP_200_OK
    assert second_response.data["created"] is False
    assert second_response.data["id"] == first_response.data["id"]
    assert first_response.data["plan_version"] == "startup-funding-plan-v1"
    assert first_response.data["as_of_date"] == "2026-07-24"
    assert (
        first_response.data["step_count"]
        == first_response.data["plan_snapshot"]["total_step_count"]
    )
    assert StartupFundingPlan.objects.count() == 1


def test_current_history_and_detail_apis(
    owner,
    reviewer,
    source_document,
):
    starting_plan, _version = source_plan(
        owner=owner,
        reviewer=reviewer,
        source_document=source_document,
    )
    client = authenticated_client(owner)
    profile_id = str(starting_plan.startup_profile_id)

    first_response = client.post(
        reverse("startup-funding-plan-generate"),
        {
            "startup_profile_id": profile_id,
            "as_of_date": "2026-07-24",
        },
        format="json",
    )
    second_response = client.post(
        reverse("startup-funding-plan-generate"),
        {
            "startup_profile_id": profile_id,
            "as_of_date": "2026-07-25",
        },
        format="json",
    )

    current_response = client.get(
        reverse("startup-funding-plan-current"),
        {
            "startup_profile_id": profile_id,
        },
    )
    history_response = client.get(
        reverse("startup-funding-plan-list"),
        {
            "startup_profile_id": profile_id,
        },
    )
    detail_response = client.get(
        reverse(
            "startup-funding-plan-detail",
            kwargs={
                "funding_plan_id": (first_response.data["id"]),
            },
        )
    )

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_201_CREATED
    assert current_response.status_code == status.HTTP_200_OK
    assert current_response.data["has_funding_plan"] is True
    assert current_response.data["funding_plan"]["id"] == second_response.data["id"]
    assert history_response.status_code == status.HTTP_200_OK
    assert history_response.data["count"] == 2
    assert detail_response.status_code == status.HTTP_200_OK
    assert detail_response.data["id"] == first_response.data["id"]


def test_current_returns_empty_before_generation(
    owner,
):
    profile = make_profile(
        owner=owner,
        name="Funding Plan Empty Startup",
    )

    response = authenticated_client(owner).get(
        reverse("startup-funding-plan-current"),
        {
            "startup_profile_id": str(profile.id),
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "startup_profile_id": str(profile.id),
        "has_funding_plan": False,
        "funding_plan": None,
    }


def test_generate_requires_current_starting_plan(
    owner,
):
    profile = make_profile(
        owner=owner,
        name="Funding Plan Missing Source",
    )

    response = authenticated_client(owner).post(
        reverse("startup-funding-plan-generate"),
        {
            "startup_profile_id": str(profile.id),
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "startup_profile_id" in response.data


def test_generate_rejects_raw_plan_data(
    owner,
):
    profile = make_profile(
        owner=owner,
        name="Funding Plan Raw Input",
    )

    response = authenticated_client(owner).post(
        reverse("startup-funding-plan-generate"),
        {
            "startup_profile_id": str(profile.id),
            "steps": [],
            "dependencies": [],
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "steps" in response.data
    assert "dependencies" in response.data


def test_other_founder_cannot_access_plan(
    owner,
    other_founder,
    reviewer,
    source_document,
):
    starting_plan, _version = source_plan(
        owner=owner,
        reviewer=reviewer,
        source_document=source_document,
    )
    owner_client = authenticated_client(owner)
    generated = owner_client.post(
        reverse("startup-funding-plan-generate"),
        {
            "startup_profile_id": str(starting_plan.startup_profile_id),
            "as_of_date": "2026-07-24",
        },
        format="json",
    )
    other_client = authenticated_client(other_founder)

    current_response = other_client.get(
        reverse("startup-funding-plan-current"),
        {
            "startup_profile_id": str(starting_plan.startup_profile_id),
        },
    )
    detail_response = other_client.get(
        reverse(
            "startup-funding-plan-detail",
            kwargs={
                "funding_plan_id": (generated.data["id"]),
            },
        )
    )

    assert current_response.status_code == status.HTTP_404_NOT_FOUND
    assert detail_response.status_code == status.HTTP_404_NOT_FOUND


def test_funding_plan_apis_require_authentication(
    owner,
):
    profile = make_profile(
        owner=owner,
        name="Funding Plan Auth Startup",
    )

    generate_response = APIClient().post(
        reverse("startup-funding-plan-generate"),
        {
            "startup_profile_id": str(profile.id),
        },
        format="json",
    )
    current_response = APIClient().get(
        reverse("startup-funding-plan-current"),
        {
            "startup_profile_id": str(profile.id),
        },
    )

    assert generate_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert current_response.status_code == status.HTTP_401_UNAUTHORIZED
