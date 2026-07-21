from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .readiness import (
    ReadinessEvaluation,
    ReadinessFinding,
    ReadinessOutcome,
    ReadinessPriority,
    ReadinessStatus,
)

ACTION_PLAN_VERSION = "startup-readiness-action-plan-v1"

_PRIORITY_ORDER = {
    ReadinessPriority.CRITICAL: 0,
    ReadinessPriority.RECOMMENDED: 1,
}
_OUTCOME_ORDER = {
    ReadinessOutcome.INVALID: 0,
    ReadinessOutcome.MISSING: 1,
    ReadinessOutcome.INCOMPLETE: 2,
}


@dataclass(frozen=True)
class ReadinessActionItem:
    position: int
    code: str
    field_path: str
    priority: ReadinessPriority
    outcome: ReadinessOutcome
    reason: str
    action: str
    actual_value: Any = None

    @classmethod
    def from_finding(
        cls,
        *,
        position: int,
        finding: ReadinessFinding,
    ) -> ReadinessActionItem:
        payload = finding.to_dict()
        return cls(
            position=position,
            code=finding.code,
            field_path=finding.field_path,
            priority=finding.priority,
            outcome=finding.outcome,
            reason=finding.reason,
            action=finding.action,
            actual_value=payload["actual_value"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "position": self.position,
            "code": self.code,
            "field_path": self.field_path,
            "priority": self.priority.value,
            "outcome": self.outcome.value,
            "reason": self.reason,
            "action": self.action,
            "actual_value": self.actual_value,
        }


@dataclass(frozen=True)
class ReadinessActionPlan:
    readiness_status: ReadinessStatus
    blocker_count: int
    recommendation_count: int
    next_action: str | None
    items: tuple[ReadinessActionItem, ...]
    source_engine_version: str
    planner_version: str = ACTION_PLAN_VERSION

    @property
    def has_actions(self) -> bool:
        return bool(self.items)

    @property
    def total_action_count(self) -> int:
        return len(self.items)

    def to_dict(self) -> dict[str, Any]:
        return {
            "readiness_status": self.readiness_status.value,
            "has_actions": self.has_actions,
            "blocker_count": self.blocker_count,
            "recommendation_count": (self.recommendation_count),
            "total_action_count": self.total_action_count,
            "next_action": self.next_action,
            "items": [item.to_dict() for item in self.items],
            "source_engine_version": (self.source_engine_version),
            "planner_version": self.planner_version,
        }


def _action_sort_key(
    indexed_finding: tuple[int, ReadinessFinding],
) -> tuple[int, int, int]:
    source_position, finding = indexed_finding
    return (
        _PRIORITY_ORDER[finding.priority],
        _OUTCOME_ORDER[finding.outcome],
        source_position,
    )


def build_startup_readiness_action_plan(
    *,
    evaluation: ReadinessEvaluation,
) -> ReadinessActionPlan:
    actionable = [
        (source_position, finding)
        for source_position, finding in enumerate(
            evaluation.findings,
        )
        if finding.outcome != ReadinessOutcome.PRESENT
    ]
    actionable.sort(key=_action_sort_key)

    items = tuple(
        ReadinessActionItem.from_finding(
            position=position,
            finding=finding,
        )
        for position, (_source_position, finding) in enumerate(
            actionable,
            start=1,
        )
    )
    blocker_count = sum(item.priority == ReadinessPriority.CRITICAL for item in items)
    recommendation_count = sum(item.priority == ReadinessPriority.RECOMMENDED for item in items)
    next_action = items[0].action if items else None

    return ReadinessActionPlan(
        readiness_status=evaluation.status,
        blocker_count=blocker_count,
        recommendation_count=recommendation_count,
        next_action=next_action,
        items=items,
        source_engine_version=(evaluation.engine_version),
    )
