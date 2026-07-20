from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from apps.startups.models import StartupProfile
from apps.startups.services import (
    ENGINE_VERSION,
    ReadinessOutcome,
    ReadinessStatus,
    evaluate_startup_readiness,
)


def profile(**overrides):
    values = {
        "startup_name": "Readiness Labs",
        "legal_name": "Readiness Labs Private Limited",
        "description": (
            "A technology startup solving a clearly defined "
            "customer problem with a scalable digital product."
        ),
        "incorporation_type": "private_limited",
        "incorporation_date": date(2025, 1, 15),
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "stage": StartupProfile.Stage.MVP,
        "sectors": ["software"],
        "technologies": ["artificial intelligence"],
        "founder_categories": [],
        "founder_gender": "",
        "dpiit_recognized": True,
        "udyam_registered": False,
        "annual_turnover": Decimal("1000000.00"),
        "revenue_stage": "early_revenue",
        "funding_required": Decimal("5000000.00"),
        "funding_purpose": ("Product development and market expansion."),
        "team_size": 8,
        "profile_data": {},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def finding(evaluation, code):
    return next(item for item in evaluation.findings if item.code == code)


def test_complete_startup_profile_is_ready():
    evaluation = evaluate_startup_readiness(
        startup_profile=profile(),
        as_of_date=date(2026, 7, 20),
    )

    assert evaluation.status == ReadinessStatus.READY
    assert evaluation.score == 100
    assert evaluation.critical_score == 100
    assert evaluation.recommended_score == 100
    assert evaluation.blocking_findings == ()
    assert evaluation.engine_version == ENGINE_VERSION
    assert all(item.outcome == ReadinessOutcome.PRESENT for item in evaluation.findings)


def test_missing_critical_fields_blocks_readiness():
    evaluation = evaluate_startup_readiness(
        startup_profile=profile(
            startup_name="",
            incorporation_date=None,
            dpiit_recognized=None,
        ),
        as_of_date=date(2026, 7, 20),
    )

    assert evaluation.status == ReadinessStatus.BLOCKED
    assert {item.code for item in evaluation.blocking_findings} == {
        "startup_name",
        "incorporation_date",
        "dpiit_recognized",
    }
    assert (
        finding(
            evaluation,
            "startup_name",
        ).outcome
        == ReadinessOutcome.MISSING
    )
    assert evaluation.score < 100


def test_future_incorporation_date_is_invalid():
    evaluation = evaluate_startup_readiness(
        startup_profile=profile(
            incorporation_date=date(2026, 7, 21),
        ),
        as_of_date=date(2026, 7, 20),
    )

    result = finding(
        evaluation,
        "incorporation_date",
    )
    assert evaluation.status == ReadinessStatus.BLOCKED
    assert result.outcome == ReadinessOutcome.INVALID
    assert result.actual_value == date(2026, 7, 21)


@pytest.mark.parametrize(
    ("profile_data", "expected_outcome"),
    [
        (
            {
                "entity_types": ["alternative_investment_fund"],
            },
            ReadinessOutcome.MISSING,
        ),
        (
            {
                "entity_types": ["alternative_investment_fund"],
                "regulatory_registrations": ["RBI"],
            },
            ReadinessOutcome.INCOMPLETE,
        ),
        (
            {
                "entity_types": ["alternative_investment_fund"],
                "regulatory_registrations": ["SEBI"],
            },
            ReadinessOutcome.PRESENT,
        ),
    ],
)
def test_aif_regulatory_context(
    profile_data,
    expected_outcome,
):
    evaluation = evaluate_startup_readiness(
        startup_profile=profile(
            profile_data=profile_data,
        ),
        as_of_date=date(2026, 7, 20),
    )

    result = finding(
        evaluation,
        "eligibility_context",
    )
    assert result.outcome == expected_outcome


def test_incomplete_recommended_fields_keep_profile_usable():
    evaluation = evaluate_startup_readiness(
        startup_profile=profile(
            description="Too short",
            district="",
            annual_turnover=None,
            funding_purpose="",
        ),
        as_of_date=date(2026, 7, 20),
    )

    assert evaluation.status == (ReadinessStatus.READY_WITH_RECOMMENDATIONS)
    assert evaluation.critical_score == 100
    assert (
        finding(
            evaluation,
            "description",
        ).outcome
        == ReadinessOutcome.INCOMPLETE
    )
    assert (
        finding(
            evaluation,
            "location",
        ).outcome
        == ReadinessOutcome.INCOMPLETE
    )
    assert (
        finding(
            evaluation,
            "business_metrics",
        ).outcome
        == ReadinessOutcome.INCOMPLETE
    )
    assert (
        finding(
            evaluation,
            "funding_plan",
        ).outcome
        == ReadinessOutcome.INCOMPLETE
    )


def test_invalid_recommended_values_are_explicit():
    evaluation = evaluate_startup_readiness(
        startup_profile=profile(
            sectors="software",
            annual_turnover=Decimal("-1"),
            funding_required=Decimal("-1"),
        ),
        as_of_date=date(2026, 7, 20),
    )

    assert evaluation.status == (ReadinessStatus.READY_WITH_RECOMMENDATIONS)
    assert (
        finding(
            evaluation,
            "sectors",
        ).outcome
        == ReadinessOutcome.INVALID
    )
    assert (
        finding(
            evaluation,
            "business_metrics",
        ).outcome
        == ReadinessOutcome.INVALID
    )
    assert (
        finding(
            evaluation,
            "funding_plan",
        ).outcome
        == ReadinessOutcome.INVALID
    )


def test_evaluation_is_deterministic_and_json_ready():
    first = evaluate_startup_readiness(
        startup_profile=profile(),
        as_of_date=date(2026, 7, 20),
    )
    second = evaluate_startup_readiness(
        startup_profile=profile(),
        as_of_date=date(2026, 7, 20),
    )

    assert first == second
    payload = first.to_dict()
    incorporation = next(
        item for item in payload["findings"] if item["code"] == "incorporation_date"
    )
    funding = next(item for item in payload["findings"] if item["code"] == "funding_plan")
    assert incorporation["actual_value"] == "2025-01-15"
    assert funding["actual_value"]["funding_required"] == ("5000000.00")
    assert payload["engine_version"] == ("startup-readiness-v1")
