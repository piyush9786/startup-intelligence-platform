import json
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
    LLMProviderResponseError,
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


class RetryableResponseProvider(FakeProvider):
    def __init__(self, payload):
        super().__init__(payload)
        self.messages = []

    def generate(self, *, messages, response_schema):
        self.messages.append(messages)
        if len(self.messages) == 1:
            raise LLMProviderResponseError("truncated")
        return super().generate(
            messages=messages,
            response_schema=response_schema,
        )


class NonRetryableResponseProvider(FakeProvider):
    def __init__(self, payload):
        super().__init__(payload)
        self.calls = 0

    def generate(self, *, messages, response_schema):
        self.calls += 1
        raise LLMProviderResponseError(
            "schema rejected",
            retryable=False,
        )


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
    # Give an invalid source ID to trigger validation failure
    ref = payload["top_priorities"][0]["source_references"][0]
    ref["source_id"] = "00000000-0000-0000-0000-000000000001"

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


def test_service_retries_retryable_response_without_retrieved_evidence(
    settings,
):
    settings.STARTUP_ADVISOR_RAG_ENABLED = True
    owner, profile, snapshot = create_source()
    provider = RetryableResponseProvider(valid_payload(profile))
    evidence = [
        {
            "id": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
            "score": 0.9,
            "text": "DPIIT recognition is required for this scheme.",
            "source_url": "https://example.gov.in/dpiit.pdf",
            "title": "DPIIT Guide",
            "page_number": 1,
            "heading": "Eligibility",
            "extraction_id": "11111111-1111-1111-1111-111111111111",
            "document_id": "22222222-2222-2222-2222-222222222222",
        }
    ]

    briefing = generate_startup_advisor_briefing(
        source_snapshot=snapshot,
        requested_by=owner,
        provider=provider,
        retriever=lambda _input: evidence,
    )

    assert len(provider.messages) == 2
    retry_payload = json.loads(provider.messages[1][1]["content"])
    assert retry_payload["retrieved_evidence"] == []
    assert "smallest complete valid briefing" in provider.messages[1][0]["content"]
    assert briefing.prompt_snapshot["generation_attempts"] == [
        {
            "attempt": 1,
            "retrieved_evidence_count": 1,
            "status": "response_error",
        },
        {
            "attempt": 2,
            "retrieved_evidence_count": 0,
            "status": "succeeded",
        },
    ]
    assert briefing.prompt_snapshot["retrieval"]["status"] == "omitted_for_retry"


def test_service_does_not_retry_non_retryable_response_error():
    owner, profile, snapshot = create_source()
    provider = NonRetryableResponseProvider(valid_payload(profile))

    with pytest.raises(LLMProviderResponseError, match="schema rejected"):
        generate_startup_advisor_briefing(
            source_snapshot=snapshot,
            requested_by=owner,
            provider=provider,
        )

    assert provider.calls == 1
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
