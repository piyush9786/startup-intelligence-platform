from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.knowledge.models import (
    ExternalSchemeDataset,
    ExternalSchemeRecord,
)

DEFAULT_DATASET_PATH = (
    Path(settings.BASE_DIR)
    / "apps"
    / "knowledge"
    / "datasets"
    / "external"
    / "startup_schemes_v1.json"
)

TEXT_FIELDS = (
    "scheme_name",
    "normalized_name",
    "ministry",
    "department",
    "sector",
    "startup_type",
    "central_state",
    "state",
    "funding_type",
    "funding_amount",
    "financial_instrument",
    "eligibility",
    "women_eligible",
    "sc_st_eligible",
    "dpiit_required",
    "startup_age_limit",
    "revenue_criteria",
    "tax_benefits",
    "application_process",
    "official_website_label",
    "official_application_url",
    "source_portal",
    "claimed_last_updated",
)

LIST_FIELDS = (
    "startup_stage",
    "industry",
    "documents_required",
    "quality_warnings",
    "source_rows",
    "external_ids",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CommandError(message)


def canonical_content_sha256(payload: dict[str, Any]) -> str:
    hash_payload = {
        key: value
        for key, value in payload.items()
        if key != "content_sha256"
    }

    canonical = json.dumps(
        hash_payload,
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


def _read_dataset(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CommandError(
            f"Could not read external scheme dataset: {path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise CommandError(
            f"External scheme dataset is not valid JSON: {exc}"
        ) from exc

    _require(
        isinstance(payload, dict),
        "External scheme dataset root must be an object.",
    )

    required_text_fields = (
        "dataset_key",
        "dataset_name",
        "source_filename",
        "normalization_version",
        "content_sha256",
    )

    for field_name in required_text_fields:
        value = payload.get(field_name)
        _require(
            isinstance(value, str) and value.strip(),
            f"Dataset requires {field_name}.",
        )

    records = payload.get("records")

    _require(
        isinstance(records, list),
        "Dataset records must be a list.",
    )
    _require(
        payload.get("record_count") == len(records),
        "Dataset record_count does not match the records list.",
    )

    actual_hash = canonical_content_sha256(payload)

    _require(
        actual_hash == payload["content_sha256"],
        "Dataset canonical content hash does not match content_sha256.",
    )

    seen_external_ids: set[str] = set()

    for index, record in enumerate(records, start=1):
        _validate_record(
            record,
            index=index,
            seen_external_ids=seen_external_ids,
        )

    return payload


def _validate_record(
    record: Any,
    *,
    index: int,
    seen_external_ids: set[str],
) -> None:
    _require(
        isinstance(record, dict),
        f"Dataset record {index} must be an object.",
    )

    for field_name in (
        "external_id",
        "scheme_name",
        "normalized_name",
    ):
        value = record.get(field_name)
        _require(
            isinstance(value, str) and value.strip(),
            f"Dataset record {index} requires {field_name}.",
        )

    external_id = record["external_id"].strip()

    _require(
        external_id not in seen_external_ids,
        f"Duplicate external_id in dataset: {external_id}",
    )
    seen_external_ids.add(external_id)

    for field_name in LIST_FIELDS:
        value = record.get(field_name, [])
        _require(
            isinstance(value, list),
            f"Dataset record {index} field {field_name} must be a list.",
        )

    raw_row = record.get("raw_row", {})
    _require(
        isinstance(raw_row, dict),
        f"Dataset record {index} field raw_row must be an object.",
    )

    source_row_number = record.get("source_row_number")
    _require(
        source_row_number is None
        or (
            isinstance(source_row_number, int)
            and source_row_number > 0
        ),
        (
            f"Dataset record {index} source_row_number must be "
            "a positive integer or null."
        ),
    )


def _text_value(record: dict[str, Any], field_name: str) -> str:
    value = record.get(field_name)

    if value is None:
        return ""

    return str(value).strip()


def _record_defaults(record: dict[str, Any]) -> dict[str, Any]:
    defaults = {
        field_name: _text_value(record, field_name)
        for field_name in TEXT_FIELDS
    }

    for field_name in LIST_FIELDS:
        defaults[field_name] = record.get(field_name, [])

    defaults.update(
        {
            "source_row_number": record.get("source_row_number"),
            "raw_row": record.get("raw_row", {}),
            "record_sha256": record_content_sha256(record),
        }
    )

    return defaults


def _update_imported_fields(
    instance: ExternalSchemeRecord,
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
        update_fields=[
            *changed_fields,
            "updated_at",
        ],
    )
    return True


@transaction.atomic
def import_external_scheme_dataset(
    payload: dict[str, Any],
) -> dict[str, Any]:
    dataset_defaults = {
        "dataset_name": payload["dataset_name"].strip(),
        "source_filename": payload["source_filename"].strip(),
        "source_sheet": _text_value(payload, "source_sheet"),
        "source_row_count": int(
            payload.get("source_row_count") or 0
        ),
        "record_count": len(payload["records"]),
        "normalization_version": (
            payload["normalization_version"].strip()
        ),
        "content_sha256": payload["content_sha256"],
        "is_active": True,
        "metadata": {
            "import_format": "normalized-external-schemes-v1",
        },
    }

    dataset, dataset_created = (
        ExternalSchemeDataset.objects.update_or_create(
            dataset_key=payload["dataset_key"].strip(),
            defaults=dataset_defaults,
        )
    )

    created_count = 0
    updated_count = 0
    unchanged_count = 0
    imported_external_ids = []

    for record in payload["records"]:
        external_id = record["external_id"].strip()
        imported_external_ids.append(external_id)
        defaults = _record_defaults(record)

        instance, created = (
            ExternalSchemeRecord.objects.get_or_create(
                dataset=dataset,
                external_id=external_id,
                defaults=defaults,
            )
        )

        if created:
            created_count += 1
            continue

        if instance.record_sha256 == defaults["record_sha256"]:
            unchanged_count += 1
            continue

        _update_imported_fields(instance, defaults)
        updated_count += 1

    stale_records = dataset.records.exclude(
        external_id__in=imported_external_ids,
    )
    removed_count = stale_records.count()
    stale_records.delete()

    return {
        "dataset": dataset,
        "dataset_created": dataset_created,
        "created": created_count,
        "updated": updated_count,
        "unchanged": unchanged_count,
        "removed": removed_count,
    }


class Command(BaseCommand):
    help = (
        "Import a normalized external scheme dataset into "
        "non-canonical review staging tables."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            nargs="?",
            default=str(DEFAULT_DATASET_PATH),
            help=(
                "Path to the normalized external scheme "
                "JSON dataset."
            ),
        )

    def handle(self, *args, **options):
        path = Path(options["path"]).expanduser().resolve()
        payload = _read_dataset(path)
        result = import_external_scheme_dataset(payload)
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
