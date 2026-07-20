from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MISSING = object()


@dataclass(frozen=True)
class RuleResult:
    field_path: str
    operator: str
    expected: Any
    actual: Any
    status: str


def get_path(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return MISSING
        current = current[key]
    return current


def evaluate_rule(
    profile: dict[str, Any], field_path: str, operator: str, expected: Any
) -> RuleResult:
    actual = get_path(profile, field_path)
    if actual is MISSING or actual is None:
        return RuleResult(field_path, operator, expected, None, "unknown")

    operations = {
        "equals": lambda: actual == expected,
        "not_equals": lambda: actual != expected,
        "in": lambda: actual in expected,
        "not_in": lambda: actual not in expected,
        "greater_than": lambda: actual > expected,
        "greater_or_equal": lambda: actual >= expected,
        "less_than": lambda: actual < expected,
        "less_or_equal": lambda: actual <= expected,
        "between": lambda: expected[0] <= actual <= expected[1],
        "contains_any": lambda: bool(set(actual) & set(expected)),
        "contains_all": lambda: set(expected).issubset(set(actual)),
        "exists": lambda: actual is not None,
        "not_exists": lambda: actual is None,
    }
    if operator not in operations:
        raise ValueError(f"Unsupported eligibility operator: {operator}")
    return RuleResult(
        field_path, operator, expected, actual, "matched" if operations[operator]() else "failed"
    )
