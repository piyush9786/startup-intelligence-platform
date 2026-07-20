from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.knowledge.models import (
    CandidatePublication,
    CandidateResolution,
    EligibilityRuleCandidate,
    PublishedEvidence,
    SchemeCandidate,
)
from apps.schemes.models import EligibilityRule, Scheme, SchemeVersion

ALLOWED_PUBLISHER_ROLES = {"reviewer", "admin"}

OPERATOR_MAP = {
    "eq": EligibilityRule.Operator.EQUALS,
    "equals": EligibilityRule.Operator.EQUALS,
    "ne": EligibilityRule.Operator.NOT_EQUALS,
    "neq": EligibilityRule.Operator.NOT_EQUALS,
    "not_eq": EligibilityRule.Operator.NOT_EQUALS,
    "not_equals": EligibilityRule.Operator.NOT_EQUALS,
    "in": EligibilityRule.Operator.IN,
    "not_in": EligibilityRule.Operator.NOT_IN,
    "gt": EligibilityRule.Operator.GREATER_THAN,
    "greater_than": EligibilityRule.Operator.GREATER_THAN,
    "gte": EligibilityRule.Operator.GREATER_OR_EQUAL,
    "greater_or_equal": EligibilityRule.Operator.GREATER_OR_EQUAL,
    "lt": EligibilityRule.Operator.LESS_THAN,
    "less_than": EligibilityRule.Operator.LESS_THAN,
    "lte": EligibilityRule.Operator.LESS_OR_EQUAL,
    "less_or_equal": EligibilityRule.Operator.LESS_OR_EQUAL,
    "between": EligibilityRule.Operator.BETWEEN,
    "contains": EligibilityRule.Operator.CONTAINS_ANY,
    "contains_any": EligibilityRule.Operator.CONTAINS_ANY,
    "contains_all": EligibilityRule.Operator.CONTAINS_ALL,
    "exists": EligibilityRule.Operator.EXISTS,
    "not_exists": EligibilityRule.Operator.NOT_EXISTS,
}


@dataclass(frozen=True)
class PublicationResult:
    publication: CandidatePublication
    scheme: Scheme
    scheme_version: SchemeVersion
    created_scheme: bool
    created_version: bool
    created_publication: bool

    @property
    def status(self) -> str:
        if not self.created_publication:
            return "unchanged"
        if self.publication.role == CandidatePublication.Role.SUPPORTING:
            return "supporting_published"
        if self.created_version:
            return "version_created"
        return "existing_version_published"


def _validate_publisher(publisher: Any) -> None:
    if publisher is None:
        raise ValidationError("A publisher is required.")
    if not getattr(publisher, "is_authenticated", False):
        raise ValidationError("The publisher must be authenticated.")
    if (
        not getattr(publisher, "is_superuser", False)
        and getattr(publisher, "role", None) not in ALLOWED_PUBLISHER_ROLES
    ):
        raise ValidationError("Only reviewers or administrators may publish candidates.")


def _decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _json_ready(value: Any) -> Any:
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, dict):
        return {
            str(key): _json_ready(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value


def _json_key(value: Any) -> str:
    return json.dumps(
        _json_ready(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _normalize_currency(value: str) -> str:
    currency = (value or "INR").strip().upper()
    if len(currency) != 3:
        raise ValidationError("Currency must be a three-letter ISO-style code.")
    return currency


def _normalized_confidence(
    value: Decimal | None,
) -> Decimal | None:
    if value is None:
        return None
    confidence = Decimal(value)
    if confidence > 1:
        confidence /= Decimal("100")
    confidence = min(max(confidence, Decimal("0")), Decimal("1"))
    return confidence.quantize(Decimal("0.0001"))


def _mapped_operator(value: str) -> str:
    normalized = (value or "").strip().casefold()
    try:
        return OPERATOR_MAP[normalized]
    except KeyError as exc:
        raise ValidationError(f"Unsupported eligibility operator: {value!r}.") from exc


def _approved_rule_rows(
    candidate: SchemeCandidate,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rules = candidate.eligibility_rules.filter(
        review_status=EligibilityRuleCandidate.ReviewStatus.APPROVED,
    ).select_related("source_chunk")

    for rule in rules:
        rows.append(
            {
                "field_path": rule.field_name.strip(),
                "operator": _mapped_operator(rule.operator),
                "expected_value": _json_ready(rule.value),
                "unit": rule.unit.strip(),
                "human_text": rule.human_text.strip(),
                "evidence_page": (
                    rule.source_chunk.page_number if rule.source_chunk_id is not None else None
                ),
                "confidence": _normalized_confidence(rule.confidence),
            }
        )

    rows.sort(
        key=lambda row: (
            row["field_path"],
            row["operator"],
            _json_key(row["expected_value"]),
            row["human_text"],
        )
    )
    return rows


def _flatten_rule_values(
    rows: list[dict[str, Any]],
    field_names: set[str],
) -> list[Any]:
    values: list[Any] = []
    for row in rows:
        if row["field_path"] not in field_names:
            continue
        value = row["expected_value"]
        values.extend(value if isinstance(value, list) else [value])

    unique = {_json_key(value): value for value in values}
    return [unique[key] for key in sorted(unique)]


def _benefit_rows(candidate: SchemeCandidate) -> list[dict[str, Any]]:
    rows = [
        {
            "type": item.benefit_type.strip(),
            "description": item.description.strip(),
            "amount_min": _decimal_text(item.amount_min),
            "amount_max": _decimal_text(item.amount_max),
            "currency": _normalize_currency(item.currency),
        }
        for item in candidate.benefit_items.all()
    ]

    if not rows and candidate.benefits_text.strip():
        rows.append(
            {
                "type": candidate.kind.strip(),
                "description": candidate.benefits_text.strip(),
                "amount_min": _decimal_text(candidate.financial_amount_min),
                "amount_max": _decimal_text(candidate.financial_amount_max),
                "currency": _normalize_currency(candidate.currency),
            }
        )

    rows.sort(key=_json_key)
    return rows


def _required_document_rows(
    candidate: SchemeCandidate,
) -> list[dict[str, Any]]:
    rows = [
        {
            "name": item.name.strip(),
            "description": item.description.strip(),
            "mandatory": item.mandatory,
        }
        for item in candidate.required_document_items.all()
    ]
    rows.sort(key=_json_key)
    return rows


def _application_step_rows(
    candidate: SchemeCandidate,
) -> list[dict[str, Any]]:
    rows = [
        {
            "step_number": item.step_number,
            "instruction": item.instruction.strip(),
            "url": item.url.strip(),
        }
        for item in candidate.application_steps.all().order_by(
            "step_number",
            "id",
        )
    ]

    if not rows and candidate.application_text.strip():
        rows.append(
            {
                "step_number": 1,
                "instruction": candidate.application_text.strip(),
                "url": candidate.application_url.strip(),
            }
        )
    return rows


def build_publication_payload(
    candidate: SchemeCandidate,
) -> dict[str, Any]:
    rule_rows = _approved_rule_rows(candidate)
    benefits = _benefit_rows(candidate)
    kind = candidate.kind.strip()
    if kind == SchemeCandidate.Kind.UNKNOWN:
        kind = ""

    support_types = sorted(
        {
            value
            for value in [
                kind,
                *[row["type"] for row in benefits],
            ]
            if value
        }
    )

    return _json_ready(
        {
            "description": candidate.summary.strip(),
            "objective": candidate.objective_text.strip(),
            "support_types": support_types,
            "categories": [kind] if kind else [],
            "eligible_sectors": _flatten_rule_values(
                rule_rows,
                {"eligible_sector", "eligible_sectors"},
            ),
            "eligible_stages": _flatten_rule_values(
                rule_rows,
                {"eligible_startup_stage", "eligible_stage"},
            ),
            "eligible_states": _flatten_rule_values(
                rule_rows,
                {"eligible_state", "eligible_states"},
            ),
            "founder_categories": _flatten_rule_values(
                rule_rows,
                {"founder_category", "founder_categories"},
            ),
            "minimum_amount": _decimal_text(candidate.financial_amount_min),
            "maximum_amount": _decimal_text(candidate.financial_amount_max),
            "currency": _normalize_currency(candidate.currency),
            "application_status": SchemeVersion.ApplicationStatus.UNKNOWN,
            "official_url": candidate.official_url.strip(),
            "application_url": candidate.application_url.strip(),
            "required_documents": _required_document_rows(candidate),
            "application_steps": _application_step_rows(candidate),
            "benefits": benefits,
            "restrictions": (
                [candidate.eligibility_text.strip()] if candidate.eligibility_text.strip() else []
            ),
            "eligibility_rules": [
                {
                    "field_path": row["field_path"],
                    "operator": row["operator"],
                    "expected_value": row["expected_value"],
                    "unit": row["unit"],
                    "human_text": row["human_text"],
                }
                for row in rule_rows
            ],
        }
    )


def publication_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        _json_ready(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _locked_candidate(
    candidate: SchemeCandidate,
) -> SchemeCandidate:
    return (
        SchemeCandidate.objects.select_for_update(of=("self",))
        .select_related(
            "run__extraction__source_document",
        )
        .prefetch_related(
            "evidence",
            "benefit_items",
            "required_document_items",
            "application_steps",
            "eligibility_rules__source_chunk",
        )
        .get(pk=candidate.pk)
    )


def _validate_candidate(
    candidate: SchemeCandidate,
) -> CandidateResolution:
    if candidate.review_status != SchemeCandidate.ReviewStatus.APPROVED:
        raise ValidationError("Only approved candidates may be published.")

    try:
        resolution = candidate.resolution
    except CandidateResolution.DoesNotExist as exc:
        raise ValidationError("The candidate requires a completed resolution.") from exc

    if resolution.classification not in {
        CandidateResolution.Classification.CANONICAL,
        CandidateResolution.Classification.SUPPORTING,
    }:
        raise ValidationError("Only canonical or supporting resolutions may be published.")

    if (
        resolution.resolved_authority_id is None
        or not resolution.canonical_title.strip()
        or resolution.resolved_by_id is None
        or resolution.resolved_at is None
    ):
        raise ValidationError("The candidate resolution is incomplete.")

    if not candidate.official_url.strip():
        raise ValidationError("A canonical publication requires an official URL.")

    if not candidate.evidence.exists():
        raise ValidationError("A candidate must have evidence before publication.")

    return resolution


def _update_aliases(scheme: Scheme, title: str) -> None:
    title = title.strip()
    if not title:
        return

    known = {
        scheme.canonical_name.casefold(),
        *[str(value).casefold() for value in scheme.alternative_names],
    }
    if title.casefold() not in known:
        scheme.alternative_names = [
            *scheme.alternative_names,
            title,
        ]


def _snapshot_evidence(
    publication: CandidatePublication,
    candidate: SchemeCandidate,
) -> None:
    PublishedEvidence.objects.bulk_create(
        [
            PublishedEvidence(
                publication=publication,
                candidate_evidence=evidence,
                evidence_type=evidence.evidence_type,
                quote=evidence.quote,
                page_number=evidence.page_number,
            )
            for evidence in candidate.evidence.all()
        ]
    )


def _create_rules(
    version: SchemeVersion,
    candidate: SchemeCandidate,
) -> None:
    EligibilityRule.objects.bulk_create(
        [
            EligibilityRule(
                scheme_version=version,
                field_path=row["field_path"],
                operator=row["operator"],
                expected_value=row["expected_value"],
                mandatory=True,
                rule_group="all",
                evidence_text=row["human_text"],
                evidence_page=row["evidence_page"],
                extraction_confidence=row["confidence"],
                manually_verified=True,
            )
            for row in _approved_rule_rows(candidate)
        ]
    )


def _publish_supporting(
    *,
    candidate: SchemeCandidate,
    resolution: CandidateResolution,
    publisher: Any,
) -> PublicationResult:
    if resolution.primary_candidate_id is None:
        raise ValidationError("A supporting candidate requires a primary candidate.")

    try:
        primary = (
            CandidatePublication.objects.select_for_update()
            .select_related("scheme", "scheme_version")
            .get(
                candidate_id=resolution.primary_candidate_id,
                role=CandidatePublication.Role.PRIMARY,
            )
        )
    except CandidatePublication.DoesNotExist as exc:
        raise ValidationError("The primary candidate must be published first.") from exc

    if (
        primary.scheme.authority_id != resolution.resolved_authority_id
        or primary.scheme.canonical_name.casefold() != resolution.canonical_title.strip().casefold()
    ):
        raise ValidationError(
            "The supporting resolution must match the primary publication's scheme and authority."
        )

    publication = CandidatePublication(
        candidate=candidate,
        scheme=primary.scheme,
        scheme_version=primary.scheme_version,
        role=CandidatePublication.Role.SUPPORTING,
        publication_hash=primary.scheme_version.content_hash,
        published_by=publisher,
        published_at=timezone.now(),
    )
    publication.full_clean()
    publication.save()
    _snapshot_evidence(publication, candidate)

    candidate.review_status = SchemeCandidate.ReviewStatus.PUBLISHED
    candidate.save(update_fields=["review_status", "updated_at"])

    return PublicationResult(
        publication=publication,
        scheme=primary.scheme,
        scheme_version=primary.scheme_version,
        created_scheme=False,
        created_version=False,
        created_publication=True,
    )


def _publish_canonical(
    *,
    candidate: SchemeCandidate,
    resolution: CandidateResolution,
    publisher: Any,
) -> PublicationResult:
    if candidate.eligibility_rules.filter(
        review_status=EligibilityRuleCandidate.ReviewStatus.DRAFT,
    ).exists():
        raise ValidationError(
            "All extracted eligibility rules must be approved or "
            "rejected before canonical publication."
        )

    title = resolution.canonical_title.strip()
    authority = resolution.resolved_authority

    scheme = (
        Scheme.objects.select_for_update().filter(canonical_name=title, authority=authority).first()
    )
    created_scheme = scheme is None

    if scheme is None:
        scheme = Scheme.objects.create(
            canonical_name=title,
            authority=authority,
            lifecycle_status=Scheme.LifecycleStatus.DRAFT,
        )
        scheme = Scheme.objects.select_for_update().get(pk=scheme.pk)

    _update_aliases(scheme, candidate.title)

    payload = build_publication_payload(candidate)
    content_hash = publication_hash(payload)
    version = scheme.versions.select_for_update().filter(content_hash=content_hash).first()

    if version is not None and scheme.current_version_id not in {None, version.id}:
        raise ValidationError(
            "The payload matches a non-current historical version. "
            "Manual review is required before publishing a reversion."
        )

    if (
        version is not None
        and CandidatePublication.objects.filter(
            scheme_version=version,
            role=CandidatePublication.Role.PRIMARY,
        ).exists()
    ):
        raise ValidationError(
            "This version already has a primary publication. "
            "Resolve the new candidate as supporting evidence."
        )

    created_version = version is None
    now = timezone.now()

    if version is None:
        latest = scheme.versions.aggregate(maximum=Max("version_number"))["maximum"] or 0
        source_document = candidate.run.extraction.source_document

        version = SchemeVersion.objects.create(
            scheme=scheme,
            version_number=latest + 1,
            source_document=source_document,
            captured_at=source_document.retrieved_at,
            content_hash=content_hash,
            description=payload["description"],
            objective=payload["objective"],
            support_types=payload["support_types"],
            categories=payload["categories"],
            eligible_sectors=payload["eligible_sectors"],
            eligible_stages=payload["eligible_stages"],
            eligible_states=payload["eligible_states"],
            founder_categories=payload["founder_categories"],
            minimum_amount=candidate.financial_amount_min,
            maximum_amount=candidate.financial_amount_max,
            currency=payload["currency"],
            application_status=payload["application_status"],
            official_url=payload["official_url"],
            application_url=payload["application_url"],
            required_documents=payload["required_documents"],
            application_steps=payload["application_steps"],
            benefits=payload["benefits"],
            restrictions=payload["restrictions"],
            verification_status=SchemeVersion.VerificationStatus.VERIFIED,
            extraction_confidence=_normalized_confidence(candidate.confidence),
            verified_at=now,
            verified_by=publisher,
        )
        _create_rules(version, candidate)

    scheme.lifecycle_status = Scheme.LifecycleStatus.ACTIVE
    scheme.current_version = version
    scheme.save(
        update_fields=[
            "alternative_names",
            "lifecycle_status",
            "current_version",
            "updated_at",
        ]
    )

    publication = CandidatePublication(
        candidate=candidate,
        scheme=scheme,
        scheme_version=version,
        role=CandidatePublication.Role.PRIMARY,
        publication_hash=content_hash,
        published_by=publisher,
        published_at=now,
    )
    publication.full_clean()
    publication.save()
    _snapshot_evidence(publication, candidate)

    candidate.review_status = SchemeCandidate.ReviewStatus.PUBLISHED
    candidate.save(update_fields=["review_status", "updated_at"])

    return PublicationResult(
        publication=publication,
        scheme=scheme,
        scheme_version=version,
        created_scheme=created_scheme,
        created_version=created_version,
        created_publication=True,
    )


@transaction.atomic
def publish_candidate(
    *,
    candidate: SchemeCandidate,
    publisher: Any,
) -> PublicationResult:
    _validate_publisher(publisher)
    candidate = _locked_candidate(candidate)

    existing = (
        CandidatePublication.objects.select_for_update()
        .select_related("scheme", "scheme_version")
        .filter(candidate=candidate)
        .first()
    )
    if existing is not None:
        return PublicationResult(
            publication=existing,
            scheme=existing.scheme,
            scheme_version=existing.scheme_version,
            created_scheme=False,
            created_version=False,
            created_publication=False,
        )

    if candidate.review_status == SchemeCandidate.ReviewStatus.PUBLISHED:
        raise ValidationError("Published candidate is missing its publication audit record.")

    resolution = _validate_candidate(candidate)

    if resolution.classification == CandidateResolution.Classification.SUPPORTING:
        return _publish_supporting(
            candidate=candidate,
            resolution=resolution,
            publisher=publisher,
        )

    return _publish_canonical(
        candidate=candidate,
        resolution=resolution,
        publisher=publisher,
    )
