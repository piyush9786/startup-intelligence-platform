from __future__ import annotations

import re
from calendar import monthrange
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

ENGINE_VERSION = "rules-v1"
_MISSING = object()
_TOKEN_RE = re.compile(r"[^a-z0-9]+")


class RuleOutcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ResolvedValue:
    value: Any = _MISSING
    supported: bool = True
    reason: str = ""


@dataclass(frozen=True)
class RuleEvaluation:
    rule_id: str
    field_path: str
    operator: str
    expected_value: Any
    actual_value: Any
    mandatory: bool
    rule_group: str
    outcome: RuleOutcome
    reason: str
    evidence_text: str
    evidence_page: int | None
    requires_verification: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["outcome"] = self.outcome.value
        payload["expected_value"] = _json_ready(self.expected_value)
        payload["actual_value"] = _json_ready(self.actual_value)
        return payload


@dataclass(frozen=True)
class EligibilityEvaluation:
    result: str
    matched_rules: tuple[RuleEvaluation, ...]
    failed_rules: tuple[RuleEvaluation, ...]
    unknown_rules: tuple[RuleEvaluation, ...]
    explanation: str
    engine_version: str = ENGINE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "result": self.result,
            "matched_rules": [item.to_dict() for item in self.matched_rules],
            "failed_rules": [item.to_dict() for item in self.failed_rules],
            "unknown_rules": [item.to_dict() for item in self.unknown_rules],
            "explanation": self.explanation,
            "engine_version": self.engine_version,
        }


class EvaluationInputError(ValueError):
    """Raised when a verified canonical rule has an invalid evaluation shape."""


def _json_ready(value: Any) -> Any:
    if value is _MISSING:
        return None
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {
            str(key): _json_ready(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_ready(item) for item in value]
    return value


def _normalize_token(value: Any) -> str:
    return _TOKEN_RE.sub("_", str(value).strip().casefold()).strip("_")


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple, set, frozenset)):
        return list(value)
    return [value]


def _is_present(value: Any) -> bool:
    if value is _MISSING or value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, frozenset, dict)):
        return bool(value)
    return True


def _values_equal(actual: Any, expected: Any) -> bool:
    if isinstance(actual, str) or isinstance(expected, str):
        return _normalize_token(actual) == _normalize_token(expected)
    return actual == expected


def _decimal(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise EvaluationInputError("Boolean values cannot be used in numeric comparisons.")
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise EvaluationInputError(
            f"Value {value!r} cannot be used in a numeric comparison."
        ) from exc


def _add_calendar_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def _elapsed_months_rounded_up(start: date, end: date) -> int:
    months = (end.year - start.year) * 12 + end.month - start.month
    anniversary = _add_calendar_months(start, months)

    if anniversary > end:
        months -= 1
        anniversary = _add_calendar_months(start, months)

    if anniversary < end:
        months += 1

    return months


def _profile_data(profile: Any) -> dict[str, Any]:
    value = getattr(profile, "profile_data", None)
    return value if isinstance(value, dict) else {}


def resolve_profile_field(
    *,
    startup_profile: Any,
    field_path: str,
    as_of_date: date,
) -> ResolvedValue:
    normalized = field_path.strip()

    if normalized == "dpiit_recognized":
        value = getattr(startup_profile, "dpiit_recognized", None)
        if value is None:
            return ResolvedValue(reason="DPIIT recognition has not been provided.")
        return ResolvedValue(value=value)

    if normalized == "startup_age_months":
        incorporated = getattr(startup_profile, "incorporation_date", None)
        if incorporated is None:
            return ResolvedValue(reason="The incorporation date has not been provided.")
        if incorporated > as_of_date:
            return ResolvedValue(reason="The incorporation date is later than the assessment date.")
        return ResolvedValue(value=_elapsed_months_rounded_up(incorporated, as_of_date))

    data = _profile_data(startup_profile)

    if normalized == "eligible_entity_type":
        if "entity_types" in data:
            return ResolvedValue(value=data["entity_types"])
        if "entity_type" in data:
            return ResolvedValue(value=data["entity_type"])

        # StartupProfile is explicitly a startup-facing profile. This default makes
        # startup-only schemes evaluable while correctly failing AIF-only schemes.
        return ResolvedValue(value=["startup"])

    if normalized == "regulatory_registration":
        if "regulatory_registrations" in data:
            return ResolvedValue(value=data["regulatory_registrations"])
        if "regulatory_registration" in data:
            return ResolvedValue(value=data["regulatory_registration"])
        return ResolvedValue(reason="Regulatory registrations have not been provided.")

    return ResolvedValue(
        supported=False,
        reason=f"Unsupported eligibility field path: {field_path!r}.",
    )


def _evaluate_operator(
    *,
    operator: str,
    actual: Any,
    expected: Any,
) -> bool:
    if operator == "exists":
        return _is_present(actual)
    if operator == "not_exists":
        return not _is_present(actual)

    if actual is _MISSING or actual is None:
        raise LookupError

    if operator == "equals":
        return _values_equal(actual, expected)
    if operator == "not_equals":
        return not _values_equal(actual, expected)

    if operator in {"in", "not_in"}:
        matches = any(_values_equal(actual, item) for item in _as_list(expected))
        return matches if operator == "in" else not matches

    if operator in {"contains_any", "contains_all"}:
        actual_values = _as_list(actual)
        expected_values = _as_list(expected)
        matches = [
            any(_values_equal(actual_item, expected_item) for actual_item in actual_values)
            for expected_item in expected_values
        ]
        return any(matches) if operator == "contains_any" else all(matches)

    if operator == "greater_than":
        return _decimal(actual) > _decimal(expected)
    if operator == "greater_or_equal":
        return _decimal(actual) >= _decimal(expected)
    if operator == "less_than":
        return _decimal(actual) < _decimal(expected)
    if operator == "less_or_equal":
        return _decimal(actual) <= _decimal(expected)

    if operator == "between":
        bounds = _as_list(expected)
        if len(bounds) != 2:
            raise EvaluationInputError("The between operator requires exactly two expected values.")
        lower, upper = (_decimal(bounds[0]), _decimal(bounds[1]))
        actual_decimal = _decimal(actual)
        return lower <= actual_decimal <= upper

    raise EvaluationInputError(f"Unsupported eligibility operator: {operator!r}.")


def _result_reason(
    *,
    field_path: str,
    operator: str,
    expected: Any,
    actual: Any,
    passed: bool,
) -> str:
    verb = "satisfied" if passed else "did not satisfy"
    return (
        f"{field_path} {verb} {operator} "
        f"(actual={_json_ready(actual)!r}, expected={_json_ready(expected)!r})."
    )


def evaluate_rule(
    *,
    startup_profile: Any,
    rule: Any,
    as_of_date: date,
) -> RuleEvaluation:
    field_path = str(rule.field_path).strip()
    operator = str(rule.operator).strip()
    rule_group = str(getattr(rule, "rule_group", "") or "").strip()
    expected = getattr(rule, "expected_value", None)
    mandatory = bool(getattr(rule, "mandatory", True))
    evidence_text = str(getattr(rule, "evidence_text", "") or "")
    evidence_page = getattr(rule, "evidence_page", None)
    rule_id = str(getattr(rule, "id", ""))

    if rule_group not in {"", "all"}:
        return RuleEvaluation(
            rule_id=rule_id,
            field_path=field_path,
            operator=operator,
            expected_value=expected,
            actual_value=None,
            mandatory=mandatory,
            rule_group=rule_group,
            outcome=RuleOutcome.UNKNOWN,
            reason=(f"Rule group {rule_group!r} is unsupported by eligibility engine v1."),
            evidence_text=evidence_text,
            evidence_page=evidence_page,
            requires_verification=True,
        )

    if not bool(getattr(rule, "manually_verified", False)):
        return RuleEvaluation(
            rule_id=rule_id,
            field_path=field_path,
            operator=operator,
            expected_value=expected,
            actual_value=None,
            mandatory=mandatory,
            rule_group=rule_group,
            outcome=RuleOutcome.UNKNOWN,
            reason="The canonical eligibility rule has not been manually verified.",
            evidence_text=evidence_text,
            evidence_page=evidence_page,
            requires_verification=True,
        )

    resolved = resolve_profile_field(
        startup_profile=startup_profile,
        field_path=field_path,
        as_of_date=as_of_date,
    )

    if not resolved.supported:
        return RuleEvaluation(
            rule_id=rule_id,
            field_path=field_path,
            operator=operator,
            expected_value=expected,
            actual_value=None,
            mandatory=mandatory,
            rule_group=rule_group,
            outcome=RuleOutcome.UNKNOWN,
            reason=resolved.reason,
            evidence_text=evidence_text,
            evidence_page=evidence_page,
            requires_verification=True,
        )

    try:
        passed = _evaluate_operator(
            operator=operator,
            actual=resolved.value,
            expected=expected,
        )
    except LookupError:
        return RuleEvaluation(
            rule_id=rule_id,
            field_path=field_path,
            operator=operator,
            expected_value=expected,
            actual_value=None,
            mandatory=mandatory,
            rule_group=rule_group,
            outcome=RuleOutcome.UNKNOWN,
            reason=resolved.reason or f"{field_path} has not been provided.",
            evidence_text=evidence_text,
            evidence_page=evidence_page,
        )
    except EvaluationInputError as exc:
        return RuleEvaluation(
            rule_id=rule_id,
            field_path=field_path,
            operator=operator,
            expected_value=expected,
            actual_value=_json_ready(resolved.value),
            mandatory=mandatory,
            rule_group=rule_group,
            outcome=RuleOutcome.UNKNOWN,
            reason=str(exc),
            evidence_text=evidence_text,
            evidence_page=evidence_page,
            requires_verification=True,
        )

    return RuleEvaluation(
        rule_id=rule_id,
        field_path=field_path,
        operator=operator,
        expected_value=expected,
        actual_value=_json_ready(resolved.value),
        mandatory=mandatory,
        rule_group=rule_group,
        outcome=RuleOutcome.PASS if passed else RuleOutcome.FAIL,
        reason=_result_reason(
            field_path=field_path,
            operator=operator,
            expected=expected,
            actual=resolved.value,
            passed=passed,
        ),
        evidence_text=evidence_text,
        evidence_page=evidence_page,
    )


def evaluate_rules(
    *,
    startup_profile: Any,
    rules: Iterable[Any],
    application_status: str,
    as_of_date: date | None = None,
) -> EligibilityEvaluation:
    assessment_date = as_of_date or date.today()
    ordered_rules = sorted(
        rules,
        key=lambda rule: (
            str(getattr(rule, "rule_group", "") or ""),
            str(getattr(rule, "field_path", "") or ""),
            str(getattr(rule, "operator", "") or ""),
            str(getattr(rule, "id", "") or ""),
        ),
    )

    evaluations = tuple(
        evaluate_rule(
            startup_profile=startup_profile,
            rule=rule,
            as_of_date=assessment_date,
        )
        for rule in ordered_rules
    )

    matched = tuple(item for item in evaluations if item.outcome == RuleOutcome.PASS)
    failed = tuple(item for item in evaluations if item.outcome == RuleOutcome.FAIL)
    unknown = tuple(item for item in evaluations if item.outcome == RuleOutcome.UNKNOWN)

    if str(application_status).strip().casefold() == "closed":
        result = "application_closed"
        explanation = "The scheme is currently marked as closed for applications."
    elif any(item.requires_verification for item in evaluations):
        result = "verification_required"
        explanation = (
            "Manual verification is required because at least one canonical rule "
            "or profile mapping is unsupported or invalid."
        )
    elif any(item.mandatory for item in failed):
        result = "ineligible"
        explanation = "One or more mandatory eligibility rules failed."
    elif any(item.mandatory for item in unknown):
        result = "insufficient_information"
        explanation = "No mandatory rule failed, but required profile information is missing."
    else:
        result = "eligible"
        explanation = "All mandatory eligibility rules passed."

    return EligibilityEvaluation(
        result=result,
        matched_rules=matched,
        failed_rules=failed,
        unknown_rules=unknown,
        explanation=explanation,
    )


def evaluate_scheme_eligibility(
    *,
    startup_profile: Any,
    scheme_version: Any,
    as_of_date: date | None = None,
) -> EligibilityEvaluation:
    return evaluate_rules(
        startup_profile=startup_profile,
        rules=scheme_version.eligibility_rules.all(),
        application_status=scheme_version.application_status,
        as_of_date=as_of_date,
    )
