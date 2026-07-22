from types import SimpleNamespace

from apps.recommendations.services.explanation import (
    EXPLANATION_VERSION,
    build_eligibility_explanation,
)


def test_ineligible_age_rule_is_explained_in_plain_language():
    assessment = SimpleNamespace(
        result="ineligible",
        matched_rules=[
            {
                "field_path": "dpiit_recognized",
                "operator": "equals",
                "expected_value": True,
                "actual_value": True,
                "mandatory": True,
            }
        ],
        failed_rules=[
            {
                "field_path": "startup_age_months",
                "operator": "less_or_equal",
                "expected_value": 120,
                "actual_value": 132,
                "mandatory": True,
            }
        ],
        unknown_rules=[],
    )

    explanation = build_eligibility_explanation(assessment)

    assert explanation["version"] == EXPLANATION_VERSION
    assert explanation["summary"] == (
        "You are not currently eligible because 1 mandatory requirement was not met."
    )
    assert explanation["passed_checks"] == [
        "Your startup has the DPIIT recognition status required by this scheme."
    ]
    assert explanation["unmet_requirements"] == [
        "Your startup is 11 years old, but this scheme accepts startups up to 10 years old."
    ]
    assert explanation["next_steps"] == [
        "Consider schemes with a higher startup-age limit."
    ]


def test_missing_information_returns_a_specific_profile_action():
    assessment = SimpleNamespace(
        result="insufficient_information",
        matched_rules=[],
        failed_rules=[],
        unknown_rules=[
            {
                "field_path": "regulatory_registration",
                "operator": "contains_any",
                "expected_value": ["sebi_aif"],
                "actual_value": None,
                "mandatory": True,
                "reason": "Regulatory registrations have not been provided.",
            }
        ],
    )

    explanation = build_eligibility_explanation(assessment)

    assert explanation["summary"] == (
        "Eligibility cannot be confirmed because 1 required profile detail is missing."
    )
    assert explanation["missing_information"] == [
        "Add your regulatory registrations so this requirement can be checked."
    ]
    assert explanation["next_steps"] == explanation["missing_information"]


def test_closed_application_adds_a_window_check_next_step():
    assessment = SimpleNamespace(
        result="application_closed",
        matched_rules=[],
        failed_rules=[],
        unknown_rules=[],
    )

    explanation = build_eligibility_explanation(assessment)

    assert explanation["summary"] == (
        "Your profile was evaluated, but applications for this scheme are currently closed."
    )
    assert explanation["next_steps"] == [
        "Check the official scheme page for the next application window."
    ]
