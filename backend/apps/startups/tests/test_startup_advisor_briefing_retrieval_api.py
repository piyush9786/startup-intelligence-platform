import uuid
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.recommendations.tests.test_recommendation_api import (
    authenticated_client,
    make_profile,
    make_user,
)
from apps.startups.models import (
    StartupAdvisorBriefing,
    StartupAdvisorSnapshot,
    StartupReadinessActionPlan,
    StartupReadinessAssessment,
)
from apps.startups.services import create_startup_advisor_snapshot

pytestmark = pytest.mark.django_db


def current_url():
    return reverse("startup-advisor-briefing-current")


def list_url():
    return reverse("startup-advisor-briefing-list")


def detail_url(briefing):
    return reverse(
        "startup-advisor-briefing-detail",
        kwargs={"briefing_id": briefing.id},
    )


def create_source(*, username):
    owner = make_user(username=username)
    profile = make_profile(owner=owner, name=f"{username} Startup")
    snapshot = create_startup_advisor_snapshot(
        startup_profile=profile,
        requested_by=owner,
    )
    return owner, profile, snapshot


def create_briefing(*, profile, snapshot, requested_by, marker, completed_at):
    return StartupAdvisorBriefing.objects.create(
        requested_by=requested_by,
        startup_profile=profile,
        source_snapshot=snapshot,
        provider="ollama",
        model_name=f"qwen-test-{marker}",
        prompt_version="startup-advisor-briefing-prompt-v1",
        schema_version="startup-advisor-briefing-schema-v1",
        generation_parameters={"temperature": 0, "seed": 7},
        prompt_snapshot={
            "marker": marker,
            "source_snapshot_id": str(snapshot.id),
        },
        briefing={
            "executive_summary": f"Summary {marker}",
            "current_position": f"Position {marker}",
            "top_priorities": [],
            "scheme_guidance": [],
            "risks": [],
            "questions_for_founder": [],
            "disclaimer": f"Disclaimer {marker}",
        },
        prompt_token_count=100,
        output_token_count=40,
        total_duration_ns=1234,
        response_metadata={"done": True, "marker": marker},
        completed_at=completed_at,
    )


def test_current_returns_explicit_empty_state():
    owner, profile, _snapshot = create_source(
        username="briefing-current-empty",
    )
    response = authenticated_client(owner).get(
        current_url(),
        {"startup_profile_id": str(profile.id)},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "startup_profile_id": str(profile.id),
        "has_briefing": False,
        "briefing": None,
    }


def test_current_returns_latest_complete_briefing():
    owner, profile, snapshot = create_source(
        username="briefing-current-latest",
    )
    now = timezone.now()
    older = create_briefing(
        profile=profile,
        snapshot=snapshot,
        requested_by=owner,
        marker="older",
        completed_at=now - timedelta(hours=1),
    )
    latest = create_briefing(
        profile=profile,
        snapshot=snapshot,
        requested_by=owner,
        marker="latest",
        completed_at=now,
    )
    response = authenticated_client(owner).get(
        current_url(),
        {"startup_profile_id": str(profile.id)},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["has_briefing"] is True
    assert response.data["briefing"]["id"] == str(latest.id)
    assert response.data["briefing"]["id"] != str(older.id)
    assert response.data["briefing"]["prompt_snapshot"]["marker"] == "latest"
    assert response.data["briefing"]["briefing"]["executive_summary"] == ("Summary latest")


def test_list_returns_history_newest_first():
    owner, profile, snapshot = create_source(
        username="briefing-list-history",
    )
    now = timezone.now()
    older = create_briefing(
        profile=profile,
        snapshot=snapshot,
        requested_by=owner,
        marker="older",
        completed_at=now - timedelta(days=1),
    )
    latest = create_briefing(
        profile=profile,
        snapshot=snapshot,
        requested_by=owner,
        marker="latest",
        completed_at=now,
    )
    response = authenticated_client(owner).get(
        list_url(),
        {"startup_profile_id": str(profile.id)},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2
    assert [item["id"] for item in response.data["briefings"]] == [
        str(latest.id),
        str(older.id),
    ]
    assert response.data["briefings"][0]["prompt_token_count"] == 100
    assert response.data["briefings"][0]["response_metadata"]["marker"] == ("latest")


def test_list_returns_empty_history():
    owner, profile, _snapshot = create_source(
        username="briefing-list-empty",
    )
    response = authenticated_client(owner).get(
        list_url(),
        {"startup_profile_id": str(profile.id)},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "startup_profile_id": str(profile.id),
        "count": 0,
        "briefings": [],
    }


def test_detail_returns_complete_persisted_briefing():
    owner, profile, snapshot = create_source(
        username="briefing-detail-owner",
    )
    briefing = create_briefing(
        profile=profile,
        snapshot=snapshot,
        requested_by=owner,
        marker="detail",
        completed_at=timezone.now(),
    )
    response = authenticated_client(owner).get(detail_url(briefing))
    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(briefing.id)
    assert response.data["startup_profile_id"] == str(profile.id)
    assert response.data["source_snapshot_id"] == str(snapshot.id)
    assert response.data["model_name"] == "qwen-test-detail"
    assert response.data["prompt_snapshot"]["marker"] == "detail"


@pytest.mark.parametrize(
    "url_name",
    [
        "startup-advisor-briefing-current",
        "startup-advisor-briefing-list",
    ],
)
def test_other_user_profile_queries_return_404(url_name):
    _owner, profile, _snapshot = create_source(
        username=f"briefing-private-{url_name}",
    )
    other = make_user(username=f"briefing-other-{url_name}")
    response = authenticated_client(other).get(
        reverse(url_name),
        {"startup_profile_id": str(profile.id)},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_other_user_detail_returns_404():
    owner, profile, snapshot = create_source(
        username="briefing-private-detail-owner",
    )
    other = make_user(username="briefing-private-detail-other")
    briefing = create_briefing(
        profile=profile,
        snapshot=snapshot,
        requested_by=owner,
        marker="private",
        completed_at=timezone.now(),
    )
    response = authenticated_client(other).get(detail_url(briefing))
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_staff_can_access_all_retrieval_endpoints():
    owner, profile, snapshot = create_source(
        username="briefing-staff-owner",
    )
    staff = make_user(username="briefing-staff-user", is_staff=True)
    briefing = create_briefing(
        profile=profile,
        snapshot=snapshot,
        requested_by=owner,
        marker="staff",
        completed_at=timezone.now(),
    )
    client = authenticated_client(staff)
    current_response = client.get(
        current_url(),
        {"startup_profile_id": str(profile.id)},
    )
    list_response = client.get(
        list_url(),
        {"startup_profile_id": str(profile.id)},
    )
    detail_response = client.get(detail_url(briefing))
    assert current_response.status_code == status.HTTP_200_OK
    assert list_response.status_code == status.HTTP_200_OK
    assert detail_response.status_code == status.HTTP_200_OK


@pytest.mark.parametrize(
    "url_name",
    [
        "startup-advisor-briefing-current",
        "startup-advisor-briefing-list",
    ],
)
def test_unknown_profile_returns_404(url_name):
    user = make_user(username=f"briefing-unknown-{url_name}")
    response = authenticated_client(user).get(
        reverse(url_name),
        {"startup_profile_id": "00000000-0000-0000-0000-000000000001"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_unknown_briefing_returns_404():
    user = make_user(username="briefing-unknown-detail")
    response = authenticated_client(user).get(
        reverse(
            "startup-advisor-briefing-detail",
            kwargs={"briefing_id": uuid.uuid4()},
        )
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize(
    ("url_name", "kwargs", "query"),
    [
        (
            "startup-advisor-briefing-current",
            {},
            {"startup_profile_id": str(uuid.uuid4())},
        ),
        (
            "startup-advisor-briefing-list",
            {},
            {"startup_profile_id": str(uuid.uuid4())},
        ),
        (
            "startup-advisor-briefing-detail",
            {"briefing_id": uuid.uuid4()},
            {},
        ),
    ],
)
def test_unauthenticated_requests_are_rejected(url_name, kwargs, query):
    response = APIClient().get(reverse(url_name, kwargs=kwargs), query)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_retrieval_performs_no_writes_or_llm_calls(monkeypatch):
    owner, profile, snapshot = create_source(
        username="briefing-read-only-owner",
    )
    briefing = create_briefing(
        profile=profile,
        snapshot=snapshot,
        requested_by=owner,
        marker="read-only",
        completed_at=timezone.now(),
    )

    def unexpected_generation(*args, **kwargs):
        raise AssertionError("Retrieval must not invoke LLM generation.")

    monkeypatch.setattr(
        "apps.startups.advisor_views.generate_startup_advisor_briefing",
        unexpected_generation,
    )
    counts_before = {
        "briefings": StartupAdvisorBriefing.objects.count(),
        "snapshots": StartupAdvisorSnapshot.objects.count(),
        "readiness": StartupReadinessAssessment.objects.count(),
        "plans": StartupReadinessActionPlan.objects.count(),
    }
    client = authenticated_client(owner)
    responses = [
        client.get(
            current_url(),
            {"startup_profile_id": str(profile.id)},
        ),
        client.get(
            list_url(),
            {"startup_profile_id": str(profile.id)},
        ),
        client.get(detail_url(briefing)),
    ]
    counts_after = {
        "briefings": StartupAdvisorBriefing.objects.count(),
        "snapshots": StartupAdvisorSnapshot.objects.count(),
        "readiness": StartupReadinessAssessment.objects.count(),
        "plans": StartupReadinessActionPlan.objects.count(),
    }
    assert all(response.status_code == status.HTTP_200_OK for response in responses)
    assert counts_after == counts_before
