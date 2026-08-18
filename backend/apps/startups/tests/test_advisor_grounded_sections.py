from types import SimpleNamespace

from apps.startups.services.advisor_briefing import (
    _enforce_grounded_advisor_sections,
)


def make_snapshot():
    return SimpleNamespace(
        readiness_snapshot={
            "status": "ready",
            "blocking_findings": [],
        },
        action_plan_snapshot={
            "id": "action-plan-1",
            "items": [],
            "has_actions": False,
        },
        recommendations_snapshot=[
            {
                "id": "rec-1",
                "scheme_name": "Scheme One",
                "assessment_result": (
                    "verification_required"
                ),
                "official_url": (
                    "https://official.example/scheme-one"
                ),
                "score_breakdown": {
                    "sector_match": True,
                    "stage_match": False,
                },
                "source_document": {
                    "title": "Official Authority",
                    "status": "verified",
                    "final_url": (
                        "https://official.example/scheme-one"
                    ),
                },
            },
            {
                "id": "rec-2",
                "scheme_name": "Scheme Two",
                "assessment_result": (
                    "verification_required"
                ),
                "official_url": (
                    "https://official.example/scheme-two"
                ),
                "score_breakdown": {
                    "sector_match": True,
                    "stage_match": False,
                },
                "source_document": {
                    "title": "Official Authority",
                    "status": "verified",
                    "final_url": (
                        "https://official.example/scheme-two"
                    ),
                },
            },
        ],
    )


def test_ready_startup_gets_no_fake_readiness_risk():
    payload = {
        "risks": [
            {
                "title": (
                    "No Current Readiness Gap Exists?"
                ),
                "reason": (
                    "0 critical and 0 recommended "
                    "findings remain."
                ),
                "mitigation": "No action.",
                "source_references": [
                    {
                        "source_type": "readiness",
                        "source_id": "ready-1",
                        "field_path": "/status",
                    }
                ],
            }
        ],
        "top_priorities": [],
        "scheme_guidance": [],
        "questions_for_founder": [],
    }

    result = _enforce_grounded_advisor_sections(
        payload,
        source_snapshot=make_snapshot(),
    )

    assert result["risks"] == []


def test_scheme_verification_becomes_priority():
    payload = {
        "risks": [],
        "top_priorities": [],
        "scheme_guidance": [],
        "questions_for_founder": [],
    }

    result = _enforce_grounded_advisor_sections(
        payload,
        source_snapshot=make_snapshot(),
    )

    assert len(result["top_priorities"]) == 2

    assert (
        result["top_priorities"][0]["priority"]
        == 1
    )

    assert (
        "Verify Scheme One eligibility"
        == result["top_priorities"][0]["title"]
    )


def test_scheme_guidance_uses_persisted_recommendations():
    result = _enforce_grounded_advisor_sections(
        {
            "risks": [],
            "top_priorities": [],
            "scheme_guidance": [],
            "questions_for_founder": [],
        },
        source_snapshot=make_snapshot(),
    )

    guidance = result["scheme_guidance"]

    assert len(guidance) == 2

    paths = {
        ref["field_path"]
        for ref
        in guidance[0]["source_references"]
    }

    assert "/official_url" in paths
    assert "/source_document/status" in paths


def test_existing_priority_is_preserved_without_deterministic_replacement():
    snapshot = SimpleNamespace(
        readiness_snapshot={
            "status": "ready",
            "blocking_findings": [],
        },
        action_plan_snapshot={
            "id": "action-plan-empty",
            "items": [],
            "has_actions": False,
        },
        recommendations_snapshot=[],
    )

    original_priority = {
        "priority": 1,
        "title": "Existing grounded priority",
        "reason": "The generated briefing supplied this priority.",
        "recommended_action": "Complete the existing action.",
        "source_references": [
            {
                "source_type": "profile",
                "source_id": "profile-1",
                "field_path": "/stage",
            }
        ],
    }

    result = _enforce_grounded_advisor_sections(
        {
            "risks": [],
            "top_priorities": [
                original_priority
            ],
            "scheme_guidance": [],
            "questions_for_founder": [],
        },
        source_snapshot=snapshot,
    )

    assert (
        result["top_priorities"]
        == [original_priority]
    )
