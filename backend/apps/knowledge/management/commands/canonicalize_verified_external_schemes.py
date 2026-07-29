"""Publish reviewer-verified external schemes into the canonical catalog.

The external review manifest is the verification authority for these records.
This command does not independently re-verify web content. It converts only
records already marked VERIFIED, preserves their proof metadata, links each
external record to its canonical Scheme, and creates a VERIFIED SchemeVersion.
"""
from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal
from typing import Any
from urllib.parse import urlparse

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.knowledge.models import ExternalSchemeRecord
from apps.schemes.models import Authority, EligibilityRule, Scheme, SchemeVersion
from apps.sources.models import Source, SourceDocument

EXTRACTOR_VERSION = "external-review-canonicalizer-v1"

_STAGE_MAP = {
    "idea": "idea",
    "ideation": "idea",
    "validation": "validation",
    "prototype": "prototype",
    "mvp": "mvp",
    "pilot": "pilot",
    "early revenue": "early_revenue",
    "growth": "growth",
    "scale": "expansion",
    "expansion": "expansion",
}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _unique_text(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean(value)
        key = text.casefold()
        if text and key not in seen:
            result.append(text)
            seen.add(key)
    return result


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _domain(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise CommandError(f"Verified record requires an official HTTPS URL: {url!r}")
    return parsed.hostname.lower().removeprefix("www.")


def _authority_name(record: ExternalSchemeRecord) -> str:
    return (
        _clean(record.department)
        or _clean(record.ministry)
        or _clean(record.source_portal)
        or "Government of India"
    )[:255]


def _short_name(title: str) -> str:
    matches = re.findall(r"\(([^()]*)\)", title)
    if matches:
        acronym = matches[-1].strip()
        if acronym and len(acronym) <= 150:
            return acronym
    words = re.findall(r"[A-Za-z0-9]+", title)
    generated = "".join(word[0].upper() for word in words if word)
    return (generated or title)[:150]


def _normalized_stages(values: list[Any]) -> list[str]:
    stages: list[str] = []
    for value in values:
        normalized = _clean(value).casefold()
        if normalized in {"", "any", "all", "all stages"}:
            continue
        stage = _STAGE_MAP.get(normalized)
        if stage and stage not in stages:
            stages.append(stage)
    return stages


def _amount_bounds(text: str) -> tuple[Decimal | None, Decimal | None]:
    """Extract only explicit INR/lakh/crore amounts from a funding field."""
    values: list[Decimal] = []
    for number, unit in re.findall(
        r"(?:₹|INR|Rs\.?|Rupees)?\s*([0-9]+(?:\.[0-9]+)?)\s*"
        r"(thousand|lakh|lac|crore)?",
        text,
        flags=re.IGNORECASE,
    ):
        if not unit and not re.search(r"(?:₹|INR|Rs\.?|Rupees)", text, re.I):
            continue
        amount = Decimal(number)
        multiplier = {
            "thousand": Decimal("1000"),
            "lakh": Decimal("100000"),
            "lac": Decimal("100000"),
            "crore": Decimal("10000000"),
        }.get(unit.casefold(), Decimal("1"))
        values.append(amount * multiplier)
    if not values:
        return None, None
    return min(values), max(values)


def _record_payload(record: ExternalSchemeRecord) -> dict[str, Any]:
    return {
        "dataset_key": record.dataset.dataset_key,
        "external_id": record.external_id,
        "scheme_name": record.scheme_name,
        "normalized_name": record.normalized_name,
        "ministry": record.ministry,
        "department": record.department,
        "sector": record.sector,
        "startup_stage": record.startup_stage,
        "startup_type": record.startup_type,
        "industry": record.industry,
        "central_state": record.central_state,
        "state": record.state,
        "funding_type": record.funding_type,
        "funding_amount": record.funding_amount,
        "financial_instrument": record.financial_instrument,
        "eligibility": record.eligibility,
        "women_eligible": record.women_eligible,
        "sc_st_eligible": record.sc_st_eligible,
        "dpiit_required": record.dpiit_required,
        "startup_age_limit": record.startup_age_limit,
        "revenue_criteria": record.revenue_criteria,
        "tax_benefits": record.tax_benefits,
        "documents_required": record.documents_required,
        "application_process": record.application_process,
        "official_website_label": record.official_website_label,
        "official_application_url": record.official_application_url,
        "source_portal": record.source_portal,
        "claimed_last_updated": record.claimed_last_updated,
        "source_row_number": record.source_row_number,
        "source_rows": record.source_rows,
        "external_ids": record.external_ids,
        "record_sha256": record.record_sha256,
        "review_status": record.review_status,
        "review_notes": record.review_notes,
        "quality_warnings": record.quality_warnings,
        "raw_row": record.raw_row,
    }


def _source_for_record(record: ExternalSchemeRecord, official_url: str) -> Source:
    domain = _domain(official_url)
    authority_name = _authority_name(record)
    source, _ = Source.objects.get_or_create(
        official_domain=domain,
        defaults={
            "name": _clean(record.source_portal) or authority_name,
            "category": "reviewer_verified_external_scheme",
            "ministry": _clean(record.ministry)[:255],
            "department": _clean(record.department)[:255],
            "state": "" if _clean(record.state).casefold() == "all india" else _clean(record.state)[:100],
            "allowed_domains": [domain],
            "listing_url": official_url,
            "authority_tier": Source.AuthorityTier.OFFICIAL_PROGRAMME,
            "crawl_frequency": Source.CrawlFrequency.MANUAL,
            "language": "en",
            "active": True,
            "respect_robots_txt": True,
            "notes": "Official source cited by the external scheme review manifest.",
        },
    )

    changed: list[str] = []
    if not source.active:
        source.active = True
        changed.append("active")
    if domain not in (source.allowed_domains or []):
        source.allowed_domains = _unique_text([*(source.allowed_domains or []), domain])
        changed.append("allowed_domains")
    if changed:
        source.save(update_fields=[*changed, "updated_at"])
    return source


def _proof_document(
    record: ExternalSchemeRecord,
    source: Source,
    official_url: str,
) -> SourceDocument:
    document = (
        SourceDocument.objects.select_for_update()
        .filter(source_url=official_url, extractor_version=EXTRACTOR_VERSION)
        .order_by("-version_number")
        .first()
    )
    if document is None:
        next_version = (
            SourceDocument.objects.filter(source_url=official_url).aggregate(
                maximum=Max("version_number")
            )["maximum"]
            or 0
        ) + 1
        document = SourceDocument.objects.create(
            source=source,
            source_url=official_url,
            final_url=official_url,
            title=(
                _clean(record.official_website_label)
                or f"Verified external scheme evidence — {source.name}"
            )[:500],
            mime_type="application/json",
            content_hash="0" * 64,
            version_number=next_version,
            is_current=True,
            retrieved_at=record.updated_at or timezone.now(),
            http_status=200,
            content_length=0,
            status=SourceDocument.Status.VERIFIED,
            extractor_version=EXTRACTOR_VERSION,
            metadata={
                "proof_origin": "external_scheme_review_manifest",
                "independent_live_crawl": False,
                "external_scheme_reviews": [],
            },
        )

    metadata = dict(document.metadata or {})
    proofs = [
        item
        for item in metadata.get("external_scheme_reviews", [])
        if isinstance(item, dict) and item.get("external_id") != record.external_id
    ]
    proofs.append(
        {
            "dataset_key": record.dataset.dataset_key,
            "external_id": record.external_id,
            "record_sha256": record.record_sha256,
            "source_row_number": record.source_row_number,
            "source_rows": record.source_rows,
            "external_ids": record.external_ids,
            "review_status": record.review_status,
            "review_notes": record.review_notes,
            "quality_warnings": record.quality_warnings,
            "raw_row": record.raw_row,
            "scheme_name": record.scheme_name,
        }
    )
    proofs.sort(key=lambda item: (item.get("dataset_key", ""), item.get("external_id", "")))
    metadata.update(
        {
            "proof_origin": "external_scheme_review_manifest",
            "independent_live_crawl": False,
            "external_scheme_reviews": proofs,
        }
    )

    document.source = source
    document.final_url = official_url
    document.content_hash = _sha256({"official_url": official_url, "proofs": proofs})
    document.status = SourceDocument.Status.VERIFIED
    document.retrieved_at = max(document.retrieved_at, record.updated_at or timezone.now())
    document.metadata = metadata
    document.save(
        update_fields=[
            "source",
            "final_url",
            "content_hash",
            "status",
            "retrieved_at",
            "metadata",
            "updated_at",
        ]
    )
    return document


def _authority_for_record(record: ExternalSchemeRecord, official_url: str) -> Authority:
    name = _authority_name(record)
    authority, created = Authority.objects.get_or_create(
        name=name,
        defaults={
            "authority_type": "government_programme",
            "ministry": _clean(record.ministry)[:255],
            "department": _clean(record.department)[:255],
            "state": "" if _clean(record.state).casefold() == "all india" else _clean(record.state)[:100],
            "official_url": official_url[:1000],
        },
    )
    if not created:
        changed: list[str] = []
        for field_name, value in {
            "ministry": _clean(record.ministry)[:255],
            "department": _clean(record.department)[:255],
            "official_url": official_url[:1000],
        }.items():
            if value and not getattr(authority, field_name):
                setattr(authority, field_name, value)
                changed.append(field_name)
        if changed:
            authority.save(update_fields=[*changed, "updated_at"])
    return authority


def _canonical_fields(record: ExternalSchemeRecord) -> dict[str, Any]:
    funding_amount = _clean(record.funding_amount)
    minimum_amount, maximum_amount = _amount_bounds(funding_amount)
    support_types = _unique_text([record.funding_type, record.financial_instrument])
    categories = _unique_text([record.sector, record.startup_type, record.central_state])
    sectors = [
        value
        for value in _unique_text([record.sector, *(record.industry or [])])
        if value.casefold() not in {"all", "all industries", "all sectors"}
    ]
    state = _clean(record.state)
    states = [] if state.casefold() in {"", "all india", "pan india", "all"} else [state]
    stages = _normalized_stages(list(record.startup_stage or []))

    eligibility_parts = _unique_text(
        [
            record.eligibility,
            f"Startup age: {record.startup_age_limit}" if _clean(record.startup_age_limit) else "",
            f"Revenue criteria: {record.revenue_criteria}" if _clean(record.revenue_criteria) else "",
            f"DPIIT requirement: {record.dpiit_required}" if _clean(record.dpiit_required) else "",
        ]
    )
    description = "\n\n".join(
        _unique_text(
            [
                record.eligibility,
                funding_amount,
                record.tax_benefits,
                record.application_process,
            ]
        )
    )
    benefits = []
    if funding_amount or support_types:
        benefits.append(
            {
                "type": support_types[0] if support_types else "support",
                "description": funding_amount or ", ".join(support_types),
                "amount_min": str(minimum_amount) if minimum_amount is not None else None,
                "amount_max": str(maximum_amount) if maximum_amount is not None else None,
                "currency": "INR",
            }
        )
    if _clean(record.tax_benefits):
        benefits.append({"type": "tax_benefit", "description": _clean(record.tax_benefits)})

    application_steps = []
    if _clean(record.application_process):
        application_steps.append(
            {
                "step_number": 1,
                "instruction": _clean(record.application_process),
                "url": _clean(record.official_application_url),
            }
        )

    return {
        "description": description,
        "objective": _clean(record.eligibility),
        "support_types": support_types,
        "categories": categories,
        "eligible_sectors": sectors,
        "eligible_stages": stages,
        "eligible_states": states,
        "founder_categories": [],
        "minimum_amount": minimum_amount,
        "maximum_amount": maximum_amount,
        "currency": "INR",
        "equity_required": True if any("equity" in value.casefold() for value in support_types) else None,
        "application_status": SchemeVersion.ApplicationStatus.UNKNOWN,
        "official_url": _clean(record.official_application_url),
        "application_url": _clean(record.official_application_url),
        "required_documents": list(record.documents_required or []),
        "application_steps": application_steps,
        "benefits": benefits,
        "restrictions": eligibility_parts,
    }


def _sync_rules(version: SchemeVersion, record: ExternalSchemeRecord) -> int:
    rules: list[dict[str, Any]] = []
    evidence = _clean(record.eligibility) or record.scheme_name
    if _clean(record.dpiit_required).casefold() == "yes":
        rules.append(
            {
                "field_path": "dpiit_recognized",
                "operator": EligibilityRule.Operator.EQUALS,
                "expected_value": True,
                "evidence_text": evidence,
            }
        )
    stages = _normalized_stages(list(record.startup_stage or []))
    if stages:
        rules.append(
            {
                "field_path": "stage",
                "operator": EligibilityRule.Operator.IN,
                "expected_value": stages,
                "evidence_text": "Eligible startup stages: " + ", ".join(record.startup_stage or []),
            }
        )

    expected = {row["field_path"] for row in rules}
    EligibilityRule.objects.filter(
        scheme_version=version,
        rule_group="external_review",
        manually_verified=True,
    ).exclude(field_path__in=expected).delete()

    for row in rules:
        EligibilityRule.objects.update_or_create(
            scheme_version=version,
            field_path=row["field_path"],
            rule_group="external_review",
            defaults={
                "operator": row["operator"],
                "expected_value": row["expected_value"],
                "mandatory": True,
                "evidence_text": row["evidence_text"],
                "evidence_page": None,
                "extraction_confidence": Decimal("1.0000"),
                "manually_verified": True,
            },
        )
    return len(rules)


@transaction.atomic
def canonicalize_verified_external_schemes(*, dry_run: bool = False) -> dict[str, int]:
    records = list(
        ExternalSchemeRecord.objects.select_for_update(of=("self",))
        .select_related("dataset")
        .filter(
            dataset__is_active=True,
            review_status=ExternalSchemeRecord.ReviewStatus.VERIFIED,
            matched_scheme__isnull=True,
        )
        .order_by("dataset__dataset_key", "external_id")
    )

    counts = {
        "eligible_records": len(records),
        "schemes_created": 0,
        "versions_created": 0,
        "records_linked": 0,
        "rules_synced": 0,
    }

    for record in records:
        title = _clean(record.scheme_name)
        official_url = _clean(record.official_application_url)
        if not title:
            raise CommandError(f"Verified record {record.external_id} has no scheme name.")
        _domain(official_url)
        if not _clean(record.review_notes):
            raise CommandError(
                f"Verified record {record.external_id} has no reviewer proof note."
            )

        authority = _authority_for_record(record, official_url)
        source = _source_for_record(record, official_url)
        source_document = _proof_document(record, source, official_url)

        scheme = Scheme.objects.filter(canonical_name__iexact=title).order_by("created_at").first()
        if scheme is None:
            scheme = Scheme.objects.create(
                canonical_name=title,
                short_name=_short_name(title),
                alternative_names=_unique_text([record.scheme_name]),
                authority=authority,
                lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
            )
            counts["schemes_created"] += 1
        else:
            changed: list[str] = []
            aliases = _unique_text([*(scheme.alternative_names or []), record.scheme_name])
            if aliases != (scheme.alternative_names or []):
                scheme.alternative_names = aliases
                changed.append("alternative_names")
            if scheme.lifecycle_status != Scheme.LifecycleStatus.ACTIVE:
                scheme.lifecycle_status = Scheme.LifecycleStatus.ACTIVE
                changed.append("lifecycle_status")
            if changed:
                scheme.save(update_fields=[*changed, "updated_at"])

        payload = _record_payload(record)
        version_hash = _sha256(
            {
                "canonicalizer": EXTRACTOR_VERSION,
                "scheme": title,
                "record": payload,
            }
        )
        version = SchemeVersion.objects.filter(
            scheme=scheme,
            content_hash=version_hash,
        ).first()
        fields = _canonical_fields(record)
        verified_at = record.updated_at or timezone.now()

        if version is None:
            next_version = (
                SchemeVersion.objects.filter(scheme=scheme).aggregate(
                    maximum=Max("version_number")
                )["maximum"]
                or 0
            ) + 1
            version = SchemeVersion.objects.create(
                scheme=scheme,
                version_number=next_version,
                source_document=source_document,
                captured_at=verified_at,
                content_hash=version_hash,
                verification_status=SchemeVersion.VerificationStatus.VERIFIED,
                extraction_confidence=Decimal("1.0000"),
                verified_at=verified_at,
                **fields,
            )
            counts["versions_created"] += 1
        else:
            for field_name, value in fields.items():
                setattr(version, field_name, value)
            version.source_document = source_document
            version.verification_status = SchemeVersion.VerificationStatus.VERIFIED
            version.extraction_confidence = Decimal("1.0000")
            version.verified_at = version.verified_at or verified_at
            version.save()

        counts["rules_synced"] += _sync_rules(version, record)

        if scheme.current_version_id != version.id:
            scheme.current_version = version
            scheme.lifecycle_status = Scheme.LifecycleStatus.ACTIVE
            scheme.save(update_fields=["current_version", "lifecycle_status", "updated_at"])

        record.matched_scheme = scheme
        record.save(update_fields=["matched_scheme", "updated_at"])
        counts["records_linked"] += 1

    if dry_run:
        transaction.set_rollback(True)
    return counts


class Command(BaseCommand):
    help = (
        "Convert already reviewer-verified, unmatched external scheme records "
        "into active canonical verified Scheme/SchemeVersion records."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and report changes, then roll the transaction back.",
        )
        parser.add_argument(
            "--expected-total",
            type=int,
            default=None,
            help="Require this many active canonical verified schemes after publication.",
        )

    def handle(self, *args, **options):
        counts = canonicalize_verified_external_schemes(dry_run=options["dry_run"])
        verified_total = Scheme.objects.filter(
            lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
            current_version__verification_status=SchemeVersion.VerificationStatus.VERIFIED,
        ).count()
        remaining = ExternalSchemeRecord.objects.filter(
            dataset__is_active=True,
            review_status=ExternalSchemeRecord.ReviewStatus.VERIFIED,
            matched_scheme__isnull=True,
        ).count()
        reported_total = (
            verified_total + counts["schemes_created"]
            if options["dry_run"]
            else verified_total
        )
        reported_remaining = (
            max(0, remaining - counts["records_linked"])
            if options["dry_run"]
            else remaining
        )

        if options["expected_total"] is not None and reported_total != options["expected_total"]:
            raise CommandError(
                f"Expected {options['expected_total']} active canonical verified schemes; "
                f"found/projected {reported_total}."
            )
        if reported_remaining:
            raise CommandError(
                f"Canonicalization left/projected {reported_remaining} verified external records unmatched."
            )

        prefix = "Dry run" if options["dry_run"] else "Canonicalization"
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix} complete: eligible={counts['eligible_records']}, "
                f"new_schemes={counts['schemes_created']}, "
                f"new_versions={counts['versions_created']}, "
                f"linked={counts['records_linked']}, "
                f"rules={counts['rules_synced']}, "
                f"canonical_verified={reported_total}, remaining_unmatched={reported_remaining}"
            )
        )
