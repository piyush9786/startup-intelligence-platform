import json
from copy import deepcopy

import pytest

from apps.recommendations.tests.test_recommendation_api import (
    make_profile,
    make_user,
)
from apps.startups.services import (
    BRIEFING_DISCLAIMER,
    BriefingOutputValidationError,
    build_startup_advisor_briefing_prompt,
    create_startup_advisor_snapshot,
    validate_startup_advisor_briefing,
)
from apps.startups.services.briefing_schema import _canonicalize_model_field_path

pytestmark = pytest.mark.django_db


def make_snapshot():
    owner = make_user(username="briefing-schema-owner")
    profile = make_profile(
        owner=owner,
        name="Briefing Schema Startup",
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
        "executive_summary": "The startup profile is available.",
        "current_position": "The persisted profile names the startup.",
        "top_priorities": [
            {
                "priority": 1,
                "title": "Complete the advisor inputs",
                "reason": "Only persisted profile facts are available.",
                "recommended_action": ("Provide missing readiness and funding details."),
                "source_references": [reference],
            }
        ],
        "scheme_guidance": [],
        "risks": [
            {
                "title": "Limited persisted evidence",
                "reason": "No readiness or recommendation data exists.",
                "mitigation": "Generate deterministic guidance first.",
                "source_references": [reference],
            }
        ],
        "questions_for_founder": ["What is the immediate funding objective?"],
        "disclaimer": BRIEFING_DISCLAIMER,
    }


def test_valid_grounded_payload_is_accepted():
    _owner, profile, snapshot = make_snapshot()
    payload = valid_payload(profile)

    result = validate_startup_advisor_briefing(
        payload=payload,
        source_snapshot=snapshot,
    )

    assert result == payload


def test_schema_violation_is_rejected():
    _owner, profile, snapshot = make_snapshot()
    payload = valid_payload(profile)
    payload["unexpected"] = True

    with pytest.raises(
        BriefingOutputValidationError,
        match="schema validation",
    ):
        validate_startup_advisor_briefing(
            payload=payload,
            source_snapshot=snapshot,
        )


def test_unknown_source_identifier_is_rejected():
    _owner, profile, snapshot = make_snapshot()
    payload = valid_payload(profile)
    payload["top_priorities"][0]["source_references"][0]["source_id"] = (
        "00000000-0000-0000-0000-000000000001"
    )

    with pytest.raises(
        BriefingOutputValidationError,
        match="unavailable source",
    ):
        validate_startup_advisor_briefing(
            payload=payload,
            source_snapshot=snapshot,
        )


def test_model_field_path_is_canonicalized_to_json_pointer():
    assert (
        _canonicalize_model_field_path(
            "/readiness/blocking_findings[0].reason",
            source_type="readiness",
        )
        == "/blocking_findings/0/reason"
    )


def test_redundant_source_prefix_is_canonicalized():
    _owner, profile, snapshot = make_snapshot()
    payload = valid_payload(profile)

    reference = payload["top_priorities"][0]["source_references"][0]
    reference["field_path"] = "/profile/startup_name"

    result = validate_startup_advisor_briefing(
        payload=payload,
        source_snapshot=snapshot,
    )

    assert result["top_priorities"][0]["source_references"][0]["field_path"] == "/startup_name"


def test_missing_source_field_path_is_rejected():
    _owner, profile, snapshot = make_snapshot()
    payload = valid_payload(profile)
    payload["top_priorities"][0]["source_references"][0]["field_path"] = "/does_not_exist"

    with pytest.raises(
        BriefingOutputValidationError,
        match="missing field path",
    ):
        validate_startup_advisor_briefing(
            payload=payload,
            source_snapshot=snapshot,
        )


def test_priorities_must_be_contiguous():
    _owner, profile, snapshot = make_snapshot()
    payload = valid_payload(profile)
    second = deepcopy(payload["top_priorities"][0])
    second["priority"] = 3
    payload["top_priorities"].append(second)

    with pytest.raises(
        BriefingOutputValidationError,
        match="ordered and contiguous",
    ):
        validate_startup_advisor_briefing(
            payload=payload,
            source_snapshot=snapshot,
        )


def test_scheme_guidance_must_cite_recommendation():
    _owner, profile, snapshot = make_snapshot()
    payload = valid_payload(profile)
    payload["scheme_guidance"] = [
        {
            "scheme_name": "Unverified scheme",
            "guidance": "Do not invent scheme advice.",
            "source_references": [
                {
                    "source_type": "profile",
                    "source_id": str(profile.id),
                    "field_path": "/startup_name",
                }
            ],
        }
    ]

    with pytest.raises(
        BriefingOutputValidationError,
        match="must be empty when the advisor snapshot contains no persisted recommendations",
    ):
        validate_startup_advisor_briefing(
            payload=payload,
            source_snapshot=snapshot,
        )


def test_prompt_contains_schema_and_immutable_snapshot():
    _owner, profile, snapshot = make_snapshot()

    prompt = build_startup_advisor_briefing_prompt(
        source_snapshot=snapshot,
    )

    assert prompt["source_input"]["advisor_snapshot_id"] == str(snapshot.id)
    assert prompt["source_input"]["profile"]["id"] == str(profile.id)
    assert prompt["response_schema"]["type"] == "object"
    assert prompt["messages"][0]["role"] == "system"
    assert "Keep the briefing concise:" in prompt["messages"][0]["content"]

    user_payload = json.loads(prompt["messages"][1]["content"])

    assert "response_schema" not in user_payload
    assert user_payload["startup_advisor_snapshot"]["advisor_snapshot_id"] == str(snapshot.id)
    assert str(snapshot.id) in prompt["messages"][1]["content"]
