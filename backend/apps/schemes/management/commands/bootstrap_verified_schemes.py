"""Bootstrap the small, reviewed canonical scheme catalog bundled with the project.

The repository contains two kinds of scheme data:

* large external discovery catalogs used for browsing and research; and
* reviewer-curated manifests used as the authoritative canonical catalog.

A fresh database previously imported only the external staging records.  The
founder dashboard and recommendation engine intentionally read canonical,
verified ``Scheme`` rows, so they stayed empty.  This command converts the
reviewed manifest content into idempotent canonical records while preserving
source provenance.
"""
from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.schemes.models import Authority, EligibilityRule, Scheme, SchemeVersion
from apps.sources.models import Source, SourceDocument

MANIFEST_DIR = (
    Path(settings.BASE_DIR)
    / "apps"
    / "knowledge"
    / "pilot"
    / "manifests"
    / "verified_catalog_v1"
)
RULES_MANIFEST = (
    Path(settings.BASE_DIR)
    / "apps"
    / "knowledge"
    / "pilot"
    / "manifests"
    / "verified_rules_v1"
    / "manifest_verified_executable_rules_pilot_v1.json"
)
EXTERNAL_DATASET = (
    Path(settings.BASE_DIR)
    / "apps"
    / "knowledge"
    / "datasets"
    / "external"
    / "startup_schemes_v1.json"
)
EXTERNAL_REVIEW_MANIFEST = (
    Path(settings.BASE_DIR)
    / "apps"
    / "knowledge"
    / "pilot"
    / "manifests"
    / "external_scheme_review_v1.json"
)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CommandError(f"Could not read bundled manifest: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CommandError(f"Bundled manifest is invalid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise CommandError(f"Bundled manifest root must be an object: {path}")
    return payload


def _domain(url: str) -> str:
    hostname = urlparse(url).hostname or ""
    return hostname.lower().removeprefix("www.")


def _content_hash(*parts: Any) -> str:
    payload = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _amount_bounds(benefits: list[dict[str, Any]]) -> tuple[Decimal | None, Decimal | None]:
    minima: list[Decimal] = []
    maxima: list[Decimal] = []
    for benefit in benefits:
        minimum = _decimal(benefit.get("amount_min"))
        maximum = _decimal(benefit.get("amount_max"))
        if minimum is not None:
            minima.append(minimum)
        if maximum is not None:
            maxima.append(maximum)
    return (min(minima) if minima else None, max(maxima) if maxima else None)


def _short_name(candidate: dict[str, Any], title: str) -> str:
    pilot_key = str(candidate.get("pilot_key") or "").strip()
    if pilot_key:
        return pilot_key.replace("_", "-").upper()[:150]
    return title[:150]


def _source_for_manifest(
    *,
    source_name: str,
    official_url: str,
    authority: dict[str, Any],
) -> Source:
    domain = _domain(official_url)
    if not domain:
        raise CommandError(f"Official URL has no hostname: {official_url}")

    source, _ = Source.objects.update_or_create(
        official_domain=domain,
        defaults={
            "name": source_name or authority["canonical_name"],
            "category": "verified_scheme_catalog",
            "ministry": str(authority.get("ministry") or ""),
            "department": str(authority.get("department") or ""),
            "state": str(authority.get("state") or ""),
            "allowed_domains": [domain],
            "listing_url": official_url,
            "authority_tier": Source.AuthorityTier.OFFICIAL_PROGRAMME,
            "crawl_frequency": Source.CrawlFrequency.MANUAL,
            "language": "en",
            "active": True,
            "respect_robots_txt": True,
            "notes": "Bundled reviewer-curated canonical scheme manifest.",
        },
    )
    return source


def _source_document(
    *,
    source: Source,
    title: str,
    official_url: str,
    content_hash: str,
    manifest_key: str,
) -> SourceDocument:
    document, _ = SourceDocument.objects.update_or_create(
        source_url=official_url,
        version_number=1,
        defaults={
            "source": source,
            "final_url": official_url,
            "title": title,
            "mime_type": "application/json",
            "content_hash": content_hash,
            "is_current": True,
            "retrieved_at": timezone.now(),
            "http_status": 200,
            "content_length": 0,
            "status": SourceDocument.Status.VERIFIED,
            "extractor_version": "bundled-reviewed-manifest-v1",
            "metadata": {
                "manifest_key": manifest_key,
                "bootstrap_origin": "reviewed_catalog",
            },
        },
    )
    return document


def _rules_by_pilot_key() -> dict[str, list[dict[str, Any]]]:
    if not RULES_MANIFEST.exists():
        return {}
    payload = _load_json(RULES_MANIFEST)
    result: dict[str, list[dict[str, Any]]] = {}
    for revision in payload.get("revisions") or []:
        key = str(revision.get("pilot_key") or "").strip()
        rules = revision.get("rules") or []
        if key and isinstance(rules, list):
            result[key] = [item for item in rules if isinstance(item, dict)]
    return result


def _sync_rules(version: SchemeVersion, rules: list[dict[str, Any]]) -> int:
    synced = 0
    expected_paths: set[str] = set()
    for rule in rules:
        field_path = str(rule.get("field_path") or "").strip()
        operator = str(rule.get("operator") or "").strip()
        evidence_text = str(rule.get("evidence_text") or "").strip()
        if not field_path or not operator or not evidence_text:
            continue
        expected_paths.add(field_path)
        record = (
            EligibilityRule.objects.filter(
                scheme_version=version,
                field_path=field_path,
            )
            .order_by("created_at", "id")
            .first()
        )
        values = {
            "operator": operator,
            "expected_value": rule.get("expected_value"),
            "mandatory": bool(rule.get("mandatory", True)),
            "rule_group": str(rule.get("evaluation_mode") or "verified"),
            "evidence_text": evidence_text,
            "evidence_page": rule.get("evidence_page"),
            "extraction_confidence": Decimal("1.0000"),
            "manually_verified": True,
        }
        if record is None:
            EligibilityRule.objects.create(
                scheme_version=version,
                field_path=field_path,
                **values,
            )
        else:
            for name, value in values.items():
                setattr(record, name, value)
            record.save()
            EligibilityRule.objects.filter(
                scheme_version=version,
                field_path=field_path,
            ).exclude(pk=record.pk).delete()
        synced += 1

    # Remove only rules previously created by this bootstrap that no longer
    # exist in the bundled rule manifest. Reviewer-created rules are retained.
    if expected_paths:
        EligibilityRule.objects.filter(
            scheme_version=version,
            manually_verified=True,
            extraction_confidence=Decimal("1.0000"),
        ).exclude(field_path__in=expected_paths).delete()
    return synced


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


def _normalized_stages(values: list[Any]) -> list[str]:
    stages: list[str] = []
    for value in values:
        normalized = str(value or "").strip().lower()
        stage = _STAGE_MAP.get(normalized)
        if stage and stage not in stages:
            stages.append(stage)
    return stages


def _amounts_from_text(value: Any) -> tuple[Decimal | None, Decimal | None]:
    text = str(value or "")
    amounts: list[Decimal] = []
    for number, unit in re.findall(
        r"(?:₹|INR)?\s*([0-9]+(?:\.[0-9]+)?)\s*(lakh|crore)?",
        text,
        flags=re.IGNORECASE,
    ):
        amount = Decimal(number)
        normalized_unit = unit.lower()
        if normalized_unit == "lakh":
            amount *= Decimal("100000")
        elif normalized_unit == "crore":
            amount *= Decimal("10000000")
        amounts.append(amount)
    if not amounts:
        return None, None
    return min(amounts), max(amounts)


def _bootstrap_external_review_matches(
    counts: dict[str, int],
) -> None:
    if not EXTERNAL_DATASET.exists() or not EXTERNAL_REVIEW_MANIFEST.exists():
        return

    dataset = _load_json(EXTERNAL_DATASET)
    review = _load_json(EXTERNAL_REVIEW_MANIFEST)
    records = {
        str(item.get("external_id") or ""): item
        for item in dataset.get("records") or []
        if isinstance(item, dict)
    }

    for decision in review.get("decisions") or []:
        if not isinstance(decision, dict):
            continue
        title = str(decision.get("matched_scheme_name") or "").strip()
        if not title:
            continue

        # The richer reviewer-curated manifests always win. This phase adds
        # only the canonical schemes that are represented solely in the
        # complete external review manifest.
        if Scheme.objects.filter(canonical_name=title).exists():
            continue

        external_id = str(decision.get("external_id") or "").strip()
        record = records.get(external_id)
        if not record:
            raise CommandError(
                f"Reviewed external scheme record is missing: {external_id}"
            )

        official_url = str(
            decision.get("official_source_url")
            or record.get("official_application_url")
            or ""
        ).strip()
        if not official_url:
            raise CommandError(
                f"Reviewed external scheme lacks official URL: {external_id}"
            )

        authority_name = str(
            record.get("department")
            or record.get("ministry")
            or record.get("source_portal")
            or "Government of India"
        ).strip()
        authority, authority_created = Authority.objects.update_or_create(
            name=authority_name,
            defaults={
                "authority_type": "central_government_programme",
                "ministry": str(record.get("ministry") or ""),
                "department": str(record.get("department") or ""),
                "state": (
                    ""
                    if str(record.get("state") or "").lower() == "all india"
                    else str(record.get("state") or "")
                ),
                "official_url": official_url,
            },
        )
        counts["authorities"] += int(authority_created)

        source = _source_for_manifest(
            source_name=str(record.get("source_portal") or authority_name),
            official_url=official_url,
            authority={
                "canonical_name": authority_name,
                "ministry": record.get("ministry") or "",
                "department": record.get("department") or "",
                "state": record.get("state") or "",
            },
        )
        record_hash = _content_hash(external_id, record, decision)
        document = _source_document(
            source=source,
            title=title,
            official_url=official_url,
            content_hash=record_hash,
            manifest_key=str(review.get("manifest_key") or "external-review"),
        )

        scheme, scheme_created = Scheme.objects.update_or_create(
            canonical_name=title,
            authority=authority,
            defaults={
                "short_name": title.split("(")[-1].rstrip(")")[:150],
                "alternative_names": [str(record.get("scheme_name") or title)],
                "lifecycle_status": Scheme.LifecycleStatus.ACTIVE,
            },
        )
        counts["schemes"] += int(scheme_created)

        minimum_amount, maximum_amount = _amounts_from_text(
            record.get("funding_amount")
        )
        support_types = [
            value
            for value in {
                str(record.get("funding_type") or "").strip(),
                str(record.get("financial_instrument") or "").strip(),
            }
            if value
        ]
        description = " ".join(
            value
            for value in [
                str(record.get("eligibility") or "").strip(),
                str(record.get("funding_amount") or "").strip(),
            ]
            if value
        )
        version_hash = _content_hash(title, record_hash, record)
        version = SchemeVersion.objects.filter(
            scheme=scheme,
            content_hash=version_hash,
        ).first()
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
                source_document=document,
                captured_at=timezone.now(),
                content_hash=version_hash,
                description=description,
                objective=str(record.get("eligibility") or ""),
                support_types=support_types,
                categories=[str(record.get("sector") or "Startup")],
                eligible_sectors=[
                    value
                    for value in (record.get("industry") or [])
                    if str(value).lower() not in {"all", "all industries"}
                ],
                eligible_stages=_normalized_stages(
                    list(record.get("startup_stage") or [])
                ),
                eligible_states=(
                    []
                    if str(record.get("state") or "").lower() == "all india"
                    else [str(record.get("state") or "")]
                ),
                minimum_amount=minimum_amount,
                maximum_amount=maximum_amount,
                currency="INR",
                equity_required=(
                    True
                    if any("equity" in value.lower() for value in support_types)
                    else None
                ),
                application_status=SchemeVersion.ApplicationStatus.UNKNOWN,
                official_url=official_url,
                application_url=str(
                    record.get("official_application_url") or official_url
                ),
                required_documents=list(
                    record.get("documents_required") or []
                ),
                application_steps=[
                    str(record.get("application_process") or "").strip()
                ],
                benefits=[
                    {
                        "type": str(record.get("funding_type") or "support"),
                        "description": str(record.get("funding_amount") or ""),
                    }
                ],
                restrictions=[],
                verification_status=(
                    SchemeVersion.VerificationStatus.VERIFIED
                ),
                extraction_confidence=Decimal("1.0000"),
                verified_at=timezone.now(),
            )
            counts["versions"] += 1

        if scheme.current_version_id != version.id:
            scheme.current_version = version
            scheme.lifecycle_status = Scheme.LifecycleStatus.ACTIVE
            scheme.save(
                update_fields=[
                    "current_version",
                    "lifecycle_status",
                    "updated_at",
                ]
            )

        generated_rules: list[dict[str, Any]] = []
        if str(record.get("dpiit_required") or "").lower() == "yes":
            generated_rules.append(
                {
                    "field_path": "dpiit_recognized",
                    "operator": EligibilityRule.Operator.EQUALS,
                    "expected_value": True,
                    "mandatory": True,
                    "evaluation_mode": "executable",
                    "evidence_text": str(record.get("eligibility") or title),
                }
            )
        stages = _normalized_stages(list(record.get("startup_stage") or []))
        if stages:
            generated_rules.append(
                {
                    "field_path": "stage",
                    "operator": EligibilityRule.Operator.IN,
                    "expected_value": stages,
                    "mandatory": True,
                    "evaluation_mode": "executable",
                    "evidence_text": (
                        "Eligible startup stages: "
                        + ", ".join(record.get("startup_stage") or [])
                    ),
                }
            )
        counts["rules"] += _sync_rules(version, generated_rules)


@transaction.atomic
def bootstrap_verified_catalog() -> dict[str, int]:
    manifests = sorted(MANIFEST_DIR.glob("manifest_*.json"))
    if not manifests:
        raise CommandError(f"No verified catalog manifests found in {MANIFEST_DIR}")

    rules_by_key = _rules_by_pilot_key()
    counts = {"authorities": 0, "schemes": 0, "versions": 0, "rules": 0}

    for path in manifests:
        payload = _load_json(path)
        authority_payload = payload.get("authority") or {}
        authority_name = str(authority_payload.get("canonical_name") or "").strip()
        if not authority_name:
            raise CommandError(f"Manifest lacks authority canonical_name: {path}")

        authority, created = Authority.objects.update_or_create(
            name=authority_name,
            defaults={
                "authority_type": str(authority_payload.get("authority_type") or ""),
                "ministry": str(authority_payload.get("ministry") or ""),
                "department": str(authority_payload.get("department") or ""),
                "state": str(authority_payload.get("state") or ""),
                "official_url": str(authority_payload.get("official_url") or ""),
            },
        )
        counts["authorities"] += int(created)

        source_info = payload.get("source_document") or {}
        source_name = str(source_info.get("source_name") or authority_name)
        manifest_hash = str(source_info.get("content_hash") or "")

        for candidate in payload.get("candidates") or []:
            curation = candidate.get("curation") or {}
            title = str(candidate.get("canonical_title") or "").strip()
            official_url = str(curation.get("official_url") or "").strip()
            if not title or not official_url:
                raise CommandError(f"Incomplete curated candidate in {path}")

            source = _source_for_manifest(
                source_name=source_name,
                official_url=official_url,
                authority=authority_payload,
            )
            document_hash = _content_hash(
                manifest_hash,
                candidate.get("pilot_key"),
                curation,
            )
            document = _source_document(
                source=source,
                title=title,
                official_url=official_url,
                content_hash=document_hash,
                manifest_key=str(payload.get("manifest_key") or path.stem),
            )

            alternative_names = []
            expected_title = str(candidate.get("expected_title") or "").strip()
            if expected_title and expected_title != title:
                alternative_names.append(expected_title)

            scheme, scheme_created = Scheme.objects.update_or_create(
                canonical_name=title,
                authority=authority,
                defaults={
                    "short_name": _short_name(candidate, title),
                    "alternative_names": alternative_names,
                    "lifecycle_status": Scheme.LifecycleStatus.ACTIVE,
                },
            )
            counts["schemes"] += int(scheme_created)

            benefits = [
                item for item in (curation.get("canonical_benefits") or [])
                if isinstance(item, dict)
            ]
            minimum_amount, maximum_amount = _amount_bounds(benefits)
            support_types = list(curation.get("canonical_support_types") or [])
            categories = list(curation.get("canonical_categories") or [])
            application_steps = list(curation.get("canonical_application_steps") or [])
            required_documents = list(curation.get("canonical_required_documents") or [])
            currency = next(
                (
                    str(item.get("currency") or "INR")[:3]
                    for item in benefits
                    if item.get("currency")
                ),
                "INR",
            )
            version_hash = _content_hash(title, document_hash, curation)
            version = SchemeVersion.objects.filter(
                scheme=scheme,
                content_hash=version_hash,
            ).first()
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
                    source_document=document,
                    captured_at=timezone.now(),
                    content_hash=version_hash,
                    description=str(curation.get("canonical_summary") or ""),
                    objective=str(curation.get("canonical_objective") or ""),
                    support_types=support_types,
                    categories=categories,
                    minimum_amount=minimum_amount,
                    maximum_amount=maximum_amount,
                    currency=currency,
                    equity_required=(
                        True if any("equity" in str(value).lower() for value in support_types)
                        else None
                    ),
                    application_status=SchemeVersion.ApplicationStatus.UNKNOWN,
                    official_url=official_url,
                    application_url=str(curation.get("application_url") or ""),
                    required_documents=required_documents,
                    application_steps=application_steps,
                    benefits=benefits,
                    restrictions=[],
                    verification_status=SchemeVersion.VerificationStatus.VERIFIED,
                    extraction_confidence=Decimal("1.0000"),
                    verified_at=timezone.now(),
                )
                counts["versions"] += 1
            else:
                # Keep the same immutable content identity while refreshing
                # operational fields that can be corrected in the manifest.
                version.source_document = document
                version.description = str(curation.get("canonical_summary") or "")
                version.objective = str(curation.get("canonical_objective") or "")
                version.support_types = support_types
                version.categories = categories
                version.minimum_amount = minimum_amount
                version.maximum_amount = maximum_amount
                version.currency = currency
                version.equity_required = (
                    True if any("equity" in str(value).lower() for value in support_types)
                    else None
                )
                version.official_url = official_url
                version.application_url = str(curation.get("application_url") or "")
                version.required_documents = required_documents
                version.application_steps = application_steps
                version.benefits = benefits
                version.verification_status = SchemeVersion.VerificationStatus.VERIFIED
                version.extraction_confidence = Decimal("1.0000")
                version.verified_at = version.verified_at or timezone.now()
                version.save()

            if scheme.current_version_id != version.id:
                scheme.current_version = version
                scheme.lifecycle_status = Scheme.LifecycleStatus.ACTIVE
                scheme.save(update_fields=["current_version", "lifecycle_status", "updated_at"])

            pilot_key = str(candidate.get("pilot_key") or "").strip()
            counts["rules"] += _sync_rules(
                version,
                rules_by_key.get(pilot_key, []),
            )

    _bootstrap_external_review_matches(counts)
    return counts


class Command(BaseCommand):
    help = "Create or refresh the bundled reviewer-verified canonical scheme catalog."

    def handle(self, *args, **options):
        counts = bootstrap_verified_catalog()
        active = Scheme.objects.filter(
            lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
            current_version__verification_status=SchemeVersion.VerificationStatus.VERIFIED,
        ).count()
        self.stdout.write(
            self.style.SUCCESS(
                "Verified scheme catalog ready: "
                f"active={active}, new_schemes={counts['schemes']}, "
                f"new_versions={counts['versions']}, rules_synced={counts['rules']}"
            )
        )
