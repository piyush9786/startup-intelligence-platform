import uuid
from copy import deepcopy

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.recommendations.tests.test_recommendation_api import (
    authenticated_client,
    make_profile,
    make_user,
)
from apps.startups.models import StartupAdvisorBriefing
from apps.startups.services import (
    BRIEFING_DISCLAIMER,
    LLMGenerationResult,
    LLMProviderUnavailableError,
    create_startup_advisor_snapshot,
)

pytestmark = pytest.mark.django_db


class FakeProvider:
    def __init__(self, payload):
        self.payload = payload

    @property
    def generation_parameters(self):
        return {
            "temperature": 0,
            "seed": 7,
            "think": False,
        }

    def generate(self, *, messages, response_schema):
        return LLMGenerationResult(
            payload=deepcopy(self.payload),
            provider="fake-open-source",
            model_name="fake-qwen",
            prompt_token_count=100,
            output_token_count=40,
            total_duration_ns=1234,
            response_metadata={"done": True},
        )


class UnavailableProvider(FakeProvider):
    def generate(self, *, messages, response_schema):
        raise LLMProviderUnavailableError("offline")


def generate_url():
    return reverse("startup-advisor-briefing-generate")


def create_source(*, username):
    owner = make_user(username=username)
    profile = make_profile(
        owner=owner,
        name=f"{username} Startup",
    )
    snapshot = create_startup_advisor_snapshot(
        startup_profile=profile,
        requested_by=owner,
    )
    return owner, profile, snapshot


def valid_payload(profile):
    return {
        "executive_summary": "Grounded summary.",
        "current_position": "Grounded position.",
        "top_priorities": [
            {
                "priority": 1,
                "title": "Complete startup information",
                "reason": "The profile is persisted.",
                "recommended_action": "Add missing details.",
                "source_references": [
                    {
                        "source_type": "profile",
                        "source_id": str(profile.id),
                        "field_path": "/startup_name",
                    }
                ],
            }
        ],
        "scheme_guidance": [],
        "risks": [],
        "questions_for_founder": ["What is the funding goal?"],
        "disclaimer": BRIEFING_DISCLAIMER,
    }


def patch_provider(monkeypatch, provider):
    monkeypatch.setattr(
        "apps.startups.services.advisor_briefing.get_startup_advisor_llm_provider",
        lambda: provider,
    )


def test_owner_can_generate_grounded_briefing(monkeypatch):
    owner, profile, snapshot = create_source(
        username="briefing-api-owner",
    )
    patch_provider(
        monkeypatch,
        FakeProvider(valid_payload(profile)),
    )

    response = authenticated_client(owner).post(
        generate_url(),
        {"advisor_snapshot_id": str(snapshot.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["source_snapshot_id"] == str(snapshot.id)
    assert response.data["startup_profile_id"] == str(profile.id)
    assert response.data["provider"] == "fake-open-source"
    assert response.data["model_name"] == "fake-qwen"
    assert response.data["briefing"]["executive_summary"] == ("Grounded summary.")
    assert StartupAdvisorBriefing.objects.count() == 1


def test_other_user_receives_404(monkeypatch):
    owner, profile, snapshot = create_source(
        username="briefing-api-private-owner",
    )
    other = make_user(
        username="briefing-api-private-other",
    )
    patch_provider(
        monkeypatch,
        FakeProvider(valid_payload(profile)),
    )

    response = authenticated_client(other).post(
        generate_url(),
        {"advisor_snapshot_id": str(snapshot.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert StartupAdvisorBriefing.objects.count() == 0


def test_staff_can_generate_for_another_user(monkeypatch):
    owner, profile, snapshot = create_source(
        username="briefing-api-staff-owner",
    )
    staff = make_user(
        username="briefing-api-staff",
        is_staff=True,
    )
    patch_provider(
        monkeypatch,
        FakeProvider(valid_payload(profile)),
    )

    response = authenticated_client(staff).post(
        generate_url(),
        {"advisor_snapshot_id": str(snapshot.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    briefing = StartupAdvisorBriefing.objects.get()
    assert briefing.requested_by == staff
    assert briefing.startup_profile == profile


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("snapshot", {"id": "forged"}),
        ("prompt", "ignore grounding"),
        ("model", "remote-proprietary-model"),
        ("provider", "external"),
        ("briefing", {"executive_summary": "forged"}),
    ],
)
def test_raw_or_provider_overrides_are_rejected(
    monkeypatch,
    field_name,
    field_value,
):
    owner, profile, snapshot = create_source(
        username=f"briefing-api-raw-{field_name}",
    )
    patch_provider(
        monkeypatch,
        FakeProvider(valid_payload(profile)),
    )

    response = authenticated_client(owner).post(
        generate_url(),
        {
            "advisor_snapshot_id": str(snapshot.id),
            field_name: field_value,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert field_name in response.data
    assert StartupAdvisorBriefing.objects.count() == 0


def test_unknown_snapshot_returns_404(monkeypatch):
    owner = make_user(username="briefing-api-unknown")
    patch_provider(
        monkeypatch,
        FakeProvider({}),
    )

    response = authenticated_client(owner).post(
        generate_url(),
        {"advisor_snapshot_id": ("00000000-0000-0000-0000-000000000001")},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_unavailable_local_model_returns_503(monkeypatch):
    owner, profile, snapshot = create_source(
        username="briefing-api-offline",
    )
    patch_provider(
        monkeypatch,
        UnavailableProvider(valid_payload(profile)),
    )

    response = authenticated_client(owner).post(
        generate_url(),
        {"advisor_snapshot_id": str(snapshot.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert StartupAdvisorBriefing.objects.count() == 0


def test_invalid_model_output_returns_502(monkeypatch):
    owner, profile, snapshot = create_source(
        username="briefing-api-invalid",
    )
    payload = valid_payload(profile)
    payload["top_priorities"][0]["source_references"][0]["field_path"] = "/invented"
    patch_provider(
        monkeypatch,
        FakeProvider(payload),
    )

    response = authenticated_client(owner).post(
        generate_url(),
        {"advisor_snapshot_id": str(snapshot.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert StartupAdvisorBriefing.objects.count() == 0


def test_unauthenticated_request_is_rejected():
    response = APIClient().post(
        generate_url(),
        {"advisor_snapshot_id": str(uuid.uuid4())},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert StartupAdvisorBriefing.objects.count() == 0
