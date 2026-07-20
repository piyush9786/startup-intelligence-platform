from __future__ import annotations

import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.sources.models import Source

REQUIRED_COLUMNS = {
    "name",
    "category",
    "official_domain",
    "listing_url",
    "authority_tier",
    "crawl_frequency",
}


def parse_bool(value: str, default: bool = True) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return default
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n"}:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


class Command(BaseCommand):
    help = "Import or update the authoritative source registry from CSV."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=str(settings.BASE_DIR / "catalog/source_registry/sources.csv"),
        )
        parser.add_argument(
            "--deactivate-missing",
            action="store_true",
            help="Deactivate existing sources absent from the CSV file.",
        )

    def handle(self, *args, **options):
        path = Path(options["file"]).expanduser().resolve()
        if not path.exists():
            raise CommandError(f"Source registry file does not exist: {path}")

        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames or [])
            if missing_columns:
                raise CommandError(f"CSV is missing required columns: {sorted(missing_columns)}")

            created = 0
            updated = 0
            seen_domains: set[str] = set()
            for row_number, row in enumerate(reader, start=2):
                try:
                    domain = row["official_domain"].strip().lower()
                    if not domain:
                        raise ValueError("official_domain is empty")
                    defaults = {
                        "name": row["name"].strip(),
                        "category": row["category"].strip(),
                        "ministry": row.get("ministry", "").strip(),
                        "department": row.get("department", "").strip(),
                        "state": row.get("state", "").strip(),
                        "allowed_domains": [
                            item.strip().lower()
                            for item in row.get("allowed_domains", "").split("|")
                            if item.strip()
                        ],
                        "listing_url": row["listing_url"].strip(),
                        "application_portal_url": row.get("application_portal_url", "").strip(),
                        "authority_tier": row["authority_tier"].strip(),
                        "crawl_frequency": row["crawl_frequency"].strip(),
                        "language": row.get("language", "en").strip() or "en",
                        "active": parse_bool(row.get("active", "true")),
                        "respect_robots_txt": parse_bool(row.get("respect_robots_txt", "true")),
                        "notes": row.get("notes", "").strip(),
                    }
                    _, was_created = Source.objects.update_or_create(
                        official_domain=domain,
                        defaults=defaults,
                    )
                except Exception as exc:
                    raise CommandError(f"Invalid source registry row {row_number}: {exc}") from exc
                seen_domains.add(domain)
                created += int(was_created)
                updated += int(not was_created)

        deactivated = 0
        if options["deactivate_missing"]:
            deactivated = Source.objects.exclude(official_domain__in=seen_domains).update(
                active=False
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Source registry imported: {created} created, "
                f"{updated} updated, {deactivated} deactivated."
            )
        )
