import json
from copy import deepcopy

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.knowledge.management.commands.import_external_knowledge import (
    CAPITAL_FORMAT,
    CERTIFICATION_FORMAT,
    canonical_content_sha256,
)
from apps.knowledge.models import (
    ExternalCapitalSupportRecord,
    ExternalCertificationRequirementRecord,
    ExternalKnowledgeDataset,
    ExternalSchemeDataset,
    ExternalSchemeRecord,
    SchemeCandidate,
)
from apps.schemes.models import Scheme

pytestmark = pytest.mark.django_db


def capital_record(
    external_id: str = "CAP001",
) -> dict:
    return {
        "external_id": external_id,
        "support_name": "Startup Loan Support",
        "support_type": "Loan",
        "scheme_name": "Example Scheme",
        "normalized_name": "example scheme",
        "ministry": "Example Ministry",
        "implementing_agency": "Example Bank",
        "funding_category": "Term Loan",
        "minimum_amount": "100000",
        "maximum_amount": "500000",
        "raw_minimum_amount": "100000",
        "raw_maximum_amount": "500000",
        "currency": "INR",
        "interest_rate_text": "As per scheme",
        "collateral_required_text": "Depends",
        "repayment_required_text": "Yes",
        "startup_stage": ["Idea"],
        "industry": ["All"],
        "eligible_entity": "Eligible startups",
        "state": "Pan India",
        "funding_purpose": "Business setup",
        "claimed_scheme_status": "Active",
        "source_priority_score": 10,
        "source_ai_recommendation_weight": 0.95,
        "remarks": "Source-only ranking fields",
        "matched_external_scheme_ids": ["EXT001"],
        "review_status": "needs_review",
        "quality_warnings": ["Official verification required."],
        "source_row_number": 2,
        "raw_row": {"support_id": external_id},
    }


def certification_record(
    *,
    external_id: str,
    display_eligible: bool,
    review_status: str,
) -> dict:
    return {
        "external_id": external_id,
        "certificate_name": f"Certificate {external_id}",
        "normalized_name": f"certificate {external_id.lower()}",
        "certificate_type": "Government Recognition",
        "description": "Example certification requirement",
        "industry": ["All"],
        "startup_stage": ["Idea"],
        "requirement_level": "optional",
        "eligibility": "Eligible startups",
        "benefits": "Example benefits",
        "validity": "Permanent",
        "renewal_period": "NA",
        "issuing_authority": "Example Authority",
        "official_document_text": "Certificate of incorporation",
        "official_apply_url": "https://example.gov.in/apply",
        "source_priority_score": 10,
        "display_eligible": display_eligible,
        "review_status": review_status,
        "quality_warnings": ["Official verification required."],
        "source_row_number": 2,
        "raw_row": {"certificate_id": external_id},
    }


def write_dataset(
    path,
    *,
    import_format: str,
    records: list[dict],
) -> dict:
    payload = {
        "dataset_key": f"test-{import_format}",
        "dataset_name": "Test external knowledge",
        "source_filename": "test.xlsx",
        "source_sheet": "Sheet1",
        "source_row_count": len(records),
        "record_count": len(records),
        "normalization_version": import_format,
        "metadata": {
            "import_format": import_format,
        },
        "records": records,
    }
    payload["content_sha256"] = canonical_content_sha256(payload)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def create_external_scheme() -> ExternalSchemeRecord:
    dataset = ExternalSchemeDataset.objects.create(
        dataset_key="existing-external-schemes",
        dataset_name="Existing external schemes",
        source_filename="schemes.json",
        source_row_count=1,
        record_count=1,
        normalization_version="v1",
        content_sha256="1" * 64,
    )
    return ExternalSchemeRecord.objects.create(
        dataset=dataset,
        external_id="EXT001",
        scheme_name="Example Scheme",
        normalized_name="example scheme",
        record_sha256="2" * 64,
    )


def test_capital_import_creates_staging_and_links_external_scheme(
    tmp_path,
):
    path = tmp_path / "capital.json"
    external_scheme = create_external_scheme()
    canonical_count = Scheme.objects.count()
    candidate_count = SchemeCandidate.objects.count()
    write_dataset(
        path,
        import_format=CAPITAL_FORMAT,
        records=[capital_record()],
    )

    call_command("import_external_knowledge", str(path))

    dataset = ExternalKnowledgeDataset.objects.get(
        dataset_key=f"test-{CAPITAL_FORMAT}",
    )
    record = dataset.capital_support_records.get(
        external_id="CAP001",
    )

    assert dataset.dataset_kind == (
        ExternalKnowledgeDataset.DatasetKind.CAPITAL_SUPPORT
    )
    assert record.review_status == "needs_review"
    assert record.minimum_amount == 100000
    assert record.maximum_amount == 500000
    assert record.source_priority_score == 10
    assert record.matched_external_schemes.get() == external_scheme
    assert record.matched_scheme is None
    assert Scheme.objects.count() == canonical_count
    assert SchemeCandidate.objects.count() == candidate_count


def test_certification_import_quarantines_rejected_rows(tmp_path):
    path = tmp_path / "certifications.json"
    write_dataset(
        path,
        import_format=CERTIFICATION_FORMAT,
        records=[
            certification_record(
                external_id="CERT001",
                display_eligible=True,
                review_status="needs_review",
            ),
            certification_record(
                external_id="CERT011",
                display_eligible=False,
                review_status="rejected",
            ),
        ],
    )

    call_command("import_external_knowledge", str(path))

    records = ExternalCertificationRequirementRecord.objects
    visible = records.get(external_id="CERT001")
    quarantined = records.get(external_id="CERT011")

    assert visible.display_eligible is True
    assert visible.review_status == "needs_review"
    assert quarantined.display_eligible is False
    assert quarantined.review_status == "rejected"


def test_reimport_is_idempotent_preserves_review_and_removes_stale(
    tmp_path,
):
    path = tmp_path / "capital.json"
    first = capital_record("CAP001")
    second = capital_record("CAP002")
    write_dataset(
        path,
        import_format=CAPITAL_FORMAT,
        records=[first, second],
    )

    call_command("import_external_knowledge", str(path))
    call_command("import_external_knowledge", str(path))

    assert ExternalCapitalSupportRecord.objects.count() == 2

    record = ExternalCapitalSupportRecord.objects.get(
        external_id="CAP001",
    )
    record.review_status = "verified"
    record.review_notes = "Reviewed manually."
    record.save(
        update_fields=[
            "review_status",
            "review_notes",
            "updated_at",
        ],
    )

    updated = deepcopy(first)
    updated["support_name"] = "Updated Startup Loan Support"
    write_dataset(
        path,
        import_format=CAPITAL_FORMAT,
        records=[updated],
    )
    call_command("import_external_knowledge", str(path))

    record.refresh_from_db()
    assert record.support_name == "Updated Startup Loan Support"
    assert record.review_status == "verified"
    assert record.review_notes == "Reviewed manually."
    assert not ExternalCapitalSupportRecord.objects.filter(
        external_id="CAP002",
    ).exists()


def test_import_rejects_invalid_hash(tmp_path):
    path = tmp_path / "capital.json"
    payload = write_dataset(
        path,
        import_format=CAPITAL_FORMAT,
        records=[capital_record()],
    )
    payload["content_sha256"] = "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CommandError, match="canonical content hash"):
        call_command("import_external_knowledge", str(path))

    assert ExternalKnowledgeDataset.objects.count() == 0
    assert ExternalCapitalSupportRecord.objects.count() == 0
