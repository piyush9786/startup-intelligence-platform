from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from apps.recommendations.services.eligibility import evaluate_rules


def profile(
    *,
    incorporation_date=None,
    dpiit_recognized=None,
    profile_data=None,
):
    return SimpleNamespace(
        incorporation_date=incorporation_date,
        dpiit_recognized=dpiit_recognized,
        profile_data=profile_data or {},
    )


def rule(
    field_path,
    operator,
    expected_value,
    *,
    mandatory=True,
    rule_group="all",
    manually_verified=True,
):
    return SimpleNamespace(
        id=uuid4(),
        field_path=field_path,
        operator=operator,
        expected_value=expected_value,
        mandatory=mandatory,
        rule_group=rule_group,
        manually_verified=manually_verified,
        evidence_text=f"Evidence for {field_path}",
        evidence_page=1,
    )


SISFS_RULES = [
    rule("dpiit_recognized", "equals", True),
    rule("eligible_entity_type", "contains_any", "startup"),
    rule("startup_age_months", "less_or_equal", 24),
]

FFS_RULES = [
    rule(
        "eligible_entity_type",
        "contains_any",
        "alternative_investment_fund",
    ),
    rule(
        "regulatory_registration",
        "contains_any",
        "SEBI",
    ),
]


def test_sisfs_exact_24_month_boundary_is_eligible():
    result = evaluate_rules(
        startup_profile=profile(
            incorporation_date=date(2024, 1, 15),
            dpiit_recognized=True,
        ),
        rules=SISFS_RULES,
        application_status="unknown",
        as_of_date=date(2026, 1, 15),
    )

    assert result.result == "eligible"
    assert len(result.matched_rules) == 3
    assert not result.failed_rules
    assert not result.unknown_rules


def test_sisfs_one_day_past_24_month_anniversary_is_ineligible():
    result = evaluate_rules(
        startup_profile=profile(
            incorporation_date=date(2024, 1, 14),
            dpiit_recognized=True,
        ),
        rules=SISFS_RULES,
        application_status="unknown",
        as_of_date=date(2026, 1, 15),
    )

    assert result.result == "ineligible"
    assert [item.field_path for item in result.failed_rules] == ["startup_age_months"]
    assert result.failed_rules[0].actual_value == 25


def test_missing_incorporation_date_is_insufficient_information():
    result = evaluate_rules(
        startup_profile=profile(
            dpiit_recognized=True,
        ),
        rules=SISFS_RULES,
        application_status="unknown",
        as_of_date=date(2026, 1, 15),
    )

    assert result.result == "insufficient_information"
    assert [item.field_path for item in result.unknown_rules] == ["startup_age_months"]


def test_ffs_startup_profile_is_ineligible_even_with_missing_registration():
    result = evaluate_rules(
        startup_profile=profile(),
        rules=FFS_RULES,
        application_status="unknown",
        as_of_date=date(2026, 1, 15),
    )

    assert result.result == "ineligible"
    assert [item.field_path for item in result.failed_rules] == ["eligible_entity_type"]
    assert [item.field_path for item in result.unknown_rules] == ["regulatory_registration"]


def test_ffs_aif_profile_with_sebi_registration_is_eligible():
    result = evaluate_rules(
        startup_profile=profile(
            profile_data={
                "entity_types": ["alternative_investment_fund"],
                "regulatory_registrations": ["SEBI"],
            }
        ),
        rules=FFS_RULES,
        application_status="unknown",
        as_of_date=date(2026, 1, 15),
    )

    assert result.result == "eligible"
    assert len(result.matched_rules) == 2


def test_contains_any_accepts_scalar_expected_value_case_insensitively():
    result = evaluate_rules(
        startup_profile=profile(
            profile_data={
                "regulatory_registrations": ["sebi"],
            }
        ),
        rules=[
            rule(
                "regulatory_registration",
                "contains_any",
                "SEBI",
            )
        ],
        application_status="unknown",
        as_of_date=date(2026, 1, 15),
    )

    assert result.result == "eligible"


def test_unverified_rule_requires_manual_verification():
    result = evaluate_rules(
        startup_profile=profile(dpiit_recognized=True),
        rules=[
            rule(
                "dpiit_recognized",
                "equals",
                True,
                manually_verified=False,
            )
        ],
        application_status="unknown",
        as_of_date=date(2026, 1, 15),
    )

    assert result.result == "verification_required"
    assert result.unknown_rules[0].requires_verification is True


def test_unsupported_rule_group_requires_manual_verification():
    result = evaluate_rules(
        startup_profile=profile(dpiit_recognized=True),
        rules=[
            rule(
                "dpiit_recognized",
                "equals",
                True,
                rule_group="either",
            )
        ],
        application_status="unknown",
        as_of_date=date(2026, 1, 15),
    )

    assert result.result == "verification_required"


def test_closed_application_overrides_rule_outcome():
    result = evaluate_rules(
        startup_profile=profile(
            incorporation_date=date(2024, 1, 15),
            dpiit_recognized=True,
        ),
        rules=SISFS_RULES,
        application_status="closed",
        as_of_date=date(2026, 1, 15),
    )

    assert result.result == "application_closed"


def test_unknown_application_status_does_not_block_eligibility():
    result = evaluate_rules(
        startup_profile=profile(
            incorporation_date=date(2024, 1, 15),
            dpiit_recognized=True,
        ),
        rules=SISFS_RULES,
        application_status="unknown",
        as_of_date=date(2026, 1, 15),
    )

    assert result.result == "eligible"


def test_empty_rule_set_requires_manual_verification():
    result = evaluate_rules(
        startup_profile=profile(),
        rules=[],
        application_status="unknown",
        as_of_date=date(2026, 1, 15),
    )

    assert result.result == "verification_required"
    assert result.engine_version == "rules-v2"
    assert not result.matched_rules
    assert not result.failed_rules
    assert not result.unknown_rules
    assert result.explanation == (
        "Manual verification is required because the verified scheme version "
        "has no executable eligibility rules."
    )
