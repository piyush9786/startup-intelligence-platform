import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.knowledge.models import ExternalSchemeDataset, ExternalSchemeRecord
from apps.schemes.models import Authority, Scheme

pytestmark = pytest.mark.django_db


def create_dataset() -> ExternalSchemeDataset:
    dataset = ExternalSchemeDataset.objects.create(
        dataset_key="review-test-v1",
        dataset_name="Review test",
        source_filename="review-test.json",
        source_row_count=2,
        record_count=2,
        normalization_version="test-v1",
        content_sha256="a" * 64,
        is_active=True,
    )

    for external_id, name in (
        ("SCH001", "Canonical copy"),
        ("SCH002", "Unsupported copy"),
    ):
        ExternalSchemeRecord.objects.create(
            dataset=dataset,
            external_id=external_id,
            scheme_name=name,
            normalized_name=name.lower(),
            official_application_url="https://old.example/source",
            quality_warnings=["Imported column warning"],
            record_sha256=external_id.lower().ljust(64, "0")[:64],
        )

    return dataset


def write_manifest(
    path,
    *,
    decisions: list[dict] | None = None,
) -> None:
    payload = {
        "schema_version": 1,
        "manifest_key": "review-test-manifest",
        "dataset_key": "review-test-v1",
        "reviewed_on": "2026-07-24",
        "reviewer": "Test reviewer",
        "clear_quality_warnings_for_verified": True,
        "apply_source_url_to_official_application_url": True,
        "decisions": decisions
        or [
            {
                "external_id": "SCH001",
                "status": "verified",
                "matched_scheme_name": "Canonical Scheme",
                "official_source_url": (
                    "https://authority.gov.in/canonical"
                ),
                "note": "Matched to the published scheme.",
                "overrides": {
                    "funding_amount": "Up to INR 10 lakh",
                },
            },
            {
                "external_id": "SCH002",
                "status": "rejected",
                "official_source_url": (
                    "https://authority.gov.in/programmes"
                ),
                "note": "No current programme exists.",
            },
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_review_manifest_applies_complete_decisions(tmp_path):
    dataset = create_dataset()
    authority = Authority.objects.create(name="Test Authority")
    canonical = Scheme.objects.create(
        canonical_name="Canonical Scheme",
        authority=authority,
        lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
    )
    path = tmp_path / "review.json"
    write_manifest(path)

    call_command("review_external_schemes", str(path))

    matched = dataset.records.get(external_id="SCH001")
    rejected = dataset.records.get(external_id="SCH002")

    assert matched.review_status == (
        ExternalSchemeRecord.ReviewStatus.VERIFIED
    )
    assert matched.matched_scheme == canonical
    assert matched.matched_candidate is None
    assert matched.funding_amount == "Up to INR 10 lakh"
    assert matched.quality_warnings == []
    assert matched.official_application_url == (
        "https://authority.gov.in/canonical"
    )
    assert "Reviewed 2026-07-24" in matched.review_notes
    assert "https://authority.gov.in/canonical" in matched.review_notes

    assert rejected.review_status == (
        ExternalSchemeRecord.ReviewStatus.REJECTED
    )
    assert rejected.matched_scheme is None
    assert rejected.quality_warnings == [
        "Imported column warning",
    ]


def test_review_manifest_requires_exact_dataset_coverage(tmp_path):
    create_dataset()
    path = tmp_path / "review.json"
    write_manifest(
        path,
        decisions=[
            {
                "external_id": "SCH001",
                "status": "rejected",
                "official_source_url": (
                    "https://authority.gov.in/programmes"
                ),
                "note": "Incomplete test decision.",
            },
        ],
    )

    with pytest.raises(
        CommandError,
        match="must cover the imported dataset exactly",
    ):
        call_command("review_external_schemes", str(path))


def test_review_manifest_check_does_not_save(tmp_path):
    dataset = create_dataset()
    authority = Authority.objects.create(name="Test Authority")
    Scheme.objects.create(
        canonical_name="Canonical Scheme",
        authority=authority,
    )
    path = tmp_path / "review.json"
    write_manifest(path)

    call_command(
        "review_external_schemes",
        str(path),
        check=True,
    )

    record = dataset.records.get(external_id="SCH001")
    assert record.review_status == (
        ExternalSchemeRecord.ReviewStatus.NEEDS_REVIEW
    )
    assert record.matched_scheme is None
    assert record.official_application_url == (
        "https://old.example/source"
    )


def test_review_manifest_rejects_non_https_sources(tmp_path):
    create_dataset()
    path = tmp_path / "review.json"
    write_manifest(
        path,
        decisions=[
            {
                "external_id": "SCH001",
                "status": "rejected",
                "official_source_url": "http://authority.gov.in/source",
                "note": "Insecure source test.",
            },
            {
                "external_id": "SCH002",
                "status": "rejected",
                "official_source_url": (
                    "https://authority.gov.in/source"
                ),
                "note": "Valid source.",
            },
        ],
    )

    with pytest.raises(
        CommandError,
        match="official HTTPS source URL",
    ):
        call_command("review_external_schemes", str(path))
