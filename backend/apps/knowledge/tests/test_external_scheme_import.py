import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.knowledge.management.commands.import_external_schemes import (
    canonical_content_sha256,
)
from apps.knowledge.models import (
    ExternalSchemeDataset,
    ExternalSchemeRecord,
    SchemeCandidate,
)
from apps.schemes.models import Scheme

pytestmark = pytest.mark.django_db


def make_record(
    *,
    external_id: str,
    scheme_name: str,
    normalized_name: str,
    source_row_number: int,
) -> dict:
    return {
        "external_id": external_id,
        "scheme_name": scheme_name,
        "normalized_name": normalized_name,
        "ministry": "Example Ministry",
        "department": "",
        "sector": "Startup",
        "startup_stage": ["Idea"],
        "startup_type": "Startup",
        "industry": ["All Industries"],
        "central_state": "Central",
        "state": "All India",
        "funding_type": "Grant",
        "funding_amount": "Up to INR 10 lakh",
        "financial_instrument": "Grant",
        "eligibility": "Example eligibility",
        "women_eligible": "Yes",
        "sc_st_eligible": "Yes",
        "dpiit_required": "No",
        "startup_age_limit": "",
        "revenue_criteria": "",
        "tax_benefits": "",
        "documents_required": ["Registration certificate"],
        "application_process": "Apply online",
        "official_website_label": "Example portal",
        "official_application_url": "https://example.gov.in/apply",
        "source_portal": "Example portal",
        "claimed_last_updated": "2026",
        "source_row_number": source_row_number,
        "quality_warnings": [],
        "raw_row": {
            "scheme_id": external_id,
            "scheme_name": scheme_name,
        },
        "source_rows": [source_row_number],
        "external_ids": [external_id],
    }


def write_dataset(path, records: list[dict]) -> dict:
    payload = {
        "dataset_key": "test-external-schemes-v1",
        "dataset_name": "Test external schemes",
        "source_filename": "test-schemes.xlsx",
        "source_sheet": "Schemes",
        "source_row_count": len(records),
        "record_count": len(records),
        "normalization_version": "external-schemes-normalizer-v1",
        "records": records,
    }
    payload["content_sha256"] = canonical_content_sha256(payload)

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return payload


def test_import_creates_review_staging_records_only(tmp_path):
    path = tmp_path / "schemes.json"

    canonical_count_before = Scheme.objects.count()
    candidate_count_before = SchemeCandidate.objects.count()

    write_dataset(
        path,
        [
            make_record(
                external_id="SCH001",
                scheme_name="First Scheme",
                normalized_name="first scheme",
                source_row_number=2,
            ),
            make_record(
                external_id="SCH002",
                scheme_name="Second Scheme",
                normalized_name="second scheme",
                source_row_number=3,
            ),
        ],
    )

    call_command("import_external_schemes", str(path))

    dataset = ExternalSchemeDataset.objects.get(
        dataset_key="test-external-schemes-v1",
    )

    assert dataset.source_row_count == 2
    assert dataset.record_count == 2
    assert dataset.records.count() == 2

    first = dataset.records.get(external_id="SCH001")

    assert first.scheme_name == "First Scheme"
    assert first.normalized_name == "first scheme"
    assert first.review_status == (
        ExternalSchemeRecord.ReviewStatus.NEEDS_REVIEW
    )
    assert first.matched_candidate is None
    assert first.matched_scheme is None
    assert first.raw_row["scheme_id"] == "SCH001"

    assert Scheme.objects.count() == canonical_count_before
    assert SchemeCandidate.objects.count() == candidate_count_before


def test_repeated_import_is_idempotent_and_syncs_source_changes(
    tmp_path,
):
    path = tmp_path / "schemes.json"

    write_dataset(
        path,
        [
            make_record(
                external_id="SCH001",
                scheme_name="First Scheme",
                normalized_name="first scheme",
                source_row_number=2,
            ),
            make_record(
                external_id="SCH002",
                scheme_name="Second Scheme",
                normalized_name="second scheme",
                source_row_number=3,
            ),
        ],
    )

    call_command("import_external_schemes", str(path))
    call_command("import_external_schemes", str(path))

    assert ExternalSchemeDataset.objects.count() == 1
    assert ExternalSchemeRecord.objects.count() == 2

    first = ExternalSchemeRecord.objects.get(
        external_id="SCH001",
    )
    first.review_status = ExternalSchemeRecord.ReviewStatus.VERIFIED
    first.review_notes = "Reviewed manually."
    first.save(
        update_fields=[
            "review_status",
            "review_notes",
            "updated_at",
        ],
    )

    write_dataset(
        path,
        [
            make_record(
                external_id="SCH001",
                scheme_name="First Scheme Updated",
                normalized_name="first scheme updated",
                source_row_number=2,
            ),
        ],
    )

    call_command("import_external_schemes", str(path))

    first.refresh_from_db()

    assert ExternalSchemeRecord.objects.count() == 1
    assert first.scheme_name == "First Scheme Updated"
    assert first.normalized_name == "first scheme updated"

    # Manual review decisions must survive source re-imports.
    assert first.review_status == (
        ExternalSchemeRecord.ReviewStatus.VERIFIED
    )
    assert first.review_notes == "Reviewed manually."

    assert not ExternalSchemeRecord.objects.filter(
        external_id="SCH002",
    ).exists()


def test_import_rejects_invalid_canonical_hash(tmp_path):
    path = tmp_path / "schemes.json"

    payload = write_dataset(
        path,
        [
            make_record(
                external_id="SCH001",
                scheme_name="First Scheme",
                normalized_name="first scheme",
                source_row_number=2,
            ),
        ],
    )

    payload["content_sha256"] = "0" * 64
    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(
        CommandError,
        match="canonical content hash",
    ):
        call_command("import_external_schemes", str(path))

    assert ExternalSchemeDataset.objects.count() == 0
    assert ExternalSchemeRecord.objects.count() == 0


def test_import_rejects_duplicate_external_ids(tmp_path):
    path = tmp_path / "schemes.json"

    duplicate = make_record(
        external_id="SCH001",
        scheme_name="Duplicate Scheme",
        normalized_name="duplicate scheme",
        source_row_number=3,
    )

    write_dataset(
        path,
        [
            make_record(
                external_id="SCH001",
                scheme_name="First Scheme",
                normalized_name="first scheme",
                source_row_number=2,
            ),
            duplicate,
        ],
    )

    with pytest.raises(
        CommandError,
        match="Duplicate external_id",
    ):
        call_command("import_external_schemes", str(path))

    assert ExternalSchemeDataset.objects.count() == 0
    assert ExternalSchemeRecord.objects.count() == 0
