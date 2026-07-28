from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.knowledge.models import (
    ExternalCapitalSupportRecord,
    ExternalCertificationRequirementRecord,
    ExternalKnowledgeDataset,
    ExternalSchemeRecord,
)

CAPITAL_FORMAT = "normalized-external-capital-support-v1"
CERTIFICATION_FORMAT = (
    "normalized-external-certification-requirements-v1"
)

SPECS = {
    CAPITAL_FORMAT: {
        "kind": ExternalKnowledgeDataset.DatasetKind.CAPITAL_SUPPORT,
        "model": ExternalCapitalSupportRecord,
        "name_field": "support_name",
        "text_fields": (
            "support_name",
            "support_type",
            "scheme_name",
            "normalized_name",
            "ministry",
            "implementing_agency",
            "funding_category",
            "raw_minimum_amount",
            "raw_maximum_amount",
            "currency",
            "interest_rate_text",
            "collateral_required_text",
            "repayment_required_text",
            "eligible_entity",
            "state",
            "funding_purpose",
            "claimed_scheme_status",
            "remarks",
        ),
        "list_fields": (
            "startup_stage",
            "industry",
            "matched_external_scheme_ids",
            "quality_warnings",
        ),
        "decimal_fields": (
            "minimum_amount",
            "maximum_amount",
            "source_ai_recommendation_weight",
        ),
        "integer_fields": ("source_priority_score",),
        "boolean_fields": (),
    },
    CERTIFICATION_FORMAT: {
        "kind": (
            ExternalKnowledgeDataset.DatasetKind.CERTIFICATION_REQUIREMENT
        ),
        "model": ExternalCertificationRequirementRecord,
        "name_field": "certificate_name",
        "text_fields": (
            "certificate_name",
            "normalized_name",
            "certificate_type",
            "description",
            "requirement_level",
            "eligibility",
            "benefits",
            "validity",
            "renewal_period",
            "issuing_authority",
            "official_document_text",
            "official_apply_url",
        ),
        "list_fields": (
            "industry",
            "startup_stage",
            "quality_warnings",
        ),
        "decimal_fields": (),
        "integer_fields": ("source_priority_score",),
        "boolean_fields": ("display_eligible",),
    },
}

REVIEW_STATUSES = {
    "needs_review",
    "verified",
    "rejected",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CommandError(message)


def canonical_content_sha256(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        {
            key: value
            for key, value in payload.items()
            if key != "content_sha256"
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def record_content_sha256(record: dict[str, Any]) -> str:
    canonical = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _text(record: dict[str, Any], field_name: str) -> str:
    value = record.get(field_name)
    return "" if value is None else str(value).strip()


def _decimal(
    record: dict[str, Any],
    field_name: str,
    index: int,
) -> Decimal | None:
    value = record.get(field_name)
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise CommandError(
            f"Record {index} field {field_name} must be decimal-compatible."
        ) from exc


def _integer(
    record: dict[str, Any],
    field_name: str,
    index: int,
) -> int | None:
    value = record.get(field_name)
    if value is None or value == "":
        return None
    _require(
        isinstance(value, int) and not isinstance(value, bool),
        f"Record {index} field {field_name} must be an integer or null.",
    )
    return value


def _record_defaults(
    record: dict[str, Any],
    spec: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    defaults = {
        field_name: _text(record, field_name)
        for field_name in spec["text_fields"]
    }
    defaults.update(
        {
            field_name: record.get(field_name, [])
            for field_name in spec["list_fields"]
        }
    )
    defaults.update(
        {
            field_name: _decimal(record, field_name, index)
            for field_name in spec["decimal_fields"]
        }
    )
    defaults.update(
        {
            field_name: _integer(record, field_name, index)
            for field_name in spec["integer_fields"]
        }
    )
    defaults.update(
        {
            field_name: record[field_name]
            for field_name in spec["boolean_fields"]
        }
    )
    defaults.update(
        {
            "source_row_number": record.get("source_row_number"),
            "raw_row": record.get("raw_row", {}),
            "record_sha256": record_content_sha256(record),
        }
    )
    return defaults


def _validate_record(
    record: Any,
    *,
    index: int,
    spec: dict[str, Any],
    seen_ids: set[str],
) -> None:
    _require(
        isinstance(record, dict),
        f"Dataset record {index} must be an object.",
    )

    for field_name in (
        "external_id",
        "normalized_name",
        spec["name_field"],
    ):
        value = record.get(field_name)
        _require(
            isinstance(value, str) and value.strip(),
            f"Dataset record {index} requires {field_name}.",
        )

    external_id = record["external_id"].strip()
    _require(
        external_id not in seen_ids,
        f"Duplicate external_id in dataset: {external_id}",
    )
    seen_ids.add(external_id)

    _require(
        record.get("review_status") in REVIEW_STATUSES,
        f"Dataset record {index} has an unsupported review_status.",
    )

    for field_name in spec["list_fields"]:
        _require(
            isinstance(record.get(field_name, []), list),
            f"Dataset record {index} field {field_name} must be a list.",
        )

    for field_name in spec["boolean_fields"]:
        _require(
            isinstance(record.get(field_name), bool),
            f"Dataset record {index} field {field_name} must be a boolean.",
        )

    source_row_number = record.get("source_row_number")
    _require(
        source_row_number is None
        or (
            isinstance(source_row_number, int)
            and not isinstance(source_row_number, bool)
            and source_row_number > 0
        ),
        (
            f"Dataset record {index} source_row_number must be "
            "a positive integer or null."
        ),
    )
    _require(
        isinstance(record.get("raw_row", {}), dict),
        f"Dataset record {index} field raw_row must be an object.",
    )

    for field_name in spec["decimal_fields"]:
        _decimal(record, field_name, index)
    for field_name in spec["integer_fields"]:
        _integer(record, field_name, index)

    if "display_eligible" in spec["boolean_fields"]:
        _require(
            record["review_status"] != "rejected"
            or record["display_eligible"] is False,
            (
                f"Dataset record {index} cannot be rejected "
                "and display eligible."
            ),
        )


def read_dataset(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CommandError(f"Could not read dataset: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CommandError(f"Dataset is not valid JSON: {exc}") from exc

    _require(
        isinstance(payload, dict),
        "External knowledge dataset root must be an object.",
    )

    for field_name in (
        "dataset_key",
        "dataset_name",
        "source_filename",
        "normalization_version",
        "content_sha256",
    ):
        value = payload.get(field_name)
        _require(
            isinstance(value, str) and value.strip(),
            f"Dataset requires {field_name}.",
        )

    metadata = payload.get("metadata")
    _require(
        isinstance(metadata, dict),
        "Dataset metadata must be an object.",
    )
    import_format = metadata.get("import_format")
    _require(
        import_format in SPECS,
        "Dataset metadata contains an unsupported import_format.",
    )

    records = payload.get("records")
    _require(isinstance(records, list), "Dataset records must be a list.")
    _require(
        payload.get("record_count") == len(records),
        "Dataset record_count does not match the records list.",
    )
    _require(
        canonical_content_sha256(payload) == payload["content_sha256"],
        "Dataset canonical content hash does not match content_sha256.",
    )

    spec = SPECS[import_format]
    seen_ids: set[str] = set()
    for index, record in enumerate(records, start=1):
        _validate_record(
            record,
            index=index,
            spec=spec,
            seen_ids=seen_ids,
        )
    return payload


def _dataset_defaults(payload: dict[str, Any]) -> dict[str, Any]:
    import_format = payload["metadata"]["import_format"]
    return {
        "dataset_kind": SPECS[import_format]["kind"],
        "dataset_name": payload["dataset_name"].strip(),
        "source_filename": payload["source_filename"].strip(),
        "source_sheet": _text(payload, "source_sheet"),
        "source_row_count": int(payload.get("source_row_count") or 0),
        "record_count": len(payload["records"]),
        "normalization_version": payload["normalization_version"].strip(),
        "content_sha256": payload["content_sha256"],
        "is_active": True,
        "metadata": payload["metadata"],
    }


def _update_imported_fields(
    instance: Any,
    defaults: dict[str, Any],
) -> bool:
    changed_fields = []
    for field_name, value in defaults.items():
        if getattr(instance, field_name) == value:
            continue
        setattr(instance, field_name, value)
        changed_fields.append(field_name)

    if not changed_fields:
        return False

    instance.save(
        update_fields=[*changed_fields, "updated_at"],
    )
    return True


def _sync_scheme_matches(
    instance: ExternalCapitalSupportRecord,
    external_ids: list[Any],
) -> None:
    clean_ids = {
        str(external_id).strip()
        for external_id in external_ids
        if str(external_id).strip()
    }
    matches = ExternalSchemeRecord.objects.filter(
        external_id__in=clean_ids,
        dataset__is_active=True,
    )
    instance.matched_external_schemes.set(matches)


@transaction.atomic
def import_external_knowledge_dataset(
    payload: dict[str, Any],
) -> dict[str, Any]:
    import_format = payload["metadata"]["import_format"]
    spec = SPECS[import_format]
    model = spec["model"]

    dataset, dataset_created = (
        ExternalKnowledgeDataset.objects.update_or_create(
            dataset_key=payload["dataset_key"].strip(),
            defaults=_dataset_defaults(payload),
        )
    )

    counts = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
    }
    imported_ids = []

    for index, record in enumerate(payload["records"], start=1):
        external_id = record["external_id"].strip()
        imported_ids.append(external_id)
        defaults = _record_defaults(record, spec, index)

        instance, created = model.objects.get_or_create(
            dataset=dataset,
            external_id=external_id,
            defaults={
                **defaults,
                "review_status": record["review_status"],
            },
        )

        if created:
            counts["created"] += 1
        elif instance.record_sha256 == defaults["record_sha256"]:
            counts["unchanged"] += 1
        else:
            _update_imported_fields(instance, defaults)
            counts["updated"] += 1

        if import_format == CAPITAL_FORMAT:
            _sync_scheme_matches(
                instance,
                record.get("matched_external_scheme_ids", []),
            )

    stale = model.objects.filter(dataset=dataset).exclude(
        external_id__in=imported_ids,
    )
    removed = stale.count()
    stale.delete()

    return {
        "dataset": dataset,
        "dataset_created": dataset_created,
        **counts,
        "removed": removed,
    }


class Command(BaseCommand):
    help = (
        "Import normalized external capital-support or certification "
        "datasets into non-canonical staging."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "paths",
            nargs="+",
            help="Paths to normalized external knowledge JSON datasets.",
        )

    def handle(self, *args, **options):
        for raw_path in options["paths"]:
            payload = read_dataset(
                Path(raw_path).expanduser().resolve()
            )
            result = import_external_knowledge_dataset(payload)
            dataset = result["dataset"]
            self.stdout.write(
                self.style.SUCCESS(
                    f"Imported {dataset.dataset_key}: "
                    f"{dataset.record_count} records "
                    f"({result['created']} created, "
                    f"{result['updated']} updated, "
                    f"{result['unchanged']} unchanged, "
                    f"{result['removed']} removed)."
                )
            )
