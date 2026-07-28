from __future__ import annotations

import csv

import pytest
from django.core.management import call_command

from apps.sources.models import Source


@pytest.mark.django_db
def test_import_sources_is_idempotent(tmp_path):
    path = tmp_path / "sources.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "name",
                "category",
                "official_domain",
                "listing_url",
                "authority_tier",
                "crawl_frequency",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "name": "Example Authority",
                "category": "test",
                "official_domain": "example.com",
                "listing_url": "https://example.com/schemes",
                "authority_tier": "B",
                "crawl_frequency": "weekly",
            }
        )

    call_command("import_sources", file=str(path))
    call_command("import_sources", file=str(path))

    assert Source.objects.count() == 1
    assert Source.objects.get().name == "Example Authority"
