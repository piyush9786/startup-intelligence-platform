from copy import deepcopy

import pytest

from apps.startups.models import StartupAdvisorBriefing
from apps.startups.services import (
    BRIEFING_DISCLAIMER,
    generate_startup_advisor_briefing,
)
from apps.startups.tests.test_startup_advisor_briefing_service import (
    FakeProvider,
    create_source,
)

pytestmark = pytest.mark.django_db


def test_briefing_accepts_and_persists_retrieved_chunk_citation(settings):
    settings.STARTUP_ADVISOR_RAG_ENABLED = True
    owner, _profile, snapshot = create_source()
    chunk_id = "80c92c34-b78e-45b8-af0a-1052a9a81ed0"
    evidence = [
        {
            "id": chunk_id,
            "score": 0.91,
            "text": "Eligible startups must be DPIIT recognised.",
            "source_url": "https://example.gov.in/scheme.pdf",
            "title": "Example Scheme",
            "page_number": 1,
            "heading": "Eligibility",
            "extraction_id": "11111111-1111-1111-1111-111111111111",
            "document_id": "22222222-2222-2222-2222-222222222222",
        }
    ]
    payload = {
        "executive_summary": "Grounded summary.",
        "current_position": "Grounded current position.",
        "top_priorities": [
            {
                "priority": 1,
                "title": "Confirm DPIIT status",
                "reason": "The retrieved official evidence requires it.",
                "recommended_action": "Verify the current recognition status.",
                "source_references": [
                    {
                        "source_type": "evidence_chunk",
                        "source_id": chunk_id,
                        "field_path": "/text",
                    }
                ],
            }
        ],
        "scheme_guidance": [],
        "risks": [],
        "questions_for_founder": [],
        "disclaimer": BRIEFING_DISCLAIMER,
    }

    briefing = generate_startup_advisor_briefing(
        source_snapshot=snapshot,
        requested_by=owner,
        provider=FakeProvider(deepcopy(payload)),
        retriever=lambda _input: evidence,
    )

    assert StartupAdvisorBriefing.objects.count() == 1
    assert briefing.prompt_snapshot["retrieval"]["status"] == "succeeded"
    assert briefing.prompt_snapshot["retrieved_evidence"][0]["id"] == chunk_id
    reference = briefing.briefing["top_priorities"][0]["source_references"][0]
    assert reference["source_type"] == "evidence_chunk"
    assert reference["field_path"] == "/text"
    assert (
        briefing.prompt_snapshot["evidence_usage"]["status"]
        == "model_cited"
    )


def test_briefing_attaches_relevant_evidence_deterministically(
    settings,
):
    settings.STARTUP_ADVISOR_RAG_ENABLED = True
    owner, profile, snapshot = create_source()
    chunk_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    evidence = [
        {
            "id": chunk_id,
            "score": 0.88,
            "text": (
                "DPIIT recognition is required before an eligible "
                "startup applies for this benefit."
            ),
            "source_url": "https://example.gov.in/dpiit.pdf",
            "title": "DPIIT Recognition Guide",
            "page_number": 4,
            "heading": "Recognition",
            "extraction_id": (
                "11111111-1111-1111-1111-111111111111"
            ),
            "document_id": (
                "22222222-2222-2222-2222-222222222222"
            ),
        }
    ]
    payload = {
        "executive_summary": "Grounded summary.",
        "current_position": "Grounded current position.",
        "top_priorities": [
            {
                "priority": 1,
                "title": "Confirm DPIIT recognition",
                "reason": (
                    "The founder should confirm the DPIIT status."
                ),
                "recommended_action": (
                    "Verify recognition before applying."
                ),
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
        "questions_for_founder": [],
        "disclaimer": BRIEFING_DISCLAIMER,
    }

    briefing = generate_startup_advisor_briefing(
        source_snapshot=snapshot,
        requested_by=owner,
        provider=FakeProvider(payload),
        retriever=lambda _input: evidence,
    )

    references = briefing.briefing[
        "top_priorities"
    ][0]["source_references"]
    assert any(
        reference["source_type"] == "evidence_chunk"
        and reference["source_id"] == chunk_id
        for reference in references
    )
    usage = briefing.prompt_snapshot["evidence_usage"]
    assert usage["status"] == "deterministic_attachment"
    assert usage["section"] == "top_priorities"
    assert "dpiit" in usage["matched_terms"]


def test_briefing_records_when_retrieved_evidence_is_not_relevant(
    settings,
):
    settings.STARTUP_ADVISOR_RAG_ENABLED = True
    owner, profile, snapshot = create_source()
    evidence = [
        {
            "id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            "score": 0.81,
            "text": (
                "Export credit insurance protects overseas "
                "shipments from buyer default."
            ),
            "source_url": "https://example.gov.in/export.pdf",
            "title": "Export Credit Insurance",
            "page_number": 8,
            "heading": "Insurance",
            "extraction_id": (
                "33333333-3333-3333-3333-333333333333"
            ),
            "document_id": (
                "44444444-4444-4444-4444-444444444444"
            ),
        }
    ]
    payload = {
        "executive_summary": "Grounded summary.",
        "current_position": "Grounded current position.",
        "top_priorities": [
            {
                "priority": 1,
                "title": "Hire a finance leader",
                "reason": "The team needs stronger cash controls.",
                "recommended_action": (
                    "Define the role and interview candidates."
                ),
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
        "questions_for_founder": [],
        "disclaimer": BRIEFING_DISCLAIMER,
    }

    briefing = generate_startup_advisor_briefing(
        source_snapshot=snapshot,
        requested_by=owner,
        provider=FakeProvider(payload),
        retriever=lambda _input: evidence,
    )

    references = briefing.briefing[
        "top_priorities"
    ][0]["source_references"]
    assert not any(
        reference["source_type"] == "evidence_chunk"
        for reference in references
    )
    usage = briefing.prompt_snapshot["evidence_usage"]
    assert usage["status"] == "not_used"
    assert "sufficient item-level term overlap" in usage["reason"]


def test_briefing_fails_open_when_retrieval_is_unavailable(settings):
    settings.STARTUP_ADVISOR_RAG_ENABLED = True
    owner, profile, snapshot = create_source()
    reference = {
        "source_type": "profile",
        "source_id": str(profile.id),
        "field_path": "/startup_name",
    }
    payload = {
        "executive_summary": "Grounded summary.",
        "current_position": "Grounded current position.",
        "top_priorities": [
            {
                "priority": 1,
                "title": "Complete startup information",
                "reason": "The profile is the source.",
                "recommended_action": "Review the startup profile.",
                "source_references": [reference],
            }
        ],
        "scheme_guidance": [],
        "risks": [],
        "questions_for_founder": [],
        "disclaimer": BRIEFING_DISCLAIMER,
    }

    def unavailable(_input):
        raise RuntimeError("qdrant offline")

    briefing = generate_startup_advisor_briefing(
        source_snapshot=snapshot,
        requested_by=owner,
        provider=FakeProvider(payload),
        retriever=unavailable,
    )

    assert briefing.prompt_snapshot["retrieval"]["status"] == "unavailable"
    assert briefing.prompt_snapshot["retrieved_evidence"] == []
    assert (
        briefing.prompt_snapshot["evidence_usage"]["status"]
        == "not_available"
    )
