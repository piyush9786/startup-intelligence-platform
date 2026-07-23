from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.knowledge.models import CandidatePublication, VerifiedRuleRevision
from apps.schemes.models import EligibilityRule, Scheme, SchemeVersion

REVISION_FORMAT = "verified-rule-revision-v1"
ALLOWED_REVIEWER_ROLES = {"reviewer", "admin"}
SUPPORTED_EXECUTABLE_FIELDS = frozenset(
    {
        "dpiit_recognized",
        "startup_age_months",
        "eligible_entity_type",
        "regulatory_registration",
    }
)
MANUAL_FIELD_PREFIX = "manual_verification."


@dataclass(frozen=True)
class RuleRevisionRow:
    pilot_key: str
    scheme: Scheme
    source_publication: CandidatePublication
    base_version: SchemeVersion
    rules: tuple[dict[str, Any], ...]
    revised_content_hash: str
    existing_revision: VerifiedRuleRevision | None

    @property
    def executable_count(self) -> int:
        return sum(row["evaluation_mode"] == "executable" for row in self.rules)

    @property
    def manual_count(self) -> int:
        return sum(row["evaluation_mode"] == "manual_verification" for row in self.rules)


@dataclass(frozen=True)
class RuleRevisionPlan:
    manifest_key: str
    manifest_hash: str
    reviewer: Any
    rows: tuple[RuleRevisionRow, ...]


@dataclass(frozen=True)
class RuleRevisionResult:
    pilot_key: str
    status: str
    scheme: Scheme
    base_version: SchemeVersion
    revised_version: SchemeVersion
    rule_count: int
    executable_count: int
    manual_count: int


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _json_ready(value: Any) -> Any:
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


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        _json_ready(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_reviewer(reviewer: Any) -> None:
    _require(reviewer is not None, "A reviewer is required.")
    _require(
        bool(getattr(reviewer, "is_authenticated", False)),
        "The reviewer must be authenticated.",
    )
    _require(
        bool(getattr(reviewer, "is_active", False)),
        "The reviewer account is inactive.",
    )
    _require(
        bool(getattr(reviewer, "is_superuser", False))
        or getattr(reviewer, "role", None) in ALLOWED_REVIEWER_ROLES,
        "Reviewer or administrator access is required.",
    )


def _normalized_rule(row: Any, *, label: str) -> dict[str, Any]:
    _require(isinstance(row, dict), f"{label} must be an object.")

    rule_key = row.get("rule_key")
    mode = row.get("evaluation_mode")
    field_path = row.get("field_path")
    operator = row.get("operator")
    mandatory = row.get("mandatory", True)
    evidence_text = row.get("evidence_text")
    evidence_page = row.get("evidence_page")
    expected_value = row.get("expected_value")

    _require(
        isinstance(rule_key, str) and rule_key.strip(),
        f"{label} requires rule_key.",
    )
    _require(
        mode in {"executable", "manual_verification"},
        f"{label} has an invalid evaluation_mode.",
    )
    _require(
        isinstance(field_path, str) and field_path.strip(),
        f"{label} requires field_path.",
    )
    _require(
        isinstance(operator, str) and operator in EligibilityRule.Operator.values,
        f"{label} has an unsupported operator.",
    )
    _require(
        isinstance(mandatory, bool),
        f"{label}.mandatory must be a boolean.",
    )
    _require(
        isinstance(evidence_text, str) and evidence_text.strip(),
        f"{label} requires evidence_text.",
    )
    _require(
        evidence_page is None
        or (
            isinstance(evidence_page, int)
            and not isinstance(evidence_page, bool)
            and evidence_page > 0
        ),
        f"{label}.evidence_page must be a positive integer or null.",
    )

    field_path = field_path.strip()
    if mode == "executable":
        _require(
            field_path in SUPPORTED_EXECUTABLE_FIELDS,
            f"{label} executable field is not supported: {field_path!r}.",
        )
    else:
        _require(
            field_path.startswith(MANUAL_FIELD_PREFIX),
            f"{label} manual field must start with {MANUAL_FIELD_PREFIX!r}.",
        )
        _require(
            operator == EligibilityRule.Operator.EXISTS,
            f"{label} manual rules must use the exists operator.",
        )
        _require(
            expected_value is None,
            f"{label} manual rules must use a null expected_value.",
        )

    return {
        "rule_key": rule_key.strip(),
        "evaluation_mode": mode,
        "field_path": field_path,
        "operator": operator,
        "expected_value": _json_ready(expected_value),
        "mandatory": mandatory,
        "rule_group": "all",
        "evidence_text": evidence_text.strip(),
        "evidence_page": evidence_page,
        "extraction_confidence": Decimal("1.0000"),
        "manually_verified": True,
    }


def _normalized_rules(value: Any, *, pilot_key: str) -> tuple[dict[str, Any], ...]:
    _require(
        isinstance(value, list) and value,
        f"Revision {pilot_key} requires at least one rule.",
    )
    rules = tuple(
        _normalized_rule(row, label=f"Revision {pilot_key} rule {index}")
        for index, row in enumerate(value, start=1)
    )

    rule_keys = [row["rule_key"] for row in rules]
    _require(
        len(rule_keys) == len(set(rule_keys)),
        f"Revision {pilot_key} contains duplicate rule_key values.",
    )
    _require(
        any(row["evaluation_mode"] == "executable" for row in rules),
        f"Revision {pilot_key} requires at least one executable rule.",
    )

    persisted_keys = [
        json.dumps(
            _json_ready(
                {
                    key: row[key]
                    for key in (
                        "field_path",
                        "operator",
                        "expected_value",
                        "mandatory",
                        "rule_group",
                        "evidence_text",
                        "evidence_page",
                    )
                }
            ),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        for row in rules
    ]
    _require(
        len(persisted_keys) == len(set(persisted_keys)),
        f"Revision {pilot_key} contains duplicate canonical rules.",
    )

    return tuple(
        sorted(
            rules,
            key=lambda row: (
                row["field_path"],
                row["operator"],
                json.dumps(
                    row["expected_value"],
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                row["rule_key"],
            ),
        )
    )


def _revision_content_hash(
    *,
    base_version: SchemeVersion,
    rules: tuple[dict[str, Any], ...],
) -> str:
    persisted_rules = [
        {
            key: row[key]
            for key in (
                "field_path",
                "operator",
                "expected_value",
                "mandatory",
                "rule_group",
                "evidence_text",
                "evidence_page",
                "extraction_confidence",
                "manually_verified",
            )
        }
        for row in rules
    ]
    return _canonical_hash(
        {
            "revision_format": REVISION_FORMAT,
            "base_content_hash": base_version.content_hash,
            "eligibility_rules": persisted_rules,
        }
    )


def build_verified_rule_revision_plan(
    *,
    manifest: Any,
    reviewer: Any,
) -> RuleRevisionPlan:
    _validate_reviewer(reviewer)
    _require(isinstance(manifest, dict), "Manifest root must be an object.")
    _require(
        manifest.get("schema_version") == 1,
        "Unsupported verified rule manifest schema version.",
    )

    manifest_key = manifest.get("manifest_key")
    revisions = manifest.get("revisions")
    _require(
        isinstance(manifest_key, str) and manifest_key.strip(),
        "Manifest requires manifest_key.",
    )
    _require(
        isinstance(revisions, list) and revisions,
        "Manifest requires at least one revision.",
    )

    manifest_key = manifest_key.strip()
    manifest_hash = _canonical_hash(manifest)
    pilot_keys: set[str] = set()
    scheme_ids: set[str] = set()
    rows: list[RuleRevisionRow] = []

    for index, row in enumerate(revisions, start=1):
        label = f"Revision {index}"
        _require(isinstance(row, dict), f"{label} must be an object.")

        pilot_key = row.get("pilot_key")
        scheme_id = row.get("scheme_id")
        source_publication_id = row.get("source_publication_id")
        expected_version_id = row.get("expected_current_version_id")
        expected_version_number = row.get("expected_current_version_number")
        expected_content_hash = row.get("expected_current_content_hash")

        _require(
            isinstance(pilot_key, str) and pilot_key.strip(),
            f"{label} requires pilot_key.",
        )
        pilot_key = pilot_key.strip()
        _require(pilot_key not in pilot_keys, f"Duplicate pilot_key: {pilot_key}.")
        pilot_keys.add(pilot_key)

        for value, field_name in (
            (scheme_id, "scheme_id"),
            (source_publication_id, "source_publication_id"),
            (expected_version_id, "expected_current_version_id"),
            (expected_content_hash, "expected_current_content_hash"),
        ):
            _require(
                isinstance(value, str) and value.strip(),
                f"{label} requires {field_name}.",
            )

        _require(
            isinstance(expected_version_number, int)
            and not isinstance(expected_version_number, bool)
            and expected_version_number > 0,
            f"{label} requires a positive current version number.",
        )
        _require(
            scheme_id not in scheme_ids,
            f"Manifest contains duplicate scheme_id: {scheme_id}.",
        )
        scheme_ids.add(scheme_id)

        try:
            scheme = Scheme.objects.select_related("current_version").get(pk=scheme_id)
        except Scheme.DoesNotExist as exc:
            raise ValidationError(f"{label} scheme was not found: {scheme_id}.") from exc

        try:
            publication = CandidatePublication.objects.select_related(
                "scheme",
                "scheme_version",
                "candidate",
            ).get(pk=source_publication_id)
        except CandidatePublication.DoesNotExist as exc:
            raise ValidationError(f"{label} source publication was not found.") from exc

        _require(
            publication.role == CandidatePublication.Role.PRIMARY,
            f"{label} source publication must be primary.",
        )
        _require(
            str(publication.scheme_id) == scheme_id,
            f"{label} source publication scheme does not match.",
        )
        _require(
            str(publication.scheme_version_id) == expected_version_id,
            f"{label} source publication version does not match.",
        )

        base_version = publication.scheme_version
        _require(
            base_version.version_number == expected_version_number,
            f"{label} source version number does not match.",
        )
        _require(
            base_version.content_hash == expected_content_hash,
            f"{label} source version content hash does not match.",
        )
        _require(
            base_version.verification_status == SchemeVersion.VerificationStatus.VERIFIED,
            f"{label} base version must be verified.",
        )

        rules = _normalized_rules(row.get("rules"), pilot_key=pilot_key)
        revised_content_hash = _revision_content_hash(
            base_version=base_version,
            rules=rules,
        )

        existing = (
            VerifiedRuleRevision.objects.select_related(
                "scheme",
                "source_publication",
                "base_version",
                "revised_version",
            )
            .filter(manifest_key=manifest_key, pilot_key=pilot_key)
            .first()
        )

        if existing is not None:
            _require(
                existing.manifest_hash == manifest_hash,
                f"{label} was already applied with different manifest content.",
            )
            _require(
                str(existing.scheme_id) == scheme_id,
                f"{label} existing revision scheme does not match.",
            )
            _require(
                str(existing.source_publication_id) == source_publication_id,
                f"{label} existing source publication does not match.",
            )
            _require(
                str(existing.base_version_id) == expected_version_id,
                f"{label} existing base version does not match.",
            )
            _require(
                existing.revised_version.content_hash == revised_content_hash,
                f"{label} existing revised content hash does not match.",
            )
        else:
            _require(
                str(scheme.current_version_id) == expected_version_id,
                f"{label} current scheme version does not match the manifest.",
            )
            _require(
                scheme.current_version.version_number == expected_version_number,
                f"{label} current scheme version number does not match.",
            )
            _require(
                scheme.current_version.content_hash == expected_content_hash,
                f"{label} current scheme content hash does not match.",
            )

        rows.append(
            RuleRevisionRow(
                pilot_key=pilot_key,
                scheme=scheme,
                source_publication=publication,
                base_version=base_version,
                rules=rules,
                revised_content_hash=revised_content_hash,
                existing_revision=existing,
            )
        )

    return RuleRevisionPlan(
        manifest_key=manifest_key,
        manifest_hash=manifest_hash,
        reviewer=reviewer,
        rows=tuple(rows),
    )


def _clone_version(
    *,
    scheme: Scheme,
    base_version: SchemeVersion,
    version_number: int,
    content_hash: str,
    reviewer: Any,
    reviewed_at: datetime,
) -> SchemeVersion:
    return SchemeVersion.objects.create(
        scheme=scheme,
        version_number=version_number,
        source_document=base_version.source_document,
        valid_from=base_version.valid_from,
        valid_to=base_version.valid_to,
        captured_at=reviewed_at,
        content_hash=content_hash,
        description=base_version.description,
        objective=base_version.objective,
        support_types=copy.deepcopy(base_version.support_types),
        categories=copy.deepcopy(base_version.categories),
        eligible_sectors=copy.deepcopy(base_version.eligible_sectors),
        eligible_stages=copy.deepcopy(base_version.eligible_stages),
        eligible_states=copy.deepcopy(base_version.eligible_states),
        founder_categories=copy.deepcopy(base_version.founder_categories),
        minimum_amount=base_version.minimum_amount,
        maximum_amount=base_version.maximum_amount,
        currency=base_version.currency,
        equity_required=base_version.equity_required,
        interest_rate_min=base_version.interest_rate_min,
        interest_rate_max=base_version.interest_rate_max,
        application_status=base_version.application_status,
        opening_date=base_version.opening_date,
        deadline=base_version.deadline,
        official_url=base_version.official_url,
        application_url=base_version.application_url,
        required_documents=copy.deepcopy(base_version.required_documents),
        application_steps=copy.deepcopy(base_version.application_steps),
        benefits=copy.deepcopy(base_version.benefits),
        restrictions=copy.deepcopy(base_version.restrictions),
        verification_status=SchemeVersion.VerificationStatus.VERIFIED,
        extraction_confidence=base_version.extraction_confidence,
        verified_at=reviewed_at,
        verified_by=reviewer,
    )


@transaction.atomic
def apply_verified_rule_revision_plan(
    plan: RuleRevisionPlan,
) -> tuple[RuleRevisionResult, ...]:
    scheme_ids = [row.scheme.id for row in plan.rows]
    locked_schemes = {
        str(scheme.id): scheme
        for scheme in (
            Scheme.objects.select_for_update(of=("self",))
            .select_related("current_version")
            .filter(id__in=scheme_ids)
            .order_by("id")
        )
    }
    results: list[RuleRevisionResult] = []

    for row in plan.rows:
        existing = (
            VerifiedRuleRevision.objects.select_for_update()
            .select_related("scheme", "base_version", "revised_version")
            .filter(manifest_key=plan.manifest_key, pilot_key=row.pilot_key)
            .first()
        )
        if existing is not None:
            if existing.manifest_hash != plan.manifest_hash:
                raise ValidationError(f"{row.pilot_key} has a conflicting applied manifest.")
            results.append(
                RuleRevisionResult(
                    pilot_key=row.pilot_key,
                    status="unchanged",
                    scheme=existing.scheme,
                    base_version=existing.base_version,
                    revised_version=existing.revised_version,
                    rule_count=len(row.rules),
                    executable_count=row.executable_count,
                    manual_count=row.manual_count,
                )
            )
            continue

        scheme = locked_schemes[str(row.scheme.id)]
        if scheme.current_version_id != row.base_version.id:
            raise ValidationError(f"{row.pilot_key} current version changed after validation.")

        base_version = SchemeVersion.objects.select_for_update().get(pk=row.base_version.id)
        if base_version.content_hash != row.base_version.content_hash:
            raise ValidationError(f"{row.pilot_key} base version changed after validation.")

        if scheme.versions.filter(content_hash=row.revised_content_hash).exists():
            raise ValidationError(
                f"{row.pilot_key} revised content already exists without its audit record."
            )

        latest_number = scheme.versions.aggregate(maximum=Max("version_number"))["maximum"] or 0
        reviewed_at = timezone.now()
        revised_version = _clone_version(
            scheme=scheme,
            base_version=base_version,
            version_number=latest_number + 1,
            content_hash=row.revised_content_hash,
            reviewer=plan.reviewer,
            reviewed_at=reviewed_at,
        )

        EligibilityRule.objects.bulk_create(
            [
                EligibilityRule(
                    scheme_version=revised_version,
                    field_path=rule["field_path"],
                    operator=rule["operator"],
                    expected_value=rule["expected_value"],
                    mandatory=rule["mandatory"],
                    rule_group=rule["rule_group"],
                    evidence_text=rule["evidence_text"],
                    evidence_page=rule["evidence_page"],
                    extraction_confidence=rule["extraction_confidence"],
                    manually_verified=rule["manually_verified"],
                )
                for rule in row.rules
            ]
        )

        scheme.current_version = revised_version
        scheme.save(update_fields=["current_version", "updated_at"])

        audit = VerifiedRuleRevision(
            manifest_key=plan.manifest_key,
            pilot_key=row.pilot_key,
            source_publication=row.source_publication,
            scheme=scheme,
            base_version=base_version,
            revised_version=revised_version,
            reviewed_by=plan.reviewer,
            reviewed_at=reviewed_at,
            manifest_hash=plan.manifest_hash,
            metadata={
                "revision_format": REVISION_FORMAT,
                "rule_keys": [rule["rule_key"] for rule in row.rules],
                "executable_rule_count": row.executable_count,
                "manual_rule_count": row.manual_count,
            },
        )
        audit.full_clean()
        audit.save()

        results.append(
            RuleRevisionResult(
                pilot_key=row.pilot_key,
                status="version_created",
                scheme=scheme,
                base_version=base_version,
                revised_version=revised_version,
                rule_count=len(row.rules),
                executable_count=row.executable_count,
                manual_count=row.manual_count,
            )
        )

    return tuple(results)
