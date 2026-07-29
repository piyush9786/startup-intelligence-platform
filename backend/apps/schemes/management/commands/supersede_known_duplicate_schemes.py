"""Safely supersede two exact duplicate canonical scheme rows.

No SchemeVersion, evidence document, recommendation, or audit row is deleted.
The duplicate Scheme remains available for historical references, while active
catalog/search paths use the keeper and the duplicate title becomes an alias.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.knowledge.models import ExternalCapitalSupportRecord, ExternalSchemeRecord
from apps.schemes.models import Scheme, SchemeVersion

DUPLICATE_PAIRS = (
    (
        "Prime Minister Employment Generation Programme (PMEGP)",
        "Prime Minister's Employment Generation Programme (PMEGP)",
    ),
    (
        "Procurement & Marketing Support (PMS) Scheme",
        "Procurement and Marketing Support (PMS) Scheme",
    ),
)


def _unique(values):
    result = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        key = text.casefold()
        if text and key not in seen:
            result.append(text)
            seen.add(key)
    return result


@transaction.atomic
def supersede_duplicates(*, dry_run: bool) -> dict[str, int]:
    counts = {"pairs": 0, "external_links": 0, "capital_links": 0}

    for keeper_name, duplicate_name in DUPLICATE_PAIRS:
        keepers = Scheme.objects.select_for_update().filter(canonical_name=keeper_name)
        duplicates = Scheme.objects.select_for_update().filter(canonical_name=duplicate_name)
        if keepers.count() != 1 or duplicates.count() != 1:
            raise CommandError(
                f"Expected exactly one keeper and duplicate for {keeper_name!r} / "
                f"{duplicate_name!r}; found {keepers.count()} and {duplicates.count()}."
            )

        keeper = keepers.get()
        duplicate = duplicates.get()
        if not keeper.current_version_id or not duplicate.current_version_id:
            raise CommandError("Both duplicate candidates must have current versions.")

        keeper_version = keeper.current_version
        duplicate_version = duplicate.current_version
        same_document = (
            keeper_version.source_document_id == duplicate_version.source_document_id
        )
        same_url = (
            keeper_version.official_url.rstrip("/").casefold()
            == duplicate_version.official_url.rstrip("/").casefold()
        )
        if not (same_document and same_url):
            raise CommandError(
                f"Refusing to merge {duplicate_name!r}: official URL and proof document "
                "do not both match the keeper."
            )

        aliases = _unique(
            [
                *(keeper.alternative_names or []),
                duplicate.canonical_name,
                *(duplicate.alternative_names or []),
            ]
        )
        keeper.alternative_names = aliases
        keeper.lifecycle_status = Scheme.LifecycleStatus.ACTIVE
        keeper.save(update_fields=["alternative_names", "lifecycle_status", "updated_at"])

        counts["external_links"] += ExternalSchemeRecord.objects.filter(
            matched_scheme=duplicate
        ).update(matched_scheme=keeper)
        counts["capital_links"] += ExternalCapitalSupportRecord.objects.filter(
            matched_scheme=duplicate
        ).update(matched_scheme=keeper)

        duplicate.lifecycle_status = Scheme.LifecycleStatus.SUPERSEDED
        duplicate.save(update_fields=["lifecycle_status", "updated_at"])
        counts["pairs"] += 1

    if dry_run:
        transaction.set_rollback(True)
    return counts


class Command(BaseCommand):
    help = "Supersede the two evidence-confirmed duplicate canonical schemes without deleting audit data."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--expected-total", type=int, default=75)

    def handle(self, *args, **options):
        counts = supersede_duplicates(dry_run=options["dry_run"])
        active_total = Scheme.objects.filter(
            lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
            current_version__verification_status=SchemeVersion.VerificationStatus.VERIFIED,
        ).count()
        projected_total = active_total - counts["pairs"] if options["dry_run"] else active_total
        if projected_total != options["expected_total"]:
            raise CommandError(
                f"Expected {options['expected_total']} active verified unique schemes after "
                f"deduplication; found/projected {projected_total}."
            )
        prefix = "Dry run" if options["dry_run"] else "Deduplication"
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix} complete: pairs={counts['pairs']}, "
                f"external_links={counts['external_links']}, "
                f"capital_links={counts['capital_links']}, "
                f"active_verified_unique={projected_total}"
            )
        )
