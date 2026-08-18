import json

import pytest

from apps.startups.services.slm_alias_contract import (
    SLMAliasContractError,
)
from apps.startups.services.slm_runtime_contract import (
    build_compact_advisor_request,
    build_compact_research_request,
    validate_compact_research_output,
)


def test_advisor_runtime_contract_builds_ref_map():
    result = build_compact_advisor_request(
        source_input={
            "profile": {
                "id": "profile-1",
                "startup_name": "Demo",
                "stage": "growth",
                "state": "Maharashtra",
                "sectors": ["DeepTech"],
            },
            "readiness": {
                "id": "readiness-1",
                "readiness_status": (
                    "needs_attention"
                ),
                "blocking_findings": [
                    {
                        "reason": (
                            "The incorporation date "
                            "is missing."
                        )
                    }
                ],
            },
            "action_plan": {},
            "recommendations": [],
        },
        retrieved_evidence=[],
    )

    payload = json.loads(
        result["messages"][1]["content"]
    )

    assert payload["task"] == (
        "FOUNDER_ADVISOR"
    )

    assert payload[
        "reference_facts"
    ][0]["id"] == "REF_001"

    assert (
        result["reference_map"]
        ["REF_001"]
        ["source_type"]
        == "readiness"
    )


def test_research_runtime_prioritizes_primary_without_excluding_secondary():
    result = (
        build_compact_research_request(
            question="What changed?",
            local_evidence=[],
            vector_evidence=[],
            live_evidence=[
                {
                    "title": "Secondary",
                    "url": (
                        "https://secondary.example"
                    ),
                    "content_excerpt": (
                        "Secondary evidence"
                    ),
                    "verification_status": (
                        "reputable_secondary"
                    ),
                    "confidence_score": 0.9,
                },
                {
                    "title": "Official",
                    "url": (
                        "https://official.example"
                    ),
                    "content_excerpt": (
                        "Official evidence"
                    ),
                    "verification_status": (
                        "official_live"
                    ),
                    "confidence_score": 0.8,
                },
            ],
        )
    )

    payload = result["payload"]

    # Primary evidence remains first, but reputable
    # secondary evidence is intentionally retained.
    assert len(
        payload["evidence"]
    ) == 2

    assert (
        payload["evidence"][0][
            "verification_status"
        ]
        == "official_live"
    )


def test_research_unknown_alias_rejected():
    result = (
        build_compact_research_request(
            question="What changed?",
            local_evidence=[
                {
                    "title": "Verified",
                    "url": (
                        "https://verified.example"
                    ),
                    "content_excerpt": (
                        "Verified fact"
                    ),
                    "confidence_score": 0.9,
                }
            ],
            vector_evidence=[],
            live_evidence=[],
        )
    )

    payload = {
        "executive_summary": "Summary",
        "findings": [
            {
                "title": "Finding",
                "finding": "Fact",
                "confidence": "high",
                "evidence_ids": [
                    "EVIDENCE_999"
                ],
            }
        ],
        "risks_or_unknowns": [],
        "source_quality_note": (
            "Verified evidence used."
        ),
    }

    with pytest.raises(
        SLMAliasContractError
    ):
        validate_compact_research_output(
            payload,
            evidence_map=result[
                "evidence_map"
            ],
        )


def test_advisor_missing_top_priorities_defaults_to_empty():
    from apps.startups.services.slm_runtime_contract import (
        validate_and_expand_compact_advisor_output,
    )

    payload = {
        "current_position": "validation",
        "executive_summary": "Ready for the next action.",
        "questions_for_founder": [],
        "risks": [],
        "scheme_guidance": [],
        # top_priorities deliberately omitted.
    }

    expanded = (
        validate_and_expand_compact_advisor_output(
            payload,
            reference_map={},
        )
    )

    assert expanded["top_priorities"] == []


def test_advisor_wrong_top_priorities_type_still_fails():
    from apps.startups.services.slm_runtime_contract import (
        validate_and_expand_compact_advisor_output,
    )

    payload = {
        "current_position": "validation",
        "executive_summary": "Summary",
        "questions_for_founder": [],
        "risks": [],
        "scheme_guidance": [],
        "top_priorities": "not-an-array",
    }

    with pytest.raises(
        SLMAliasContractError
    ):
        validate_and_expand_compact_advisor_output(
            payload,
            reference_map={},
        )


def test_advisor_scheme_guidance_drops_extra_fields():
    from apps.startups.services.slm_runtime_contract import (
        validate_and_expand_compact_advisor_output,
    )

    payload = {
        "current_position": "validation",
        "executive_summary": "Ready for next action.",
        "questions_for_founder": [],
        "risks": [],
        "scheme_guidance": [
            {
                "citations": ["REF_001"],
                "guidance": (
                    "Review requirements before applying."
                ),
                "scheme_name": "Example Scheme",

                # Model drift: unsupported presentation fields.
                "reason": "Extra explanation",
                "title": "Proceed?",
            }
        ],
        "top_priorities": [],
    }

    expanded = (
        validate_and_expand_compact_advisor_output(
            payload,
            reference_map={
                "REF_001": {
                    "source_type": "recommendation",
                    "source_id": "scheme-1",
                    "field_path": "/scheme_name",
                }
            },
        )
    )

    item = expanded["scheme_guidance"][0]

    assert "reason" not in item
    assert "title" not in item

    assert (
        item["scheme_name"]
        == "Example Scheme"
    )

    assert item["source_references"] == [
        {
            "source_type": "recommendation",
            "source_id": "scheme-1",
            "field_path": "/scheme_name",
        }
    ]


def test_advisor_scheme_guidance_missing_required_field_still_fails():
    from apps.startups.services.slm_runtime_contract import (
        validate_and_expand_compact_advisor_output,
    )

    payload = {
        "current_position": "validation",
        "executive_summary": "Summary",
        "questions_for_founder": [],
        "risks": [],
        "scheme_guidance": [
            {
                "citations": ["REF_001"],
                # required guidance/scheme fields
                # are deliberately not manufactured.
                "title": "Extra field only",
            }
        ],
        "top_priorities": [],
    }

    with pytest.raises(
        SLMAliasContractError
    ):
        validate_and_expand_compact_advisor_output(
            payload,
            reference_map={
                "REF_001": {
                    "source_type": "recommendation",
                    "source_id": "scheme-1",
                    "field_path": "/scheme_name",
                }
            },
        )


def test_research_request_balances_evidence_trust_tiers():
    local_evidence = [
        {
            "title": f"Official evidence {index}",
            "url": f"https://example.gov.in/item-{index}",
            "content_excerpt": f"Verified fact {index}",
            "verification_status": "verified_internal",
            "confidence_score": 0.95 - (index * 0.01),
            "source_type": "official_portal",
        }
        for index in range(6)
    ]

    live_evidence = [
        {
            "title": "Reputable market source 1",
            "url": "https://inc42.com/example-1",
            "content_excerpt": "Competitor market evidence one.",
            "verification_status": "reputable_secondary",
            "confidence_score": 0.80,
            "source_type": "news",
        },
        {
            "title": "Reputable market source 2",
            "url": "https://inc42.com/example-2",
            "content_excerpt": "Competitor market evidence two.",
            "verification_status": "reputable_secondary",
            "confidence_score": 0.78,
            "source_type": "news",
        },
        {
            "title": "Startup directory 1",
            "url": "https://f6s.com/example-1",
            "content_excerpt": "Possible competitor discovery evidence.",
            "verification_status": "unverified_live",
            "confidence_score": 0.60,
            "source_type": "startup_directory",
        },
        {
            "title": "Startup directory 2",
            "url": "https://tracxn.com/example-2",
            "content_excerpt": "Possible competitor discovery evidence.",
            "verification_status": "unverified_live",
            "confidence_score": 0.58,
            "source_type": "startup_directory",
        },
        {
            "title": "Rejected random source",
            "url": "https://random.invalid/example",
            "content_excerpt": "This must never reach the model.",
            "verification_status": "rejected",
            "confidence_score": 0.99,
            "source_type": "web_source",
        },
    ]

    result = build_compact_research_request(
        question="Who are the current competitors?",
        live_evidence=live_evidence,
        vector_evidence=[],
        local_evidence=local_evidence,
    )

    evidence = result["payload"]["evidence"]

    assert len(evidence) == 4

    statuses = [
        item["verification_status"]
        for item in evidence
    ]

    assert statuses.count(
        "verified_internal"
    ) == 3

    assert statuses.count(
        "reputable_secondary"
    ) == 1

    assert statuses.count(
        "unverified_live"
    ) == 0

    assert "rejected" not in statuses

    titles = {
        item["title"]
        for item in evidence
    }

    assert (
        "Rejected random source"
        not in titles
    )


def test_research_request_fills_unused_balanced_slots():
    local_evidence = [
        {
            "title": f"Verified item {index}",
            "url": f"https://example.gov.in/{index}",
            "content_excerpt": f"Verified evidence {index}",
            "verification_status": "verified_internal",
            "confidence_score": 0.90,
            "source_type": "official_portal",
        }
        for index in range(8)
    ]

    result = build_compact_research_request(
        question="Create a founder research report.",
        live_evidence=[],
        vector_evidence=[],
        local_evidence=local_evidence,
    )

    evidence = result["payload"]["evidence"]

    assert len(evidence) == 4

    assert all(
        item["verification_status"]
        == "verified_internal"
        for item in evidence
    )


def test_research_runtime_normalizes_legacy_slm_shape():
    from apps.startups.services.slm_runtime_contract import (
        normalize_compact_research_output,
        validate_compact_research_output,
    )

    evidence_map = {
        "EVIDENCE_001": {
            "verification_status": "official_live",
            "confidence_score": 0.95,
        },
        "EVIDENCE_002": {
            "verification_status": "reputable_secondary",
            "confidence_score": 0.80,
        },
    }

    legacy_payload = {
        "executive_summary": (
            "Grounded research summary."
        ),
        "findings": [
            {
                "title": "Official support",
                "finding": (
                    "An official startup support "
                    "source was retrieved."
                ),
                "confidence": "high",
                "evidence_ids": [
                    "EVIDENCE_001",
                ],
            }
        ],
        "risks": [
            {
                "title": "Evidence gap",
                "reason": (
                    "The available source does "
                    "not establish every detail."
                ),
                "confidence": "medium",
                "evidence": [
                    "EVIDENCE_002",
                ],
            }
        ],
        "recommended_actions": [
            {
                "title": "Legacy action",
                "action": (
                    "Verify the application status."
                ),
                "confidence": "high",
            }
        ],
        "questions_for_guidance": [
            {
                "title": "Legacy question",
                "guidance": (
                    "Confirm the application status."
                ),
                "confidence": "medium",
            }
        ],
    }

    normalized = (
        normalize_compact_research_output(
            legacy_payload,
            evidence_map=evidence_map,
        )
    )

    assert "risks" not in normalized
    assert (
        "recommended_actions"
        not in normalized
    )
    assert (
        "questions_for_guidance"
        not in normalized
    )

    assert normalized[
        "risks_or_unknowns"
    ] == [
        (
            "Evidence gap: The available source "
            "does not establish every detail."
        )
    ]

    assert (
        normalized["source_quality_note"]
        == (
            "Evidence supplied by Django: "
            "1 verified/official, "
            "1 reputable secondary, "
            "0 unverified."
        )
    )

    used_aliases = (
        validate_compact_research_output(
            normalized,
            evidence_map=evidence_map,
        )
    )

    assert used_aliases == [
        "EVIDENCE_001",
    ]


def test_research_legacy_risk_unknown_alias_rejected():
    import pytest

    from apps.startups.services.slm_alias_contract import (
        SLMAliasContractError,
    )
    from apps.startups.services.slm_runtime_contract import (
        normalize_compact_research_output,
    )

    with pytest.raises(
        SLMAliasContractError
    ):
        normalize_compact_research_output(
            {
                "executive_summary": "Summary",
                "findings": [],
                "risks": [
                    {
                        "title": "Risk",
                        "reason": "Risk reason.",
                        "evidence": [
                            "EVIDENCE_999",
                        ],
                    }
                ],
            },
            evidence_map={},
        )


def test_research_system_requires_strict_json_syntax():
    from apps.startups.services.slm_runtime_contract import (
        RESEARCH_SYSTEM,
    )

    assert (
        "first character of the response MUST be {"
        in RESEARCH_SYSTEM
    )
    assert (
        "final character MUST be }"
        in RESEARCH_SYSTEM
    )
    assert (
        "Do not output YAML"
        in RESEARCH_SYSTEM
    )
    assert (
        '"executive_summary"'
        in RESEARCH_SYSTEM
    )
    assert (
        '"evidence_ids"'
        in RESEARCH_SYSTEM
    )
