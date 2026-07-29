import pytest
from django.core.management import call_command

from apps.knowledge.models import ExternalSchemeDataset, ExternalSchemeRecord
from apps.schemes.models import Scheme, SchemeVersion
from apps.sources.models import SourceDocument

pytestmark = pytest.mark.django_db


def _record(*, status="verified", external_id="SCH100"):
    dataset = ExternalSchemeDataset.objects.create(
        dataset_key="canonicalization-test-v1",
        dataset_name="Canonicalization test",
        source_filename="test.json",
        source_row_count=1,
        record_count=1,
        normalization_version="test-v1",
        content_sha256="a" * 64,
        is_active=True,
    )
    return ExternalSchemeRecord.objects.create(
        dataset=dataset,
        external_id=external_id,
        scheme_name="Women Technology Grant",
        normalized_name="women technology grant",
        ministry="Test Ministry",
        department="Test Department",
        sector="Technology",
        startup_stage=["Idea", "Prototype"],
        funding_type="Grant",
        funding_amount="Up to INR 10 lakh",
        financial_instrument="Grant",
        eligibility="Eligible technology startups may apply.",
        dpiit_required="Yes",
        documents_required=["DPIIT certificate"],
        application_process="Apply on the official portal.",
        official_application_url="https://authority.gov.in/grant",
        source_portal="Test Authority",
        source_row_number=42,
        source_rows=[42],
        external_ids=[external_id],
        record_sha256="b" * 64,
        review_status=status,
        review_notes=(
            "Reviewed 2026-07-28 by Test reviewer. Official source: "
            "https://authority.gov.in/grant. Confirmed."
        ),
    )


def test_verified_unmatched_record_becomes_canonical_and_keeps_proof():
    record = _record()

    call_command("canonicalize_verified_external_schemes")

    record.refresh_from_db()
    scheme = record.matched_scheme
    assert scheme is not None
    assert scheme.lifecycle_status == Scheme.LifecycleStatus.ACTIVE
    assert scheme.current_version.verification_status == (
        SchemeVersion.VerificationStatus.VERIFIED
    )
    assert scheme.current_version.official_url == "https://authority.gov.in/grant"
    assert scheme.current_version.eligible_stages == ["idea", "prototype"]
    assert scheme.current_version.eligibility_rules.filter(
        field_path="dpiit_recognized",
        manually_verified=True,
    ).exists()

    proof = SourceDocument.objects.get(extractor_version="external-review-canonicalizer-v1")
    rows = proof.metadata["external_scheme_reviews"]
    assert rows[0]["external_id"] == record.external_id
    assert rows[0]["record_sha256"] == record.record_sha256
    assert "Official source" in rows[0]["review_notes"]
    assert proof.metadata["independent_live_crawl"] is False


def test_command_is_idempotent():
    _record()
    call_command("canonicalize_verified_external_schemes")
    first = (Scheme.objects.count(), SchemeVersion.objects.count(), SourceDocument.objects.count())

    call_command("canonicalize_verified_external_schemes")

    assert (Scheme.objects.count(), SchemeVersion.objects.count(), SourceDocument.objects.count()) == first


def test_rejected_records_are_not_published():
    _record(status=ExternalSchemeRecord.ReviewStatus.REJECTED)
    call_command("canonicalize_verified_external_schemes")
    assert Scheme.objects.count() == 0
