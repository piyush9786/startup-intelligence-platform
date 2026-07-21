from copy import deepcopy

import pytest

from apps.recommendations.models import (
    EligibilityAssessment,
    Recommendation,
    RecommendationGenerationRun,
)
from apps.recommendations.tests.test_recommendation_api import (
    make_profile,
    make_user,
)
from apps.startups.models import (
    StartupAdvisorBriefing,
    StartupAdvisorSnapshot,
    StartupReadinessActionPlan,
    StartupReadinessAssessment,
)
from apps.startups.services import (
    BRIEFING_DISCLAIMER,
    AdvisorSnapshotChangedError,
    BriefingOutputValidationError,
    LLMGenerationResult,
    LLMProviderUnavailableError,
    create_startup_advisor_snapshot,
    generate_startup_advisor_briefing,
)

pytestmark = pytest.mark.django_db


class FakeProvider:
    def __init__(self, payload, callback=None):
        self.payload = payload
        self.callback = callback

    @property
    def generation_parameters(self):
        return {
            "temperature": 0,
            "seed": 7,
            "think": False,
        }

    def generate(self, *, messages, response_schema):
        if self.callback:
            self.callback()
        return LLMGenerationResult(
            payload=deepcopy(self.payload),
            provider="fake-open-source",
            model_name="fake-qwen",
            prompt_token_count=100,
            output_token_count=40,
            total_duration_ns=1234,
            response_metadata={
                "done": True,
                "done_reason": "stop",
            },
        )


class UnavailableProvider(FakeProvider):
    def generate(self, *, messages, response_schema):
        raise LLMProviderUnavailableError("offline")


def create_source():
    owner = make_user(username="briefing-service-owner")
    profile = make_profile(
        owner=owner,
        name="Briefing Service Startup",
    )
    snapshot = create_startup_advisor_snapshot(
        startup_profile=profile,
        requested_by=owner,
    )
    return owner, profile, snapshot


def valid_payload(profile):
    reference = {
        "source_type": "profile",
        "source_id": str(profile.id),
        "field_path": "/startup_name",
    }
    return {
        "executive_summary": "Grounded summary.",
        "current_position": "Grounded current position.",
        "top_priorities": [
            {
                "priority": 1,
                "title": "Complete startup information",
                "reason": "The persisted profile is the source.",
                "recommended_action": "Add missing founder details.",
                "source_references": [reference],
            }
        ],
        "scheme_guidance": [],
        "risks": [],
        "questions_for_founder": ["What is the funding goal?"],
        "disclaimer": BRIEFING_DISCLAIMER,
    }


def test_service_persists_validated_briefing_and_metadata():
    owner, profile, snapshot = create_source()

    briefing = generate_startup_advisor_briefing(
        source_snapshot=snapshot,
        requested_by=owner,
        provider=FakeProvider(valid_payload(profile)),
    )

    assert briefing.source_snapshot == snapshot
    assert briefing.startup_profile == profile
    assert briefing.requested_by == owner
    assert briefing.provider == "fake-open-source"
    assert briefing.model_name == "fake-qwen"
    assert briefing.prompt_token_count == 100
    assert briefing.output_token_count == 40
    assert briefing.briefing["top_priorities"][0]["priority"] == 1
    assert briefing.prompt_snapshot["source_input"]["advisor_snapshot_id"] == str(snapshot.id)


def test_service_only_adds_briefing_record():
    owner, profile, snapshot = create_source()
    counts_before = {
        "snapshots": StartupAdvisorSnapshot.objects.count(),
        "readiness": StartupReadinessAssessment.objects.count(),
        "plans": StartupReadinessActionPlan.objects.count(),
        "runs": RecommendationGenerationRun.objects.count(),
        "eligibility": EligibilityAssessment.objects.count(),
        "recommendations": Recommendation.objects.count(),
    }

    generate_startup_advisor_briefing(
        source_snapshot=snapshot,
        requested_by=owner,
        provider=FakeProvider(valid_payload(profile)),
    )

    counts_after = {
        "snapshots": StartupAdvisorSnapshot.objects.count(),
        "readiness": StartupReadinessAssessment.objects.count(),
        "plans": StartupReadinessActionPlan.objects.count(),
        "runs": RecommendationGenerationRun.objects.count(),
        "eligibility": EligibilityAssessment.objects.count(),
        "recommendations": Recommendation.objects.count(),
    }
    assert counts_after == counts_before
    assert StartupAdvisorBriefing.objects.count() == 1


def test_invalid_output_is_not_persisted():
    owner, profile, snapshot = create_source()
    payload = valid_payload(profile)
    payload["top_priorities"][0]["source_references"][0]["field_path"] = "/invented"

    with pytest.raises(BriefingOutputValidationError):
        generate_startup_advisor_briefing(
            source_snapshot=snapshot,
            requested_by=owner,
            provider=FakeProvider(payload),
        )

    assert StartupAdvisorBriefing.objects.count() == 0


def test_provider_failure_is_not_persisted():
    owner, profile, snapshot = create_source()

    with pytest.raises(LLMProviderUnavailableError):
        generate_startup_advisor_briefing(
            source_snapshot=snapshot,
            requested_by=owner,
            provider=UnavailableProvider(valid_payload(profile)),
        )

    assert StartupAdvisorBriefing.objects.count() == 0


def test_source_mutation_during_generation_is_rejected():
    owner, profile, snapshot = create_source()

    def mutate_snapshot():
        snapshot.profile_snapshot = {
            **snapshot.profile_snapshot,
            "startup_name": "Mutated snapshot",
        }
        snapshot.save(
            update_fields=[
                "profile_snapshot",
                "updated_at",
            ]
        )

    with pytest.raises(
        AdvisorSnapshotChangedError,
        match="changed during LLM generation",
    ):
        generate_startup_advisor_briefing(
            source_snapshot=snapshot,
            requested_by=owner,
            provider=FakeProvider(
                valid_payload(profile),
                callback=mutate_snapshot,
            ),
        )

    assert StartupAdvisorBriefing.objects.count() == 0


def test_service_retains_historical_briefings():
    owner, profile, snapshot = create_source()
    provider = FakeProvider(valid_payload(profile))

    first = generate_startup_advisor_briefing(
        source_snapshot=snapshot,
        requested_by=owner,
        provider=provider,
    )
    second = generate_startup_advisor_briefing(
        source_snapshot=snapshot,
        requested_by=owner,
        provider=provider,
    )

    assert first.pk != second.pk
    assert StartupAdvisorBriefing.objects.count() == 2
