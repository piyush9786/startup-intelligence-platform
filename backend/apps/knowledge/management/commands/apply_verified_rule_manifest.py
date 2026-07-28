from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.knowledge.services.rule_revision import (
    apply_verified_rule_revision_plan,
    build_verified_rule_revision_plan,
)

DEFAULT_MANIFEST = (
    Path(settings.BASE_DIR)
    / "apps"
    / "knowledge"
    / "pilot"
    / "manifests"
    / "verified_rules_v1"
    / "manifest_verified_executable_rules_pilot_v1.json"
)


def _read_manifest(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CommandError(f"Could not read verified rule manifest: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CommandError(f"Verified rule manifest is not valid JSON: {exc}") from exc


def _reviewer_by_email(email: str):
    user_model = get_user_model()
    try:
        return user_model.objects.get(email__iexact=email.strip())
    except user_model.DoesNotExist as exc:
        raise CommandError(f"Reviewer not found: {email}") from exc
    except user_model.MultipleObjectsReturned as exc:
        raise CommandError("Reviewer email is not unique.") from exc


class Command(BaseCommand):
    help = (
        "Validate or apply immutable verified eligibility-rule revisions. "
        "Dry-run is the default."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--manifest",
            default=str(DEFAULT_MANIFEST),
            help="Path to the verified rule manifest JSON.",
        )
        parser.add_argument(
            "--reviewer-email",
            required=True,
            help="Reviewer or administrator email for audit fields.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help=(
                "Create new verified scheme versions atomically. "
                "Without this flag, no writes occur."
            ),
        )

    def handle(self, *args, **options):
        path = Path(options["manifest"]).expanduser().resolve()
        manifest = _read_manifest(path)
        reviewer = _reviewer_by_email(options["reviewer_email"])

        try:
            plan = build_verified_rule_revision_plan(
                manifest=manifest,
                reviewer=reviewer,
            )
        except ValidationError as exc:
            raise CommandError(
                f"Verified rule manifest validation failed: {exc}"
            ) from exc

        mode = "APPLY" if options["apply"] else "DRY RUN"
        self.stdout.write(f"{mode}: {plan.manifest_key}")
        for row in plan.rows:
            status = "unchanged" if row.existing_revision is not None else "create_version"
            self.stdout.write(
                f"- {row.pilot_key}: "
                f"scheme={row.scheme.id} "
                f"base=v{row.base_version.version_number} "
                f"rules={len(row.rules)} "
                f"executable={row.executable_count} "
                f"manual={row.manual_count} "
                f"status={status}"
            )

        if not options["apply"]:
            self.stdout.write(
                self.style.WARNING(
                    "No database writes performed. Run again with --apply "
                    "to create immutable verified versions."
                )
            )
            return

        try:
            results = apply_verified_rule_revision_plan(plan)
        except ValidationError as exc:
            raise CommandError(f"Verified rule revision apply failed: {exc}") from exc

        for result in results:
            self.stdout.write(
                f"- {result.pilot_key}: {result.status} "
                f"v{result.base_version.version_number} -> "
                f"v{result.revised_version.version_number}"
            )

        self.stdout.write(
            self.style.SUCCESS("Verified eligibility-rule revisions applied.")
        )
