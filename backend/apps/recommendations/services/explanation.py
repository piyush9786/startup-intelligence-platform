from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from typing import Any

EXPLANATION_VERSION = "eligibility-explanation-v1"

_FIELD_LABELS = {
    "dpiit_recognized": "DPIIT recognition",
    "startup_age_months": "startup age",
    "eligible_entity_type": "legal entity type",
    "regulatory_registration": "regulatory registration",
}


def _value(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set, frozenset)):
        return list(value)
    return [value]


def _deduplicate(items: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _humanize_token(value: Any) -> str:
    return str(value).replace("_", " ").replace("-", " ").strip()


def _field_label(field_path: str) -> str:
    return _FIELD_LABELS.get(field_path, _humanize_token(field_path))


def _decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _format_months(value: Any) -> str:
    numeric = _decimal(value)
    if numeric is None:
        return str(value)

    months = int(numeric)
    years, remaining_months = divmod(months, 12)
    parts: list[str] = []
    if years:
        parts.append(f"{years} year{'s' if years != 1 else ''}")
    if remaining_months:
        parts.append(
            f"{remaining_months} month{'s' if remaining_months != 1 else ''}"
        )
    return " ".join(parts) or "0 months"


def _format_value(field_path: str, value: Any) -> str:
    if value is None:
        return "not provided"
    if field_path == "startup_age_months":
        return _format_months(value)
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (list, tuple, set, frozenset)):
        values = [_humanize_token(item) for item in value]
        return ", ".join(values) if values else "not provided"
    return _humanize_token(value)


def _operator_text(operator: str, expected: Any, field_path: str) -> str:
    expected_text = _format_value(field_path, expected)
    labels = {
        "equals": f"must be {expected_text}",
        "not_equals": f"must not be {expected_text}",
        "in": f"must be one of {expected_text}",
        "not_in": f"must not be one of {expected_text}",
        "greater_than": f"must be greater than {expected_text}",
        "greater_or_equal": f"must be at least {expected_text}",
        "less_than": f"must be less than {expected_text}",
        "less_or_equal": f"must be no more than {expected_text}",
        "between": f"must be between {expected_text}",
        "contains_any": f"must include at least one of {expected_text}",
        "contains_all": f"must include all of {expected_text}",
        "exists": "must be provided",
        "not_exists": "must not be provided",
    }
    return labels.get(operator, f"must satisfy {operator} {expected_text}")


def _passed_message(rule: Any) -> str:
    field_path = str(_value(rule, "field_path", "") or "")
    actual = _value(rule, "actual_value")
    expected = _value(rule, "expected_value")

    if field_path == "dpiit_recognized":
        return "Your startup has the DPIIT recognition status required by this scheme."

    if field_path == "startup_age_months":
        return (
            f"Your startup age is {_format_months(actual)}, which is within "
            f"the scheme limit of {_format_months(expected)}."
        )

    if field_path == "eligible_entity_type":
        return (
            f"Your legal entity type ({_format_value(field_path, actual)}) "
            "matches this scheme."
        )

    if field_path == "regulatory_registration":
        return (
            "Your regulatory registration information satisfies this "
            "scheme requirement."
        )

    label = _field_label(field_path)
    operator = str(_value(rule, "operator", ""))
    requirement = _operator_text(operator, expected, field_path)
    return (
        f"Your {label} ({_format_value(field_path, actual)}) satisfies "
        f"the requirement that it {requirement}."
    )


def _failed_message(rule: Any) -> str:
    field_path = str(_value(rule, "field_path", "") or "")
    operator = str(_value(rule, "operator", "") or "")
    actual = _value(rule, "actual_value")
    expected = _value(rule, "expected_value")

    if field_path == "dpiit_recognized":
        return (
            "This scheme requires DPIIT recognition, but your startup profile "
            "does not currently confirm it."
        )

    if field_path == "startup_age_months" and operator in {
        "less_than",
        "less_or_equal",
    }:
        return (
            f"Your startup is {_format_months(actual)} old, but this scheme "
            f"accepts startups up to {_format_months(expected)} old."
        )

    if field_path == "eligible_entity_type":
        return (
            f"Your legal entity type is {_format_value(field_path, actual)}, "
            f"but this scheme accepts {_format_value(field_path, expected)}."
        )

    if field_path == "regulatory_registration":
        return (
            "Your current regulatory registrations do not match the "
            f"registration required by this scheme: {_format_value(field_path, expected)}."
        )

    label = _field_label(field_path)
    return (
        f"Your {label} is {_format_value(field_path, actual)}, but it "
        f"{_operator_text(operator, expected, field_path)}."
    )


def _unknown_message(rule: Any) -> str:
    field_path = str(_value(rule, "field_path", "") or "")
    reason = str(_value(rule, "reason", "") or "").strip()

    messages = {
        "dpiit_recognized": (
            "Add your DPIIT recognition status so this requirement can be checked."
        ),
        "startup_age_months": (
            "Add a valid incorporation date so the platform can calculate startup age."
        ),
        "eligible_entity_type": (
            "Confirm your legal entity type so this requirement can be checked."
        ),
        "regulatory_registration": (
            "Add your regulatory registrations so this requirement can be checked."
        ),
    }
    if field_path in messages:
        return messages[field_path]
    if reason:
        return reason
    return f"Add your {_field_label(field_path)} so this requirement can be checked."


def _next_step(rule: Any, *, outcome: str) -> str:
    field_path = str(_value(rule, "field_path", "") or "")
    expected = _value(rule, "expected_value")

    if outcome == "unknown":
        return _unknown_message(rule)

    if field_path == "dpiit_recognized":
        return (
            "Obtain DPIIT recognition, or correct the recognition status in "
            "your startup profile before applying."
        )
    if field_path == "startup_age_months":
        return "Consider schemes with a higher startup-age limit."
    if field_path == "eligible_entity_type":
        return (
            "Confirm that your legal entity type is recorded correctly and "
            "look for schemes that support your entity type."
        )
    if field_path == "regulatory_registration":
        return (
            "Obtain or add the required regulatory registration: "
            f"{_format_value(field_path, expected)}."
        )
    return (
        f"Update or verify your {_field_label(field_path)} before applying "
        "to this scheme."
    )


def _summary(
    *,
    result: str,
    failed_rules: list[Any],
    unknown_rules: list[Any],
) -> str:
    mandatory_failed = sum(
        1 for rule in failed_rules if bool(_value(rule, "mandatory", True))
    )
    mandatory_unknown = sum(
        1 for rule in unknown_rules if bool(_value(rule, "mandatory", True))
    )

    summaries = {
        "eligible": (
            "You meet all mandatory eligibility requirements currently "
            "available for this scheme."
        ),
        "application_closed": (
            "Your profile was evaluated, but applications for this scheme "
            "are currently closed."
        ),
        "verification_required": (
            "This result needs manual verification before you rely on it."
        ),
        "likely_eligible": (
            "Your profile appears to match this scheme, but eligibility is "
            "not fully confirmed."
        ),
        "conditionally_eligible": (
            "You may qualify after completing the outstanding requirements."
        ),
    }
    if result in summaries:
        return summaries[result]
    if result == "ineligible":
        count = mandatory_failed or len(failed_rules)
        return (
            f"You are not currently eligible because {count} mandatory "
            f"requirement{'s were' if count != 1 else ' was'} not met."
        )
    if result == "insufficient_information":
        count = mandatory_unknown or len(unknown_rules)
        return (
            f"Eligibility cannot be confirmed because {count} required "
            f"profile detail{'s are' if count != 1 else ' is'} missing."
        )
    return "The scheme was evaluated using the current startup profile."


def build_eligibility_explanation(assessment: Any) -> dict[str, Any]:
    result = str(_value(assessment, "result", "") or "")
    matched_rules = list(_value(assessment, "matched_rules", []) or [])
    failed_rules = list(_value(assessment, "failed_rules", []) or [])
    unknown_rules = list(_value(assessment, "unknown_rules", []) or [])

    next_steps = [
        *(_next_step(rule, outcome="failed") for rule in failed_rules),
        *(_next_step(rule, outcome="unknown") for rule in unknown_rules),
    ]
    if result == "application_closed":
        next_steps.append(
            "Check the official scheme page for the next application window."
        )
    if result == "verification_required":
        next_steps.append(
            "Review the scheme evidence or ask an administrator to verify "
            "the unsupported rule."
        )

    return {
        "version": EXPLANATION_VERSION,
        "result": result,
        "summary": _summary(
            result=result,
            failed_rules=failed_rules,
            unknown_rules=unknown_rules,
        ),
        "passed_checks": [_passed_message(rule) for rule in matched_rules],
        "unmet_requirements": [_failed_message(rule) for rule in failed_rules],
        "missing_information": [_unknown_message(rule) for rule in unknown_rules],
        "next_steps": _deduplicate(next_steps),
    }
