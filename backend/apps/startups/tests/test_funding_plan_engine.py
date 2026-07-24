from datetime import date

import pytest

from apps.startups.services.funding_plan import (
    FundingPlanDependency,
    FundingPlanInputError,
    FundingPlanStep,
    order_funding_plan,
)

AS_OF_DATE = date(2026, 7, 24)


def step(
    step_id,
    *,
    urgency=100,
    relevance=100,
    source_position=1,
    status="unknown",
    opening_date=None,
    deadline=None,
    duration_min_days=None,
    duration_max_days=None,
    parallelizable=True,
):
    return FundingPlanStep(
        step_id=step_id,
        title=f"Complete {step_id}",
        item_type="scheme_opportunity",
        source_position=source_position,
        founder_urgency_rank=urgency,
        funding_relevance_rank=relevance,
        application_status=status,
        opening_date=opening_date,
        deadline=deadline,
        duration_min_days=duration_min_days,
        duration_max_days=duration_max_days,
        parallelizable=parallelizable,
    )


def dependency(
    relationship_id,
    predecessor,
    successor,
    *,
    dependency_type="hard",
):
    return FundingPlanDependency(
        relationship_id=relationship_id,
        predecessor_step_id=predecessor,
        successor_step_id=successor,
        dependency_type=dependency_type,
    )


def test_hard_dependency_overrides_priority():
    plan = order_funding_plan(
        steps=[
            step(
                "predecessor",
                urgency=100,
                relevance=100,
            ),
            step(
                "high-priority-target",
                urgency=1,
                relevance=1,
            ),
        ],
        dependencies=[
            dependency(
                "unlock-1",
                "predecessor",
                "high-priority-target",
            ),
        ],
        as_of_date=AS_OF_DATE,
    )

    assert [item["step_id"] for item in plan["steps"]] == [
        "predecessor",
        "high-priority-target",
    ]
    assert plan["steps"][1]["hard_predecessor_ids"] == ["predecessor"]


def test_multiple_predecessors_are_required():
    plan = order_funding_plan(
        steps=[
            step("first"),
            step("second"),
            step("target"),
        ],
        dependencies=[
            dependency(
                "unlock-first",
                "first",
                "target",
            ),
            dependency(
                "unlock-second",
                "second",
                "target",
            ),
        ],
        as_of_date=AS_OF_DATE,
    )

    assert plan["execution_waves"] == [
        {
            "wave": 1,
            "step_ids": [
                "first",
                "second",
            ],
        },
        {
            "wave": 2,
            "step_ids": ["target"],
        },
    ]
    assert plan["steps"][2]["hard_predecessor_ids"] == [
        "first",
        "second",
    ]


def test_independent_steps_share_parallel_wave():
    plan = order_funding_plan(
        steps=[
            step(
                "earlier",
                urgency=1,
            ),
            step(
                "later",
                urgency=2,
            ),
        ],
        dependencies=[],
        as_of_date=AS_OF_DATE,
    )

    assert plan["execution_wave_count"] == 1
    assert plan["next_step_ids"] == [
        "earlier",
        "later",
    ]


def test_nonparallel_urgent_step_is_isolated():
    plan = order_funding_plan(
        steps=[
            step(
                "urgent-review",
                urgency=1,
                parallelizable=False,
            ),
            step(
                "parallel-application",
                urgency=2,
            ),
        ],
        dependencies=[],
        as_of_date=AS_OF_DATE,
    )

    assert plan["execution_waves"] == [
        {
            "wave": 1,
            "step_ids": ["urgent-review"],
        },
        {
            "wave": 2,
            "step_ids": ["parallel-application"],
        },
    ]


def test_verified_deadline_orders_ready_steps():
    plan = order_funding_plan(
        steps=[
            step(
                "later-deadline",
                status="open",
                deadline=date(2026, 9, 30),
            ),
            step(
                "earlier-deadline",
                status="open",
                deadline=date(2026, 8, 15),
            ),
        ],
        dependencies=[],
        as_of_date=AS_OF_DATE,
    )

    assert [item["step_id"] for item in plan["steps"]] == [
        "earlier-deadline",
        "later-deadline",
    ]


def test_urgency_then_relevance_are_deterministic():
    plan = order_funding_plan(
        steps=[
            step(
                "lower-relevance",
                urgency=1,
                relevance=2,
            ),
            step(
                "higher-relevance",
                urgency=1,
                relevance=1,
            ),
            step(
                "lower-urgency",
                urgency=2,
                relevance=1,
            ),
        ],
        dependencies=[],
        as_of_date=AS_OF_DATE,
    )

    assert [item["step_id"] for item in plan["steps"]] == [
        "higher-relevance",
        "lower-relevance",
        "lower-urgency",
    ]


def test_supporting_dependency_does_not_block():
    plan = order_funding_plan(
        steps=[
            step("supporting-step"),
            step("target"),
        ],
        dependencies=[
            dependency(
                "support-1",
                "supporting-step",
                "target",
                dependency_type="supporting",
            ),
        ],
        as_of_date=AS_OF_DATE,
    )

    assert plan["execution_wave_count"] == 1

    target = next(item for item in plan["steps"] if item["step_id"] == "target")

    assert target["supporting_predecessor_ids"] == ["supporting-step"]
    assert target["hard_predecessor_ids"] == []


def test_hard_dependency_cycle_is_rejected():
    with pytest.raises(
        FundingPlanInputError,
        match="cycle",
    ):
        order_funding_plan(
            steps=[
                step("first"),
                step("second"),
            ],
            dependencies=[
                dependency(
                    "first-second",
                    "first",
                    "second",
                ),
                dependency(
                    "second-first",
                    "second",
                    "first",
                ),
            ],
            as_of_date=AS_OF_DATE,
        )


def test_processing_time_range_is_validated():
    with pytest.raises(
        FundingPlanInputError,
        match="inverted",
    ):
        order_funding_plan(
            steps=[
                step(
                    "invalid-duration",
                    duration_min_days=20,
                    duration_max_days=10,
                ),
            ],
            dependencies=[],
            as_of_date=AS_OF_DATE,
        )


def test_output_is_deterministic():
    steps = [
        step(
            "first",
            source_position=2,
        ),
        step(
            "second",
            source_position=1,
        ),
        step(
            "target",
            source_position=3,
        ),
    ]
    dependencies = [
        dependency(
            "unlock-first",
            "first",
            "target",
        ),
        dependency(
            "support-second",
            "second",
            "target",
            dependency_type="supporting",
        ),
    ]

    first = order_funding_plan(
        steps=steps,
        dependencies=dependencies,
        as_of_date=AS_OF_DATE,
    )
    second = order_funding_plan(
        steps=list(reversed(steps)),
        dependencies=list(reversed(dependencies)),
        as_of_date=AS_OF_DATE,
    )

    assert first == second
