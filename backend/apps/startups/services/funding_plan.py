from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

FUNDING_PLAN_VERSION = "startup-funding-plan-v1"

VALID_APPLICATION_STATUSES = frozenset(
    {
        "open",
        "rolling",
        "upcoming",
        "unknown",
        "closed",
    }
)

VALID_DEPENDENCY_TYPES = frozenset(
    {
        "hard",
        "supporting",
    }
)


class FundingPlanInputError(ValueError):
    """Raised when funding-plan inputs cannot form a valid plan."""


@dataclass(frozen=True, slots=True)
class FundingPlanStep:
    step_id: str
    title: str
    item_type: str
    source_position: int
    founder_urgency_rank: int = 100
    funding_relevance_rank: int = 100
    application_status: str = "unknown"
    opening_date: date | None = None
    deadline: date | None = None
    duration_min_days: int | None = None
    duration_max_days: int | None = None
    parallelizable: bool = True
    metadata: dict[str, Any] = field(
        default_factory=dict,
    )


@dataclass(frozen=True, slots=True)
class FundingPlanDependency:
    relationship_id: str
    predecessor_step_id: str
    successor_step_id: str
    dependency_type: str = "hard"
    metadata: dict[str, Any] = field(
        default_factory=dict,
    )


def _validate_step(
    step: FundingPlanStep,
) -> None:
    if not step.step_id.strip():
        raise FundingPlanInputError("Every funding-plan step requires a step ID.")

    if step.step_id != step.step_id.strip():
        raise FundingPlanInputError(f"Step ID {step.step_id!r} contains outer whitespace.")

    if not step.title.strip():
        raise FundingPlanInputError(f"Step {step.step_id!r} requires a title.")

    if not step.item_type.strip():
        raise FundingPlanInputError(f"Step {step.step_id!r} requires an item type.")

    if step.source_position < 1:
        raise FundingPlanInputError(f"Step {step.step_id!r} has an invalid source position.")

    if step.founder_urgency_rank < 1:
        raise FundingPlanInputError(f"Step {step.step_id!r} has an invalid urgency rank.")

    if step.funding_relevance_rank < 1:
        raise FundingPlanInputError(f"Step {step.step_id!r} has an invalid relevance rank.")

    if step.application_status not in VALID_APPLICATION_STATUSES:
        raise FundingPlanInputError(f"Step {step.step_id!r} has an invalid application status.")

    if (
        step.opening_date is not None
        and step.deadline is not None
        and step.opening_date > step.deadline
    ):
        raise FundingPlanInputError(f"Step {step.step_id!r} opens after its deadline.")

    has_minimum = step.duration_min_days is not None
    has_maximum = step.duration_max_days is not None

    if has_minimum != has_maximum:
        raise FundingPlanInputError(
            f"Step {step.step_id!r} must provide both processing-time bounds."
        )

    if not has_minimum:
        return

    assert step.duration_min_days is not None
    assert step.duration_max_days is not None

    if step.duration_min_days < 0 or step.duration_max_days < 0:
        raise FundingPlanInputError(f"Step {step.step_id!r} has a negative processing-time bound.")

    if step.duration_min_days > step.duration_max_days:
        raise FundingPlanInputError(f"Step {step.step_id!r} has an inverted processing-time range.")


def _validate_steps(
    steps: tuple[FundingPlanStep, ...],
) -> dict[str, FundingPlanStep]:
    step_by_id: dict[str, FundingPlanStep] = {}

    for step in steps:
        _validate_step(step)

        if step.step_id in step_by_id:
            raise FundingPlanInputError(f"Duplicate funding-plan step ID: {step.step_id}")

        step_by_id[step.step_id] = step

    return step_by_id


def _validate_dependencies(
    dependencies: tuple[
        FundingPlanDependency,
        ...,
    ],
    *,
    step_by_id: dict[str, FundingPlanStep],
) -> tuple[
    dict[str, set[str]],
    dict[str, set[str]],
]:
    hard_predecessors = {step_id: set() for step_id in step_by_id}
    supporting_predecessors = {step_id: set() for step_id in step_by_id}

    relationship_ids: set[str] = set()
    relationship_keys: set[tuple[str, str, str]] = set()

    for relationship in dependencies:
        if not relationship.relationship_id.strip():
            raise FundingPlanInputError("Every dependency requires a relationship ID.")

        if relationship.relationship_id in relationship_ids:
            raise FundingPlanInputError(
                f"Duplicate dependency relationship ID: {relationship.relationship_id}"
            )

        relationship_ids.add(relationship.relationship_id)

        if relationship.dependency_type not in VALID_DEPENDENCY_TYPES:
            raise FundingPlanInputError(
                f"Dependency {relationship.relationship_id!r} has an invalid dependency type."
            )

        if relationship.predecessor_step_id not in step_by_id:
            raise FundingPlanInputError(
                f"Dependency {relationship.relationship_id!r} references an unknown predecessor."
            )

        if relationship.successor_step_id not in step_by_id:
            raise FundingPlanInputError(
                f"Dependency {relationship.relationship_id!r} references an unknown successor."
            )

        if relationship.predecessor_step_id == relationship.successor_step_id:
            raise FundingPlanInputError("A funding-plan step cannot depend on itself.")

        relationship_key = (
            relationship.predecessor_step_id,
            relationship.successor_step_id,
            relationship.dependency_type,
        )

        if relationship_key in relationship_keys:
            raise FundingPlanInputError(f"Duplicate funding-plan dependency: {relationship_key}")

        relationship_keys.add(relationship_key)

        target = (
            hard_predecessors if relationship.dependency_type == "hard" else supporting_predecessors
        )

        target[relationship.successor_step_id].add(relationship.predecessor_step_id)

    return (
        hard_predecessors,
        supporting_predecessors,
    )


def _application_window_rank(
    step: FundingPlanStep,
    *,
    as_of_date: date,
) -> int:
    if step.deadline is not None and step.deadline < as_of_date:
        return 5

    return {
        "open": 0,
        "rolling": 1,
        "upcoming": 2,
        "unknown": 3,
        "closed": 5,
    }[step.application_status]


def _step_sort_key(
    step: FundingPlanStep,
    *,
    as_of_date: date,
) -> tuple[
    int,
    date,
    int,
    int,
    date,
    int,
    str,
]:
    return (
        _application_window_rank(
            step,
            as_of_date=as_of_date,
        ),
        step.deadline or date.max,
        step.founder_urgency_rank,
        step.funding_relevance_rank,
        step.opening_date or date.max,
        step.source_position,
        step.step_id,
    )


def _dependency_record(
    relationship: FundingPlanDependency,
) -> dict[str, Any]:
    return {
        "relationship_id": (relationship.relationship_id),
        "predecessor_step_id": (relationship.predecessor_step_id),
        "successor_step_id": (relationship.successor_step_id),
        "dependency_type": (relationship.dependency_type),
        "metadata": dict(relationship.metadata),
    }


def _ordered_step_record(
    *,
    step: FundingPlanStep,
    position: int,
    execution_wave: int,
    hard_predecessors: set[str],
    supporting_predecessors: set[str],
) -> dict[str, Any]:
    if hard_predecessors:
        dependency_status = "waiting_on_hard_dependencies"
    elif execution_wave == 1:
        dependency_status = "ready"
    else:
        dependency_status = "sequenced_by_priority"

    estimated_processing_days = None

    if step.duration_min_days is not None:
        estimated_processing_days = {
            "minimum": step.duration_min_days,
            "maximum": step.duration_max_days,
        }

    return {
        "position": position,
        "execution_wave": execution_wave,
        "step_id": step.step_id,
        "item_type": step.item_type,
        "title": step.title,
        "dependency_status": dependency_status,
        "hard_predecessor_ids": sorted(hard_predecessors),
        "supporting_predecessor_ids": sorted(supporting_predecessors),
        "parallelizable": step.parallelizable,
        "founder_urgency_rank": (step.founder_urgency_rank),
        "funding_relevance_rank": (step.funding_relevance_rank),
        "application_window": {
            "status": step.application_status,
            "opening_date": (
                step.opening_date.isoformat() if step.opening_date is not None else None
            ),
            "deadline": (step.deadline.isoformat() if step.deadline is not None else None),
        },
        "estimated_processing_days": (estimated_processing_days),
        "source_position": step.source_position,
        "metadata": dict(step.metadata),
    }


def order_funding_plan(
    *,
    steps: list[FundingPlanStep],
    dependencies: list[FundingPlanDependency],
    as_of_date: date,
) -> dict[str, Any]:
    step_tuple = tuple(steps)
    dependency_tuple = tuple(dependencies)

    step_by_id = _validate_steps(step_tuple)

    (
        hard_predecessors,
        supporting_predecessors,
    ) = _validate_dependencies(
        dependency_tuple,
        step_by_id=step_by_id,
    )

    remaining = set(step_by_id)
    completed: set[str] = set()
    execution_waves: list[list[str]] = []

    while remaining:
        ready = [
            step_by_id[step_id] for step_id in remaining if hard_predecessors[step_id] <= completed
        ]

        if not ready:
            unresolved = sorted(remaining)

            raise FundingPlanInputError(
                "Hard funding-plan dependencies contain a cycle involving: " + ", ".join(unresolved)
            )

        ready.sort(
            key=lambda step: _step_sort_key(
                step,
                as_of_date=as_of_date,
            )
        )

        first_step = ready[0]

        if first_step.parallelizable:
            selected = [step for step in ready if step.parallelizable]
        else:
            selected = [first_step]

        wave_step_ids = [step.step_id for step in selected]

        execution_waves.append(wave_step_ids)

        completed.update(wave_step_ids)
        remaining.difference_update(wave_step_ids)

    ordered_records: list[dict[str, Any]] = []
    position = 1

    for execution_wave, wave_step_ids in enumerate(
        execution_waves,
        start=1,
    ):
        for step_id in wave_step_ids:
            ordered_records.append(
                _ordered_step_record(
                    step=step_by_id[step_id],
                    position=position,
                    execution_wave=execution_wave,
                    hard_predecessors=(hard_predecessors[step_id]),
                    supporting_predecessors=(supporting_predecessors[step_id]),
                )
            )
            position += 1

    ordered_dependencies = sorted(
        (_dependency_record(relationship) for relationship in dependency_tuple),
        key=lambda relationship: (
            relationship["successor_step_id"],
            relationship["dependency_type"],
            relationship["predecessor_step_id"],
            relationship["relationship_id"],
        ),
    )

    return {
        "plan_version": FUNDING_PLAN_VERSION,
        "as_of_date": as_of_date.isoformat(),
        "total_step_count": len(ordered_records),
        "execution_wave_count": len(execution_waves),
        "next_step_ids": (list(execution_waves[0]) if execution_waves else []),
        "execution_waves": [
            {
                "wave": wave_number,
                "step_ids": list(step_ids),
            }
            for wave_number, step_ids in enumerate(
                execution_waves,
                start=1,
            )
        ],
        "steps": ordered_records,
        "dependencies": ordered_dependencies,
    }
