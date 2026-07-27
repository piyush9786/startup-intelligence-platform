from __future__ import annotations

import csv

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.companies.models import (
    Company,
    CompanyDataSource,
    CompanyMetric,
    CompanyOutcome,
    CompanySourceRecord,
    RawCompanyDataset,
    normalize_company_name,
)
from apps.companies.services.csv_importer import CompanyCSVError, read_company_csv

pytestmark = pytest.mark.django_db

FIELDNAMES = [
    "external_id",
    "canonical_name",
    "aliases",
    "industry",
    "sub_industry",
    "business_model",
    "customer_segment",
    "country",
    "state",
    "city",
    "founded_year",
    "website",
    "operating_status",
    "verification_status",
    "source_record_url",
    "confidence_score",
    "outcome_date",
    "outcome_reason",
    "evidence_url",
    "metric_name",
    "metric_value",
    "metric_unit",
    "observation_date",
]


def write_rows(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def company_row(**overrides):
    row = {
        "external_id": "source-001",
        "canonical_name": "Example Cloud Private Limited",
        "aliases": "Example Cloud|ExampleCloud",
        "industry": "B2B SaaS",
        "sub_industry": "Workflow automation",
        "business_model": "subscription",
        "customer_segment": "SMB",
        "country": "India",
        "state": "Karnataka",
        "city": "Bengaluru",
        "founded_year": "2020",
        "website": "https://example.invalid",
        "operating_status": "active",
        "verification_status": "partially_verified",
        "source_record_url": "https://data.example.invalid/company/source-001",
        "confidence_score": "0.750",
        "outcome_date": "2026-07-01",
        "outcome_reason": "Latest source observation",
        "evidence_url": "https://data.example.invalid/company/source-001",
        "metric_name": "employee_count",
        "metric_value": "42",
        "metric_unit": "people",
        "observation_date": "2025-12-31",
    }
    row.update(overrides)
    return row


def run_import(path):
    call_command(
        "import_companies",
        file=str(path),
        source_slug="test-company-source",
        source_name="Test Company Source",
        source_type="public_dataset",
        source_url="https://data.example.invalid",
        licence="test-only",
        reliability_score="0.750",
        skip_storage_upload=True,
    )


def test_normalizes_common_legal_suffixes():
    assert normalize_company_name("ABC Technologies Pvt. Ltd.") == "abc technologies"
    assert normalize_company_name("ABC Technologies & Company") == (
        "abc technologies and company"
    )
    assert normalize_company_name("आरोग्य टेक प्राइवेट लिमिटेड") == (
        "आरोग्य टेक प्राइवेट लिमिटेड"
    )


def test_csv_reader_enforces_configured_row_limit(tmp_path):
    path = tmp_path / "too-many.csv"
    write_rows(
        path,
        [
            company_row(external_id="source-001"),
            company_row(external_id="source-002"),
        ],
    )

    with pytest.raises(CompanyCSVError, match="maximum of 1"):
        read_company_csv(path, max_rows=1)


def test_company_csv_import_is_idempotent(tmp_path):
    path = tmp_path / "companies.csv"
    write_rows(path, [company_row()])

    run_import(path)
    run_import(path)

    assert CompanyDataSource.objects.count() == 1
    assert RawCompanyDataset.objects.count() == 1
    assert Company.objects.count() == 1
    assert CompanySourceRecord.objects.count() == 1
    assert CompanyMetric.objects.count() == 1
    assert CompanyOutcome.objects.count() == 1

    company = Company.objects.get()
    assert company.normalized_name == "example cloud"
    assert set(company.aliases.values_list("normalized_alias", flat=True)) == {
        "example cloud",
        "examplecloud",
    }
    dataset = RawCompanyDataset.objects.get()
    assert dataset.parsing_status == RawCompanyDataset.ParsingStatus.PROCESSED
    assert dataset.storage_path.startswith("file://")
    assert dataset.accepted_count == 1


def test_new_observation_file_preserves_metric_history(tmp_path):
    first = tmp_path / "companies-2024.csv"
    second = tmp_path / "companies-2025.csv"
    write_rows(first, [company_row(metric_value="35", observation_date="2024-12-31")])
    write_rows(second, [company_row(metric_value="42", observation_date="2025-12-31")])

    run_import(first)
    run_import(second)

    assert Company.objects.count() == 1
    assert RawCompanyDataset.objects.count() == 2
    assert list(
        CompanyMetric.objects.order_by("observation_date").values_list(
            "metric_value", flat=True
        )
    ) == [35, 42]


def test_exact_identity_is_resolved_across_sources(tmp_path):
    first = tmp_path / "source-one.csv"
    second = tmp_path / "source-two.csv"
    write_rows(first, [company_row()])
    write_rows(
        second,
        [
            company_row(
                external_id="other-source-991",
                canonical_name="Example Cloud Pvt Ltd",
            )
        ],
    )

    run_import(first)
    call_command(
        "import_companies",
        file=str(second),
        source_slug="other-company-source",
        source_name="Other Company Source",
        source_type="public_dataset",
        reliability_score="0.800",
        skip_storage_upload=True,
    )

    assert Company.objects.count() == 1
    assert CompanySourceRecord.objects.count() == 2
    assert Company.objects.get().aliases.filter(
        alias="Example Cloud Pvt Ltd",
    ).exists()


def test_invalid_metric_row_is_registered_as_failed_without_company_writes(tmp_path):
    path = tmp_path / "invalid.csv"
    write_rows(path, [company_row(metric_value="", observation_date="")])

    with pytest.raises(CommandError, match="partial metric observation"):
        run_import(path)

    assert Company.objects.count() == 0
    dataset = RawCompanyDataset.objects.get()
    assert dataset.parsing_status == RawCompanyDataset.ParsingStatus.FAILED
    assert "partial metric observation" in dataset.error_message
