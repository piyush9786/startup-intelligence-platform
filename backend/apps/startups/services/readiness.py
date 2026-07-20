from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

from apps.startups.models import StartupProfile

ENGINE_VERSION = "startup-readiness-v1"
_TOKEN_RE = re.compile(r"[^a-z0-9]+")
_VALID_STAGES = frozenset(value for value, _label in StartupProfile.Stage.choices)
_OUTCOME_FACTORS = {
    "present": Decimal("1"),
    "incomplete": Decimal("0.5"),
    "missing": Decimal("0"),
    "invalid": Decimal("0"),
}


class ReadinessPriority(StrEnum):
    CRITICAL = "critical"
    RECOMMENDED = "recommended"


class ReadinessOutcome(StrEnum):
    PRESENT = "present"
    MISSING = "missing"
    INCOMPLETE = "incomplete"
    INVALID = "invalid"


class ReadinessStatus(StrEnum):
    READY = "ready"
    READY_WITH_RECOMMENDATIONS = "ready_with_recommendations"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class ReadinessFinding:
    code: str
    field_path: str
    priority: ReadinessPriority
    outcome: ReadinessOutcome
    reason: str
    action: str
    actual_value: Any = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["priority"] = self.priority.value
        payload["outcome"] = self.outcome.value
        payload["actual_value"] = _json_ready(
            self.actual_value,
        )
        return payload


@dataclass(frozen=True)
class ReadinessEvaluation:
    status: ReadinessStatus
    score: int
    critical_score: int
    recommended_score: int
    findings: tuple[ReadinessFinding, ...]
    summary: str
    engine_version: str = ENGINE_VERSION

    @property
    def critical_findings(
        self,
    ) -> tuple[ReadinessFinding, ...]:
        return tuple(item for item in self.findings if item.priority == ReadinessPriority.CRITICAL)

    @property
    def recommended_findings(
        self,
    ) -> tuple[ReadinessFinding, ...]:
        return tuple(
            item for item in self.findings if item.priority == ReadinessPriority.RECOMMENDED
        )

    @property
    def blocking_findings(
        self,
    ) -> tuple[ReadinessFinding, ...]:
        return tuple(
            item for item in self.critical_findings if item.outcome != ReadinessOutcome.PRESENT
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "score": self.score,
            "critical_score": self.critical_score,
            "recommended_score": (self.recommended_score),
            "findings": [item.to_dict() for item in self.findings],
            "blocking_findings": [item.to_dict() for item in self.blocking_findings],
            "summary": self.summary,
            "engine_version": self.engine_version,
        }


def _json_ready(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {
            str(key): _json_ready(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }
    if isinstance(
        value,
        (list, tuple, set, frozenset),
    ):
        return [_json_ready(item) for item in value]
    return value


def _normalize_token(value: Any) -> str:
    return _TOKEN_RE.sub(
        "_",
        str(value).strip().casefold(),
    ).strip("_")


def _nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _decimal(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise ValueError
    try:
        return Decimal(str(value))
    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError from exc


def _finding(
    *,
    code: str,
    field_path: str,
    priority: ReadinessPriority,
    outcome: ReadinessOutcome,
    reason: str,
    action: str,
    actual_value: Any = None,
) -> ReadinessFinding:
    return ReadinessFinding(
        code=code,
        field_path=field_path,
        priority=priority,
        outcome=outcome,
        reason=reason,
        action=action,
        actual_value=actual_value,
    )


def _check_startup_name(
    profile: Any,
) -> ReadinessFinding:
    value = getattr(profile, "startup_name", None)
    if not _nonblank(value):
        return _finding(
            code="startup_name",
            field_path="startup_name",
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.MISSING,
            reason="The startup name has not been provided.",
            action="Add the startup's commonly used name.",
            actual_value=value,
        )
    if len(value.strip()) < 2:
        return _finding(
            code="startup_name",
            field_path="startup_name",
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.INCOMPLETE,
            reason="The startup name is too short to be useful.",
            action="Provide the full startup name.",
            actual_value=value,
        )
    return _finding(
        code="startup_name",
        field_path="startup_name",
        priority=ReadinessPriority.CRITICAL,
        outcome=ReadinessOutcome.PRESENT,
        reason="The startup name is present.",
        action="No action required.",
        actual_value=value.strip(),
    )


def _check_stage(profile: Any) -> ReadinessFinding:
    value = getattr(profile, "stage", None)
    if not _nonblank(value):
        return _finding(
            code="stage",
            field_path="stage",
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.MISSING,
            reason="The startup stage has not been provided.",
            action="Select the startup's current stage.",
            actual_value=value,
        )
    if value not in _VALID_STAGES:
        return _finding(
            code="stage",
            field_path="stage",
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.INVALID,
            reason="The startup stage is not a supported value.",
            action=("Choose one of the supported startup stage values."),
            actual_value=value,
        )
    return _finding(
        code="stage",
        field_path="stage",
        priority=ReadinessPriority.CRITICAL,
        outcome=ReadinessOutcome.PRESENT,
        reason="The startup stage is valid.",
        action="No action required.",
        actual_value=value,
    )


def _check_incorporation_date(
    profile: Any,
    *,
    as_of_date: date,
) -> ReadinessFinding:
    value = getattr(
        profile,
        "incorporation_date",
        None,
    )
    if value is None:
        return _finding(
            code="incorporation_date",
            field_path="incorporation_date",
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.MISSING,
            reason=("The incorporation date has not been provided."),
            action=("Add the legal incorporation or registration date."),
        )
    if not isinstance(value, date):
        return _finding(
            code="incorporation_date",
            field_path="incorporation_date",
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.INVALID,
            reason="The incorporation date is not a date.",
            action="Provide a valid calendar date.",
            actual_value=value,
        )
    if value > as_of_date:
        return _finding(
            code="incorporation_date",
            field_path="incorporation_date",
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.INVALID,
            reason=("The incorporation date is later than the readiness assessment date."),
            action=("Correct the incorporation date before running eligibility."),
            actual_value=value,
        )
    return _finding(
        code="incorporation_date",
        field_path="incorporation_date",
        priority=ReadinessPriority.CRITICAL,
        outcome=ReadinessOutcome.PRESENT,
        reason="The incorporation date is valid.",
        action="No action required.",
        actual_value=value,
    )


def _check_dpiit_recognition(
    profile: Any,
) -> ReadinessFinding:
    value = getattr(
        profile,
        "dpiit_recognized",
        None,
    )
    if value is None:
        return _finding(
            code="dpiit_recognized",
            field_path="dpiit_recognized",
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.MISSING,
            reason=("DPIIT recognition status has not been provided."),
            action=("Record whether the startup is DPIIT recognized."),
        )
    if not isinstance(value, bool):
        return _finding(
            code="dpiit_recognized",
            field_path="dpiit_recognized",
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.INVALID,
            reason=("DPIIT recognition status must be true or false."),
            action=("Replace the value with an explicit boolean."),
            actual_value=value,
        )
    return _finding(
        code="dpiit_recognized",
        field_path="dpiit_recognized",
        priority=ReadinessPriority.CRITICAL,
        outcome=ReadinessOutcome.PRESENT,
        reason=("DPIIT recognition status is explicitly recorded."),
        action="No action required.",
        actual_value=value,
    )


def _as_tokens(value: Any) -> list[str] | None:
    if isinstance(value, str):
        values = [value]
    elif isinstance(
        value,
        (list, tuple, set, frozenset),
    ):
        values = list(value)
    else:
        return None

    tokens = [_normalize_token(item) for item in values if _nonblank(item)]
    return tokens


def _check_eligibility_context(
    profile: Any,
) -> ReadinessFinding:
    data = getattr(profile, "profile_data", None)
    if not isinstance(data, dict):
        return _finding(
            code="eligibility_context",
            field_path="profile_data",
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.INVALID,
            reason="Profile data must be a JSON object.",
            action=("Replace profile_data with an object of named values."),
            actual_value=data,
        )

    entity_value = data.get(
        "entity_types",
        data.get("entity_type"),
    )
    if entity_value is None:
        return _finding(
            code="eligibility_context",
            field_path="profile_data.entity_types",
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.PRESENT,
            reason=(
                "No entity override is set; the eligibility engine will use the startup default."
            ),
            action="No action required.",
            actual_value=["startup"],
        )

    entity_tokens = _as_tokens(entity_value)
    if entity_tokens is None:
        return _finding(
            code="eligibility_context",
            field_path="profile_data.entity_types",
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.INVALID,
            reason=("Entity types must be a string or a list of strings."),
            action=("Provide valid entity type names."),
            actual_value=entity_value,
        )
    if not entity_tokens:
        return _finding(
            code="eligibility_context",
            field_path="profile_data.entity_types",
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.INCOMPLETE,
            reason="The entity type list is empty.",
            action=("Remove the empty override or add the applicable entity type."),
            actual_value=entity_value,
        )

    is_aif = bool(
        {
            "alternative_investment_fund",
            "aif",
        }
        & set(entity_tokens)
    )
    if not is_aif:
        return _finding(
            code="eligibility_context",
            field_path="profile_data.entity_types",
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.PRESENT,
            reason="The entity context is usable.",
            action="No action required.",
            actual_value=entity_value,
        )

    registration_value = data.get(
        "regulatory_registrations",
        data.get("regulatory_registration"),
    )
    if registration_value is None:
        return _finding(
            code="eligibility_context",
            field_path=("profile_data.regulatory_registrations"),
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.MISSING,
            reason=("An AIF profile requires regulatory registration data."),
            action=("Add the fund's regulatory registrations, including SEBI when applicable."),
        )

    registration_tokens = _as_tokens(
        registration_value,
    )
    if registration_tokens is None:
        return _finding(
            code="eligibility_context",
            field_path=("profile_data.regulatory_registrations"),
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.INVALID,
            reason=("Regulatory registrations must be a string or a list of strings."),
            action=("Provide valid regulatory registration names."),
            actual_value=registration_value,
        )
    if "sebi" not in registration_tokens:
        return _finding(
            code="eligibility_context",
            field_path=("profile_data.regulatory_registrations"),
            priority=ReadinessPriority.CRITICAL,
            outcome=ReadinessOutcome.INCOMPLETE,
            reason=("The AIF entity context does not include a SEBI registration."),
            action=("Record SEBI registration before evaluating AIF-only schemes."),
            actual_value=registration_value,
        )
    return _finding(
        code="eligibility_context",
        field_path=("profile_data.regulatory_registrations"),
        priority=ReadinessPriority.CRITICAL,
        outcome=ReadinessOutcome.PRESENT,
        reason=("The AIF entity and regulatory context is complete."),
        action="No action required.",
        actual_value=registration_value,
    )


def _check_optional_text(
    profile: Any,
    *,
    code: str,
    field_path: str,
    label: str,
) -> ReadinessFinding:
    value = getattr(profile, field_path, None)
    if not _nonblank(value):
        return _finding(
            code=code,
            field_path=field_path,
            priority=ReadinessPriority.RECOMMENDED,
            outcome=ReadinessOutcome.MISSING,
            reason=f"{label} has not been provided.",
            action=f"Add {label.lower()}.",
            actual_value=value,
        )
    return _finding(
        code=code,
        field_path=field_path,
        priority=ReadinessPriority.RECOMMENDED,
        outcome=ReadinessOutcome.PRESENT,
        reason=f"{label} is present.",
        action="No action required.",
        actual_value=value.strip(),
    )


def _check_description(
    profile: Any,
) -> ReadinessFinding:
    value = getattr(profile, "description", None)
    if not _nonblank(value):
        return _finding(
            code="description",
            field_path="description",
            priority=ReadinessPriority.RECOMMENDED,
            outcome=ReadinessOutcome.MISSING,
            reason=("A startup description has not been provided."),
            action=("Add a concise description of the problem, solution, and customer."),
            actual_value=value,
        )
    length = len(value.strip())
    if length < 50:
        return _finding(
            code="description",
            field_path="description",
            priority=ReadinessPriority.RECOMMENDED,
            outcome=ReadinessOutcome.INCOMPLETE,
            reason=("The startup description is shorter than 50 characters."),
            action=("Expand the description with the problem, solution, and target customer."),
            actual_value=value.strip(),
        )
    return _finding(
        code="description",
        field_path="description",
        priority=ReadinessPriority.RECOMMENDED,
        outcome=ReadinessOutcome.PRESENT,
        reason="The startup description is sufficiently detailed.",
        action="No action required.",
        actual_value=value.strip(),
    )


def _check_location(profile: Any) -> ReadinessFinding:
    state = getattr(profile, "state", None)
    district = getattr(profile, "district", None)
    actual = {
        "state": state,
        "district": district,
    }
    if not _nonblank(state):
        return _finding(
            code="location",
            field_path="state,district",
            priority=ReadinessPriority.RECOMMENDED,
            outcome=ReadinessOutcome.MISSING,
            reason="The startup state has not been provided.",
            action=("Add the operating or registered state and district."),
            actual_value=actual,
        )
    if not _nonblank(district):
        return _finding(
            code="location",
            field_path="state,district",
            priority=ReadinessPriority.RECOMMENDED,
            outcome=ReadinessOutcome.INCOMPLETE,
            reason=("The state is present but the district is missing."),
            action=("Add the district for more precise regional matching."),
            actual_value=actual,
        )
    return _finding(
        code="location",
        field_path="state,district",
        priority=ReadinessPriority.RECOMMENDED,
        outcome=ReadinessOutcome.PRESENT,
        reason="State and district are present.",
        action="No action required.",
        actual_value=actual,
    )


def _check_sectors(profile: Any) -> ReadinessFinding:
    value = getattr(profile, "sectors", None)
    if value is None or value == []:
        return _finding(
            code="sectors",
            field_path="sectors",
            priority=ReadinessPriority.RECOMMENDED,
            outcome=ReadinessOutcome.MISSING,
            reason="No startup sectors have been provided.",
            action="Add at least one primary sector.",
            actual_value=value,
        )
    if not isinstance(value, list):
        return _finding(
            code="sectors",
            field_path="sectors",
            priority=ReadinessPriority.RECOMMENDED,
            outcome=ReadinessOutcome.INVALID,
            reason="Sectors must be stored as a list.",
            action=("Replace the value with a list of sector names."),
            actual_value=value,
        )
    normalized = [item.strip() for item in value if _nonblank(item)]
    if len(normalized) != len(value) or not normalized:
        return _finding(
            code="sectors",
            field_path="sectors",
            priority=ReadinessPriority.RECOMMENDED,
            outcome=ReadinessOutcome.INVALID,
            reason=("Every sector must be a non-empty string."),
            action=("Remove empty or non-text sector values."),
            actual_value=value,
        )
    return _finding(
        code="sectors",
        field_path="sectors",
        priority=ReadinessPriority.RECOMMENDED,
        outcome=ReadinessOutcome.PRESENT,
        reason="At least one valid sector is present.",
        action="No action required.",
        actual_value=normalized,
    )


def _check_udyam_registration(
    profile: Any,
) -> ReadinessFinding:
    value = getattr(
        profile,
        "udyam_registered",
        None,
    )
    if value is None:
        return _finding(
            code="udyam_registered",
            field_path="udyam_registered",
            priority=ReadinessPriority.RECOMMENDED,
            outcome=ReadinessOutcome.MISSING,
            reason=("Udyam registration status has not been provided."),
            action=("Record whether the startup has an Udyam registration."),
        )
    if not isinstance(value, bool):
        return _finding(
            code="udyam_registered",
            field_path="udyam_registered",
            priority=ReadinessPriority.RECOMMENDED,
            outcome=ReadinessOutcome.INVALID,
            reason=("Udyam registration status must be true or false."),
            action=("Replace the value with an explicit boolean."),
            actual_value=value,
        )
    return _finding(
        code="udyam_registered",
        field_path="udyam_registered",
        priority=ReadinessPriority.RECOMMENDED,
        outcome=ReadinessOutcome.PRESENT,
        reason=("Udyam registration status is explicitly recorded."),
        action="No action required.",
        actual_value=value,
    )


def _check_business_metrics(
    profile: Any,
) -> ReadinessFinding:
    turnover = getattr(
        profile,
        "annual_turnover",
        None,
    )
    revenue_stage = getattr(
        profile,
        "revenue_stage",
        None,
    )
    team_size = getattr(profile, "team_size", None)
    actual = {
        "annual_turnover": turnover,
        "revenue_stage": revenue_stage,
        "team_size": team_size,
    }

    if turnover is not None:
        try:
            if _decimal(turnover) < 0:
                raise ValueError
        except ValueError:
            return _finding(
                code="business_metrics",
                field_path=("annual_turnover,revenue_stage,team_size"),
                priority=(ReadinessPriority.RECOMMENDED),
                outcome=ReadinessOutcome.INVALID,
                reason=("Annual turnover must be a non-negative number."),
                action="Correct the annual turnover value.",
                actual_value=actual,
            )

    if team_size is not None and (
        not isinstance(team_size, int) or isinstance(team_size, bool) or team_size <= 0
    ):
        return _finding(
            code="business_metrics",
            field_path=("annual_turnover,revenue_stage,team_size"),
            priority=ReadinessPriority.RECOMMENDED,
            outcome=ReadinessOutcome.INVALID,
            reason=("Team size must be a positive whole number."),
            action="Correct the team size value.",
            actual_value=actual,
        )

    provided = (
        turnover is not None,
        _nonblank(revenue_stage),
        team_size is not None,
    )
    count = sum(provided)
    if count == 0:
        return _finding(
            code="business_metrics",
            field_path=("annual_turnover,revenue_stage,team_size"),
            priority=ReadinessPriority.RECOMMENDED,
            outcome=ReadinessOutcome.MISSING,
            reason="No business metrics have been provided.",
            action=("Add turnover, revenue stage, and team size where available."),
            actual_value=actual,
        )
    if count < len(provided):
        return _finding(
            code="business_metrics",
            field_path=("annual_turnover,revenue_stage,team_size"),
            priority=ReadinessPriority.RECOMMENDED,
            outcome=ReadinessOutcome.INCOMPLETE,
            reason="Only some business metrics are present.",
            action=("Complete the missing turnover, revenue stage, or team size values."),
            actual_value=actual,
        )
    return _finding(
        code="business_metrics",
        field_path=("annual_turnover,revenue_stage,team_size"),
        priority=ReadinessPriority.RECOMMENDED,
        outcome=ReadinessOutcome.PRESENT,
        reason="The core business metrics are complete.",
        action="No action required.",
        actual_value=actual,
    )


def _check_funding_plan(
    profile: Any,
) -> ReadinessFinding:
    amount = getattr(
        profile,
        "funding_required",
        None,
    )
    purpose = getattr(
        profile,
        "funding_purpose",
        None,
    )
    actual = {
        "funding_required": amount,
        "funding_purpose": purpose,
    }

    decimal_amount = None
    if amount is not None:
        try:
            decimal_amount = _decimal(amount)
            if decimal_amount < 0:
                raise ValueError
        except ValueError:
            return _finding(
                code="funding_plan",
                field_path=("funding_required,funding_purpose"),
                priority=(ReadinessPriority.RECOMMENDED),
                outcome=ReadinessOutcome.INVALID,
                reason=("Funding required must be a non-negative number."),
                action="Correct the funding amount.",
                actual_value=actual,
            )

    has_purpose = _nonblank(purpose)
    if amount is None and not has_purpose:
        return _finding(
            code="funding_plan",
            field_path=("funding_required,funding_purpose"),
            priority=ReadinessPriority.RECOMMENDED,
            outcome=ReadinessOutcome.MISSING,
            reason="No funding plan has been provided.",
            action=(
                "Add the required amount and its intended use, or record zero funding required."
            ),
            actual_value=actual,
        )
    if decimal_amount == 0:
        return _finding(
            code="funding_plan",
            field_path=("funding_required,funding_purpose"),
            priority=ReadinessPriority.RECOMMENDED,
            outcome=ReadinessOutcome.PRESENT,
            reason=("The profile explicitly records that no funding is required."),
            action="No action required.",
            actual_value=actual,
        )
    if amount is None or not has_purpose:
        return _finding(
            code="funding_plan",
            field_path=("funding_required,funding_purpose"),
            priority=ReadinessPriority.RECOMMENDED,
            outcome=ReadinessOutcome.INCOMPLETE,
            reason=("The funding amount and purpose are not both present."),
            action=("Complete both the funding amount and funding purpose."),
            actual_value=actual,
        )
    return _finding(
        code="funding_plan",
        field_path=("funding_required,funding_purpose"),
        priority=ReadinessPriority.RECOMMENDED,
        outcome=ReadinessOutcome.PRESENT,
        reason="The funding plan is complete.",
        action="No action required.",
        actual_value=actual,
    )


def _category_score(
    findings: tuple[ReadinessFinding, ...],
) -> int:
    if not findings:
        return 100
    earned = sum(_OUTCOME_FACTORS[item.outcome.value] for item in findings)
    score = earned / Decimal(len(findings)) * Decimal("100")
    return int(
        score.quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )


def evaluate_startup_readiness(
    *,
    startup_profile: Any,
    as_of_date: date,
) -> ReadinessEvaluation:
    findings = (
        _check_startup_name(startup_profile),
        _check_stage(startup_profile),
        _check_incorporation_date(
            startup_profile,
            as_of_date=as_of_date,
        ),
        _check_dpiit_recognition(
            startup_profile,
        ),
        _check_eligibility_context(
            startup_profile,
        ),
        _check_optional_text(
            startup_profile,
            code="legal_name",
            field_path="legal_name",
            label="Legal name",
        ),
        _check_description(startup_profile),
        _check_optional_text(
            startup_profile,
            code="incorporation_type",
            field_path="incorporation_type",
            label="Incorporation type",
        ),
        _check_location(startup_profile),
        _check_sectors(startup_profile),
        _check_udyam_registration(
            startup_profile,
        ),
        _check_business_metrics(
            startup_profile,
        ),
        _check_funding_plan(startup_profile),
    )

    critical = tuple(item for item in findings if item.priority == ReadinessPriority.CRITICAL)
    recommended = tuple(item for item in findings if item.priority == ReadinessPriority.RECOMMENDED)
    critical_score = _category_score(critical)
    recommended_score = _category_score(
        recommended,
    )
    score = int(
        (
            Decimal(critical_score) * Decimal("0.70") + Decimal(recommended_score) * Decimal("0.30")
        ).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )

    blocking_count = sum(item.outcome != ReadinessOutcome.PRESENT for item in critical)
    recommended_attention_count = sum(
        item.outcome != ReadinessOutcome.PRESENT for item in recommended
    )

    if blocking_count:
        status = ReadinessStatus.BLOCKED
    elif recommended_attention_count:
        status = ReadinessStatus.READY_WITH_RECOMMENDATIONS
    else:
        status = ReadinessStatus.READY

    summary = (
        f"{blocking_count} critical and "
        f"{recommended_attention_count} recommended "
        "readiness findings require attention."
    )

    return ReadinessEvaluation(
        status=status,
        score=score,
        critical_score=critical_score,
        recommended_score=recommended_score,
        findings=findings,
        summary=summary,
    )
