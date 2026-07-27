from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from apps.companies.models import (
    Company,
    CompanyAlias,
    CompanyDataSource,
    CompanyMetric,
    CompanyOutcome,
    CompanySourceRecord,
    RawCompanyDataset,
    normalize_company_name,
)

REQUIRED_COLUMNS = {
    "external_id",
    "canonical_name",
    "industry",
    "business_model",
    "country",
    "operating_status",
    "confidence_score",
}
METRIC_COLUMNS = {"metric_name", "metric_value", "metric_unit", "observation_date"}


class CompanyCSVError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedCompanyRow:
    row_number: int
    raw_data: dict[str, str]
    external_id: str
    canonical_name: str
    industry: str
    sub_industry: str
    business_model: str
    customer_segment: str
    country: str
    state: str
    city: str
    founded_year: int | None
    website: str
    operating_status: str
    verification_status: str
    aliases: tuple[str, ...]
    source_record_url: str
    confidence_score: Decimal
    outcome_date: date | None
    outcome_reason: str
    evidence_url: str
    metric_name: str
    metric_value: Decimal | None
    metric_unit: str
    observation_date: date | None


@dataclass(frozen=True)
class ImportResult:
    dataset: RawCompanyDataset
    companies_created: int
    companies_updated: int
    metrics_created: int
    outcomes_created: int


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_decimal(
    value: str,
    *,
    field_name: str,
    row_number: int,
    required: bool = True,
) -> Decimal | None:
    value = value.strip()
    if not value and not required:
        return None
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise CompanyCSVError(
            f"row {row_number}: {field_name} must be a decimal"
        ) from exc


def _parse_date(
    value: str,
    *,
    field_name: str,
    row_number: int,
) -> date | None:
    value = value.strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise CompanyCSVError(
            f"row {row_number}: {field_name} must use YYYY-MM-DD"
        ) from exc


def _parse_year(value: str, row_number: int) -> int | None:
    value = value.strip()
    if not value:
        return None
    try:
        year = int(value)
    except ValueError as exc:
        raise CompanyCSVError(f"row {row_number}: founded_year must be an integer") from exc
    if year < 1800 or year > timezone.now().year:
        raise CompanyCSVError(
            f"row {row_number}: founded_year must be between 1800 and {timezone.now().year}"
        )
    return year


def read_company_csv(
    path: Path,
    *,
    max_rows: int | None = None,
) -> list[ParsedCompanyRow]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise CompanyCSVError(f"CSV is missing required columns: {sorted(missing)}")

        rows = []
        for row_number, row in enumerate(reader, start=2):
            if max_rows is not None and len(rows) >= max_rows:
                raise CompanyCSVError(
                    f"CSV exceeds the maximum of {max_rows} company rows"
                )
            rows.append(_parse_row(row, row_number))

    if not rows:
        raise CompanyCSVError("CSV contains no company rows")
    _validate_repeated_external_ids(rows)
    return rows


def _parse_row(row: dict[str, str], row_number: int) -> ParsedCompanyRow:
    raw = {key: (value or "").strip() for key, value in row.items() if key is not None}
    for field in REQUIRED_COLUMNS - {"confidence_score"}:
        if not raw.get(field):
            raise CompanyCSVError(f"row {row_number}: {field} is required")

    confidence = _parse_decimal(
        raw.get("confidence_score", ""),
        field_name="confidence_score",
        row_number=row_number,
    )
    if confidence is None or not Decimal("0") <= confidence <= Decimal("1"):
        raise CompanyCSVError(f"row {row_number}: confidence_score must be between 0 and 1")

    operating_status = raw["operating_status"].lower()
    valid_statuses = {value for value, _ in Company.OperatingStatus.choices}
    if operating_status not in valid_statuses:
        raise CompanyCSVError(
            f"row {row_number}: unsupported operating_status {operating_status!r}"
        )

    verification_status = raw.get(
        "verification_status", Company.VerificationStatus.UNVERIFIED
    ).lower()
    valid_verification = {value for value, _ in Company.VerificationStatus.choices}
    if verification_status not in valid_verification:
        raise CompanyCSVError(
            f"row {row_number}: unsupported verification_status {verification_status!r}"
        )

    metric_values = {field: raw.get(field, "") for field in METRIC_COLUMNS}
    has_any_metric = any(metric_values.values())
    if has_any_metric and not all(metric_values.values()):
        missing_metric = sorted(field for field, value in metric_values.items() if not value)
        raise CompanyCSVError(
            f"row {row_number}: partial metric observation; missing {missing_metric}"
        )

    metric_name = metric_values["metric_name"].lower()
    metric_value = None
    observation_date = None
    if has_any_metric:
        valid_metrics = {value for value, _ in CompanyMetric.MetricName.choices}
        if metric_name not in valid_metrics:
            raise CompanyCSVError(
                f"row {row_number}: unsupported metric_name {metric_name!r}"
            )
        metric_value = _parse_decimal(
            metric_values["metric_value"],
            field_name="metric_value",
            row_number=row_number,
        )
        observation_date = _parse_date(
            metric_values["observation_date"],
            field_name="observation_date",
            row_number=row_number,
        )

    return ParsedCompanyRow(
        row_number=row_number,
        raw_data=raw,
        external_id=raw["external_id"],
        canonical_name=raw["canonical_name"],
        industry=raw["industry"],
        sub_industry=raw.get("sub_industry", ""),
        business_model=raw["business_model"],
        customer_segment=raw.get("customer_segment", ""),
        country=raw["country"],
        state=raw.get("state", ""),
        city=raw.get("city", ""),
        founded_year=_parse_year(raw.get("founded_year", ""), row_number),
        website=raw.get("website", ""),
        operating_status=operating_status,
        verification_status=verification_status,
        aliases=tuple(
            alias.strip() for alias in raw.get("aliases", "").split("|") if alias.strip()
        ),
        source_record_url=raw.get("source_record_url", ""),
        confidence_score=confidence,
        outcome_date=_parse_date(
            raw.get("outcome_date", ""),
            field_name="outcome_date",
            row_number=row_number,
        ),
        outcome_reason=raw.get("outcome_reason", ""),
        evidence_url=raw.get("evidence_url", ""),
        metric_name=metric_name,
        metric_value=metric_value,
        metric_unit=metric_values["metric_unit"],
        observation_date=observation_date,
    )


def _validate_repeated_external_ids(rows: list[ParsedCompanyRow]) -> None:
    identities: dict[str, tuple[str, str, str]] = {}
    for row in rows:
        identity = (row.canonical_name.casefold(), row.country.casefold(), str(row.founded_year))
        existing = identities.setdefault(row.external_id, identity)
        if existing != identity:
            raise CompanyCSVError(
                f"row {row.row_number}: external_id {row.external_id!r} has "
                "conflicting company identity fields"
            )


def _identity_candidates(row: ParsedCompanyRow):
    queryset = Company.objects.filter(
        country__iexact=row.country,
    )
    if row.founded_year is None:
        queryset = queryset.filter(founded_year__isnull=True)
    else:
        queryset = queryset.filter(founded_year=row.founded_year)
    return queryset


def _resolve_company(row: ParsedCompanyRow) -> Company | None:
    """Resolve only high-confidence exact identities across data sources."""
    normalized_names = {
        normalize_company_name(name)
        for name in (row.canonical_name, *row.aliases)
        if normalize_company_name(name)
    }
    candidates = list(
        _identity_candidates(row)
        .select_for_update()
        .filter(normalized_name__in=normalized_names)
        .order_by("id")[:2]
    )
    if not candidates:
        candidate_ids = list(
            _identity_candidates(row)
            .filter(aliases__normalized_alias__in=normalized_names)
            .values_list("id", flat=True)
            .distinct()[:2]
        )
        candidates = list(
            Company.objects.select_for_update()
            .filter(id__in=candidate_ids)
            .order_by("id")[:2]
        )
    if len(candidates) > 1:
        raise CompanyCSVError(
            f"row {row.row_number}: company identity is ambiguous; "
            "review the matching canonical names and aliases"
        )
    return candidates[0] if candidates else None


def import_company_rows(
    *,
    source: CompanyDataSource,
    dataset: RawCompanyDataset,
    rows: list[ParsedCompanyRow],
) -> ImportResult:
    companies_created = 0
    companies_updated = 0
    metrics_created = 0
    outcomes_created = 0

    with transaction.atomic():
        for row in rows:
            source_record = CompanySourceRecord.objects.select_related("company").filter(
                source=source,
                external_id=row.external_id,
            ).first()
            company_defaults = {
                "canonical_name": row.canonical_name,
                "industry": row.industry,
                "sub_industry": row.sub_industry,
                "business_model": row.business_model,
                "customer_segment": row.customer_segment,
                "country": row.country,
                "state": row.state,
                "city": row.city,
                "founded_year": row.founded_year,
                "website": row.website,
                "operating_status": row.operating_status,
                "verification_status": row.verification_status,
            }
            if source_record is None:
                company = _resolve_company(row)
                if company is None:
                    company = Company.objects.create(**company_defaults)
                    companies_created += 1
                else:
                    companies_updated += 1
                source_record = CompanySourceRecord(
                    company=company,
                    source=source,
                    external_id=row.external_id,
                )
            else:
                company = source_record.company
                for field, value in company_defaults.items():
                    setattr(company, field, value)
                company.save()
                companies_updated += 1

            source_record.latest_dataset = dataset
            source_record.source_record_url = row.source_record_url
            source_record.confidence_score = row.confidence_score
            source_record.raw_data = row.raw_data
            source_record.save()

            # Process the source's canonical name last so it wins when an
            # alias normalizes to the same identity within that source.
            for alias in (*row.aliases, row.canonical_name):
                CompanyAlias.objects.update_or_create(
                    company=company,
                    source=source,
                    normalized_alias=normalize_company_name(alias),
                    defaults={"alias": alias},
                )

            if row.metric_name:
                _, created = CompanyMetric.objects.update_or_create(
                    company=company,
                    source=source,
                    metric_name=row.metric_name,
                    observation_date=row.observation_date,
                    metric_unit=row.metric_unit,
                    defaults={
                        "dataset": dataset,
                        "metric_value": row.metric_value,
                        "confidence_score": row.confidence_score,
                    },
                )
                metrics_created += int(created)

            _, created = CompanyOutcome.objects.update_or_create(
                company=company,
                source=source,
                outcome_type=row.operating_status,
                outcome_date=row.outcome_date,
                defaults={
                    "dataset": dataset,
                    "reason": row.outcome_reason,
                    "evidence_url": row.evidence_url,
                    "confidence_score": row.confidence_score,
                },
            )
            outcomes_created += int(created)

        dataset.parsing_status = RawCompanyDataset.ParsingStatus.PROCESSED
        dataset.row_count = len(rows)
        dataset.accepted_count = len(rows)
        dataset.rejected_count = 0
        dataset.error_message = ""
        dataset.save(
            update_fields=[
                "parsing_status",
                "row_count",
                "accepted_count",
                "rejected_count",
                "error_message",
                "updated_at",
            ]
        )

    return ImportResult(
        dataset=dataset,
        companies_created=companies_created,
        companies_updated=companies_updated,
        metrics_created=metrics_created,
        outcomes_created=outcomes_created,
    )
