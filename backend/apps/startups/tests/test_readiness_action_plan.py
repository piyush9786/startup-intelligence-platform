from datetime import date
from decimal import Decimal

from apps.startups.services import (
    ACTION_PLAN_VERSION,
    ReadinessEvaluation,
    ReadinessFinding,
    ReadinessOutcome,
    ReadinessPriority,
    ReadinessStatus,
    build_startup_readiness_action_plan,
)


def make_finding(
    *,
    code: str,
    priority: ReadinessPriority,
    outcome: ReadinessOutcome,
    action: str,
    actual_value=None,
) -> ReadinessFinding:
    return ReadinessFinding(
        code=code,
        field_path=f"profile.{code}",
        priority=priority,
        outcome=outcome,
        reason=f"Reason for {code}.",
        action=action,
        actual_value=actual_value,
    )


def make_evaluation(
    *,
    findings: tuple[ReadinessFinding, ...],
    status: ReadinessStatus = (ReadinessStatus.BLOCKED),
    engine_version: str = "test-readiness-engine",
) -> ReadinessEvaluation:
    return ReadinessEvaluation(
        status=status,
        score=50,
        critical_score=40,
        recommended_score=70,
        findings=findings,
        summary="Test readiness evaluation.",
        engine_version=engine_version,
    )


def test_action_plan_orders_priority_then_outcome():
    findings = (
        make_finding(
            code="critical_incomplete",
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.INCOMPLETE,
            action="Complete critical field.",
        ),
        make_finding(
            code="recommended_invalid",
            priority=ReadinessPriority.RECOMMENDED,
            outcome=ReadinessOutcome.INVALID,
            action="Correct recommended field.",
        ),
        make_finding(
            code="critical_missing",
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.MISSING,
            action="Add critical field.",
        ),
        make_finding(
            code="present",
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.PRESENT,
            action="No action required.",
        ),
        make_finding(
            code="critical_invalid",
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.INVALID,
            action="Correct critical field.",
        ),
        make_finding(
            code="recommended_missing",
            priority=ReadinessPriority.RECOMMENDED,
            outcome=ReadinessOutcome.MISSING,
            action="Add recommended field.",
        ),
        make_finding(
            code="recommended_incomplete",
            priority=ReadinessPriority.RECOMMENDED,
            outcome=ReadinessOutcome.INCOMPLETE,
            action="Complete recommended field.",
        ),
    )

    plan = build_startup_readiness_action_plan(
        evaluation=make_evaluation(
            findings=findings,
        )
    )

    assert [item.code for item in plan.items] == [
        "critical_invalid",
        "critical_missing",
        "critical_incomplete",
        "recommended_invalid",
        "recommended_missing",
        "recommended_incomplete",
    ]
    assert [item.position for item in plan.items] == [1, 2, 3, 4, 5, 6]


def test_action_plan_preserves_source_order_within_bucket():
    findings = tuple(
        make_finding(
            code=code,
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.MISSING,
            action=f"Add {code}.",
        )
        for code in (
            "first",
            "second",
            "third",
        )
    )

    plan = build_startup_readiness_action_plan(
        evaluation=make_evaluation(
            findings=findings,
        )
    )

    assert [item.code for item in plan.items] == [
        "first",
        "second",
        "third",
    ]


def test_action_plan_counts_and_next_action():
    findings = (
        make_finding(
            code="recommended_missing",
            priority=ReadinessPriority.RECOMMENDED,
            outcome=ReadinessOutcome.MISSING,
            action="Add recommendation.",
        ),
        make_finding(
            code="critical_invalid",
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.INVALID,
            action="Correct blocker.",
        ),
        make_finding(
            code="critical_incomplete",
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.INCOMPLETE,
            action="Complete blocker.",
        ),
    )

    plan = build_startup_readiness_action_plan(
        evaluation=make_evaluation(
            findings=findings,
        )
    )

    assert plan.has_actions is True
    assert plan.blocker_count == 2
    assert plan.recommendation_count == 1
    assert plan.total_action_count == 3
    assert plan.next_action == "Correct blocker."


def test_ready_evaluation_produces_empty_plan():
    findings = (
        make_finding(
            code="complete",
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.PRESENT,
            action="No action required.",
        ),
    )

    plan = build_startup_readiness_action_plan(
        evaluation=make_evaluation(
            findings=findings,
            status=ReadinessStatus.READY,
        )
    )

    assert plan.readiness_status == (ReadinessStatus.READY)
    assert plan.has_actions is False
    assert plan.blocker_count == 0
    assert plan.recommendation_count == 0
    assert plan.total_action_count == 0
    assert plan.next_action is None
    assert plan.items == ()


def test_action_plan_output_is_json_ready():
    finding = make_finding(
        code="business_metrics",
        priority=ReadinessPriority.RECOMMENDED,
        outcome=ReadinessOutcome.INVALID,
        action="Correct business metrics.",
        actual_value={
            "turnover": Decimal("1250000.50"),
            "as_of_date": date(2026, 7, 21),
        },
    )

    payload = build_startup_readiness_action_plan(
        evaluation=make_evaluation(
            findings=(finding,),
        )
    ).to_dict()

    assert payload["items"][0]["actual_value"] == {
        "as_of_date": "2026-07-21",
        "turnover": "1250000.50",
    }
    assert payload["items"][0]["priority"] == ("recommended")
    assert payload["items"][0]["outcome"] == ("invalid")


def test_action_plan_preserves_source_metadata():
    plan = build_startup_readiness_action_plan(
        evaluation=make_evaluation(
            findings=(),
            status=(ReadinessStatus.READY_WITH_RECOMMENDATIONS),
            engine_version="custom-readiness-v9",
        )
    )

    payload = plan.to_dict()

    assert payload["readiness_status"] == ("ready_with_recommendations")
    assert payload["source_engine_version"] == ("custom-readiness-v9")
    assert payload["planner_version"] == (ACTION_PLAN_VERSION)


def test_action_plan_is_deterministic():
    evaluation = make_evaluation(
        findings=(
            make_finding(
                code="critical_missing",
                priority=ReadinessPriority.CRITICAL,
                outcome=ReadinessOutcome.MISSING,
                action="Add critical field.",
            ),
            make_finding(
                code="recommended_invalid",
                priority=(ReadinessPriority.RECOMMENDED),
                outcome=ReadinessOutcome.INVALID,
                action="Correct recommended field.",
            ),
        )
    )

    first = build_startup_readiness_action_plan(
        evaluation=evaluation,
    ).to_dict()
    second = build_startup_readiness_action_plan(
        evaluation=evaluation,
    ).to_dict()

    assert first == second
