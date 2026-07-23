from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.knowledge.models import ExternalSchemeDataset, ExternalSchemeRecord
from apps.schemes.models import Scheme

DEFAULT_MANIFEST_PATH = (
    Path(settings.BASE_DIR)
    / "apps"
    / "knowledge"
    / "pilot"
    / "manifests"
    / "external_scheme_review_v1.json"
)

TEXT_OVERRIDE_FIELDS = {
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
}

LIST_OVERRIDE_FIELDS = {
    "startup_stage",
    "industry",
    "documents_required",
    "quality_warnings",
}

SUPPORTED_STATUSES = {
    ExternalSchemeRecord.ReviewStatus.VERIFIED,
    ExternalSchemeRecord.ReviewStatus.REJECTED,
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CommandError(message)


def _is_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def read_review_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CommandError(
            f"Could not read external scheme review manifest: {path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise CommandError(
            f"External scheme review manifest is not valid JSON: {exc}"
        ) from exc

    _require(
        isinstance(payload, dict),
        "External scheme review manifest root must be an object.",
    )
    _require(
        payload.get("schema_version") == 1,
        "External scheme review manifest schema_version must be 1.",
    )

    for field_name in (
        "manifest_key",
        "dataset_key",
        "reviewed_on",
        "reviewer",
    ):
        value = payload.get(field_name)
        _require(
            isinstance(value, str) and value.strip(),
            f"External scheme review manifest requires {field_name}.",
        )

    decisions = payload.get("decisions")
    _require(
        isinstance(decisions, list) and decisions,
        "External scheme review manifest decisions must be a non-empty list.",
    )

    seen_external_ids: set[str] = set()
    allowed_override_fields = (
        TEXT_OVERRIDE_FIELDS | LIST_OVERRIDE_FIELDS
    )

    for index, decision in enumerate(decisions, start=1):
        _require(
            isinstance(decision, dict),
            f"Review decision {index} must be an object.",
        )

        external_id = decision.get("external_id")
        _require(
            isinstance(external_id, str) and external_id.strip(),
            f"Review decision {index} requires external_id.",
        )
        _require(
            external_id not in seen_external_ids,
            f"Duplicate review decision for external_id {external_id}.",
        )
        seen_external_ids.add(external_id)

        status = decision.get("status")
        _require(
            status in SUPPORTED_STATUSES,
            (
                f"Review decision {external_id} has unsupported "
                f"status {status!r}."
            ),
        )

        source_url = decision.get("official_source_url")
        _require(
            isinstance(source_url, str)
            and _is_https_url(source_url.strip()),
            (
                f"Review decision {external_id} requires an "
                "official HTTPS source URL."
            ),
        )

        note = decision.get("note")
        _require(
            isinstance(note, str) and note.strip(),
            f"Review decision {external_id} requires a review note.",
        )

        matched_scheme_name = decision.get("matched_scheme_name")
        _require(
            matched_scheme_name is None
            or (
                isinstance(matched_scheme_name, str)
                and matched_scheme_name.strip()
            ),
            (
                f"Review decision {external_id} matched_scheme_name "
                "must be a non-empty string when supplied."
            ),
        )
        _require(
            not matched_scheme_name
            or status == ExternalSchemeRecord.ReviewStatus.VERIFIED,
            (
                f"Review decision {external_id} can only match a "
                "canonical scheme when verified."
            ),
        )

        overrides = decision.get("overrides", {})
        _require(
            isinstance(overrides, dict),
            f"Review decision {external_id} overrides must be an object.",
        )
        unknown_fields = set(overrides) - allowed_override_fields
        _require(
            not unknown_fields,
            (
                f"Review decision {external_id} contains unsupported "
                f"override fields: {sorted(unknown_fields)}."
            ),
        )

        for field_name, value in overrides.items():
            if field_name in TEXT_OVERRIDE_FIELDS:
                _require(
                    isinstance(value, str),
                    (
                        f"Review decision {external_id} field "
                        f"{field_name} must be a string."
                    ),
                )
            else:
                _require(
                    isinstance(value, list),
                    (
                        f"Review decision {external_id} field "
                        f"{field_name} must be a list."
                    ),
                )

    return payload


def _resolve_canonical_scheme(
    canonical_name: str,
    *,
    external_id: str,
) -> Scheme:
    matches = Scheme.objects.filter(
        canonical_name=canonical_name,
    )
    count = matches.count()
    _require(
        count == 1,
        (
            f"Review decision {external_id} expected exactly one "
            f"canonical scheme named {canonical_name!r}; found {count}."
        ),
    )
    return matches.get()


@transaction.atomic
def apply_review_manifest(
    payload: dict[str, Any],
    *,
    check_only: bool = False,
) -> dict[str, int]:
    try:
        dataset = ExternalSchemeDataset.objects.get(
            dataset_key=payload["dataset_key"].strip(),
        )
    except ExternalSchemeDataset.DoesNotExist as exc:
        raise CommandError(
            "Import the external scheme dataset before applying its "
            f"review manifest: {payload['dataset_key']}"
        ) from exc

    records = {
        record.external_id: record
        for record in dataset.records.select_for_update()
    }
    decisions = {
        decision["external_id"]: decision
        for decision in payload["decisions"]
    }

    missing_decisions = set(records) - set(decisions)
    unknown_decisions = set(decisions) - set(records)
    _require(
        not missing_decisions and not unknown_decisions,
        (
            "Review manifest must cover the imported dataset exactly. "
            f"Missing decisions: {sorted(missing_decisions)}. "
            f"Unknown decisions: {sorted(unknown_decisions)}."
        ),
    )

    verified = 0
    rejected = 0
    matched = 0
    changed = 0
    clear_warnings = bool(
        payload.get("clear_quality_warnings_for_verified", False)
    )
    apply_source_url = bool(
        payload.get(
            "apply_source_url_to_official_application_url",
            False,
        )
    )

    for external_id, decision in decisions.items():
        record = records[external_id]
        status = decision["status"]
        source_url = decision["official_source_url"].strip()
        matched_scheme = None

        if decision.get("matched_scheme_name"):
            matched_scheme = _resolve_canonical_scheme(
                decision["matched_scheme_name"].strip(),
                external_id=external_id,
            )
            matched += 1

        if status == ExternalSchemeRecord.ReviewStatus.VERIFIED:
            verified += 1
        else:
            rejected += 1

        values: dict[str, Any] = {
            "review_status": status,
            "matched_scheme": matched_scheme,
            "matched_candidate": None,
            "review_notes": (
                f"Reviewed {payload['reviewed_on']} by "
                f"{payload['reviewer'].strip()}. Official source: "
                f"{source_url}. {decision['note'].strip()}"
            ),
        }
        values.update(decision.get("overrides", {}))

        if apply_source_url:
            values.setdefault(
                "official_application_url",
                source_url,
            )

        if (
            clear_warnings
            and status == ExternalSchemeRecord.ReviewStatus.VERIFIED
        ):
            values.setdefault("quality_warnings", [])

        changed_fields = []
        for field_name, value in values.items():
            if getattr(record, field_name) == value:
                continue
            setattr(record, field_name, value)
            changed_fields.append(field_name)

        if not changed_fields:
            continue

        changed += 1
        if not check_only:
            record.save(
                update_fields=[
                    *changed_fields,
                    "updated_at",
                ],
            )

    if check_only:
        transaction.set_rollback(True)

    return {
        "verified": verified,
        "rejected": rejected,
        "matched": matched,
        "changed": changed,
        "total": len(decisions),
    }


class Command(BaseCommand):
    help = (
        "Validate and apply a complete, official-source review manifest "
        "to an imported external scheme dataset."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            nargs="?",
            default=str(DEFAULT_MANIFEST_PATH),
            help="Path to the external scheme review manifest.",
        )
        parser.add_argument(
            "--check",
            action="store_true",
            help="Validate coverage and references without saving changes.",
        )

    def handle(self, *args, **options):
        path = Path(options["path"]).expanduser().resolve()
        payload = read_review_manifest(path)
        result = apply_review_manifest(
            payload,
            check_only=options["check"],
        )
        action = "Validated" if options["check"] else "Applied"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} {payload['manifest_key']}: "
                f"{result['total']} decisions "
                f"({result['verified']} verified, "
                f"{result['rejected']} rejected, "
                f"{result['matched']} canonical matches, "
                f"{result['changed']} records changed)."
            )
        )
