import pytest

from apps.startups.services.llm_provider import (
    LLMResponseFormatError,
    _clean_and_parse_json_payload,
)


def test_repairs_missing_comma_between_object_fields():
    malformed = (
        '{"current_position":"growth startup" '
        '"executive_summary":"Ready with one gap",'
        '"risks":[]}'
    )

    parsed = _clean_and_parse_json_payload(
        malformed
    )

    assert (
        parsed["current_position"]
        == "growth startup"
    )

    assert (
        parsed["executive_summary"]
        == "Ready with one gap"
    )


def test_repairs_multiple_missing_object_commas():
    malformed = (
        '{"a":"one" '
        '"b":"two" '
        '"c":[]}'
    )

    parsed = _clean_and_parse_json_payload(
        malformed
    )

    assert parsed == {
        "a": "one",
        "b": "two",
        "c": [],
    }


def test_still_repairs_trailing_comma():
    parsed = _clean_and_parse_json_payload(
        '{"a":"one","items":[1,2,],}'
    )

    assert parsed == {
        "a": "one",
        "items": [1, 2],
    }


def test_does_not_semantically_repair_broken_json():
    malformed = (
        '{"reason":"This has an '
        '"unescaped quote inside"}'
    )

    with pytest.raises(
        LLMResponseFormatError
    ):
        _clean_and_parse_json_payload(
            malformed
        )


def test_repairs_missing_object_close_before_array_close():
    malformed = (
        '{"risks":['
        '{"citations":["REF_004"],'
        '"title":"No Current Readiness Gap Exists?"],'
        '"scheme_guidance":[]}'
    )

    parsed = _clean_and_parse_json_payload(
        malformed
    )

    assert parsed == {
        "risks": [
            {
                "citations": ["REF_004"],
                "title": (
                    "No Current Readiness Gap Exists?"
                ),
            }
        ],
        "scheme_guidance": [],
    }


def test_repairs_missing_array_close_before_object_close():
    malformed = (
        '{"items":[{"name":"one"}'
        '}'
    )

    parsed = _clean_and_parse_json_payload(
        malformed
    )

    assert parsed == {
        "items": [
            {
                "name": "one",
            }
        ]
    }
