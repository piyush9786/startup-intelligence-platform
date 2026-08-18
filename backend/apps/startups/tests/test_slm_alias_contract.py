from apps.startups.services.slm_alias_contract import (
    SLMAliasContractError,
    expand_compact_advisor_output,
)


def _payload():
    return {
        "executive_summary": "Ready to proceed.",
        "current_position": "Profile is complete.",
        "top_priorities": [
            {
                "priority": 1,
                "title": "Validate scheme fit",
                "reason": "A persisted recommendation exists.",
                "recommended_action": "Review the official requirements.",
                "citations": ["REF_001"],
            }
        ],
        "scheme_guidance": [],
        "risks": [],
        "questions_for_founder": [],
    }


def test_compact_alias_expands_to_legacy_reference():
    result = expand_compact_advisor_output(
        _payload(),
        reference_map={
            "REF_001": {
                "source_type": "profile",
                "source_id": (
                    "11111111-1111-1111-1111-111111111111"
                ),
                "field_path": "/stage",
            }
        },
    )

    refs = result["top_priorities"][0]["source_references"]
    assert refs == [
        {
            "source_type": "profile",
            "source_id": (
                "11111111-1111-1111-1111-111111111111"
            ),
            "field_path": "/stage",
        }
    ]
    assert "citations" not in result["top_priorities"][0]
    assert result["disclaimer"]


def test_unknown_alias_is_rejected():
    payload = _payload()
    payload["top_priorities"][0]["citations"] = ["REF_999"]

    try:
        expand_compact_advisor_output(
            payload,
            reference_map={},
        )
    except SLMAliasContractError as exc:
        assert "REF_999" in str(exc)
    else:
        raise AssertionError("Expected alias validation failure")
