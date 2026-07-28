"""Verified and curated local retrieval for the research workflow."""
from __future__ import annotations

import re
from typing import Any, Iterable

from apps.companies.models import Company
from apps.knowledge.models import (
    ExternalCapitalSupportRecord,
    ExternalCertificationRequirementRecord,
    ExternalSchemeRecord,
)
from apps.schemes.models import Scheme, SchemeVersion

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_PROFILE_MATCH_STOPWORDS = frozenset(
    {
        "all",
        "and",
        "business",
        "capital",
        "company",
        "early",
        "funding",
        "grant",
        "growth",
        "idea",
        "india",
        "indian",
        "loan",
        "pan",
        "scheme",
        "stage",
        "startup",
        "support",
    }
)
_RANKING_ITERATOR_CHUNK_SIZE = 500


def _text_tokens(*values: Any) -> set[str]:
    text = " ".join(
        str(value)
        for value in values
        if value not in (None, "", [], {})
    ).casefold()
    return {
        token
        for token in _TOKEN_PATTERN.findall(text)
        if len(token) >= 3
    }


def _profile_terms(profile) -> set[str]:
    profile_data = profile.profile_data or {}
    return _text_tokens(
        profile.startup_name,
        profile.description,
        profile.stage,
        profile.state,
        profile.district,
        profile.sectors,
        profile.technologies,
        profile.resource_needs,
        profile.funding_purpose,
        profile.revenue_stage,
        profile_data.get("target_customer"),
        profile_data.get("customer_segment"),
        profile_data.get("sub_industry"),
        profile_data.get("business_model"),
        profile_data.get("revenue_model"),
    ) - _PROFILE_MATCH_STOPWORDS


def _rank_records(
    records: Iterable[Any],
    *,
    profile_terms: set[str],
    fields: tuple[str, ...],
    limit: int,
) -> list[Any]:
    if not profile_terms or limit <= 0:
        return []

    ranked: list[tuple[int, int, int, str, Any]] = []
    for record in records:
        record_terms = _text_tokens(
            *(getattr(record, field, "") for field in fields)
        )
        overlap = profile_terms & record_terms
        if not overlap:
            continue

        verified_bonus = int(
            getattr(record, "review_status", "") == "verified"
        )
        name = str(
            getattr(record, "scheme_name", "")
            or getattr(record, "support_name", "")
            or getattr(record, "certificate_name", "")
        )
        ranked.append(
            (
                len(overlap),
                sum(len(token) for token in overlap),
                verified_bonus,
                name.casefold(),
                record,
            )
        )

    ranked.sort(
        key=lambda item: (
            -item[0],
            -item[1],
            -item[2],
            item[3],
        )
    )
    return [item[4] for item in ranked[:limit]]


def _catalog_source_type(record: Any) -> str:
    return (
        "verified_internal"
        if getattr(record, "review_status", "") == "verified"
        else "curated_catalog"
    )


def _catalog_notice(record: Any) -> str:
    status = str(
        getattr(record, "review_status", "needs_review")
    )
    if status == "verified":
        return "Catalog review status: verified."
    return (
        f"Catalog review status: {status}; use as exploratory catalog "
        "context and verify official terms before acting."
    )


def _append_external_schemes(
    local_items: list[dict[str, Any]],
    *,
    profile_terms: set[str],
) -> None:
    queryset = (
        ExternalSchemeRecord.objects.filter(dataset__is_active=True)
        .exclude(review_status=ExternalSchemeRecord.ReviewStatus.REJECTED)
        .select_related("dataset")
    )
    records = _rank_records(
        queryset.iterator(chunk_size=_RANKING_ITERATOR_CHUNK_SIZE),
        profile_terms=profile_terms,
        fields=(
            "scheme_name",
            "ministry",
            "department",
            "sector",
            "startup_stage",
            "startup_type",
            "industry",
            "state",
            "funding_type",
            "financial_instrument",
            "eligibility",
        ),
        limit=5,
    )
    for record in records:
        local_items.append(
            {
                "title": f"Support Catalog Scheme: {record.scheme_name}",
                "url": (
                    record.official_application_url
                    or f"internal://external-schemes/{record.id}"
                ),
                "source_type": _catalog_source_type(record),
                "content_excerpt": (
                    f"{_catalog_notice(record)} "
                    f"Ministry: {record.ministry or 'Not specified'}; "
                    f"Department: {record.department or 'Not specified'}; "
                    f"Sector: {record.sector or 'Not specified'}; "
                    f"Stages: {record.startup_stage or []}; "
                    f"Funding type: {record.funding_type or 'Not specified'}; "
                    f"Funding amount: {record.funding_amount or 'Not specified'}; "
                    f"Instrument: {record.financial_instrument or 'Not specified'}; "
                    f"Eligibility: {record.eligibility[:500] or 'Not specified'}; "
                    f"Documents: {record.documents_required or []}"
                ),
            }
        )


def _append_external_capital_support(
    local_items: list[dict[str, Any]],
    *,
    profile_terms: set[str],
) -> None:
    queryset = (
        ExternalCapitalSupportRecord.objects.filter(
            dataset__is_active=True,
        )
        .exclude(
            review_status=(
                ExternalCapitalSupportRecord.ReviewStatus.REJECTED
            )
        )
        .select_related("dataset")
    )
    records = _rank_records(
        queryset.iterator(chunk_size=_RANKING_ITERATOR_CHUNK_SIZE),
        profile_terms=profile_terms,
        fields=(
            "support_name",
            "support_type",
            "scheme_name",
            "ministry",
            "implementing_agency",
            "funding_category",
            "startup_stage",
            "industry",
            "eligible_entity",
            "state",
            "funding_purpose",
            "interest_rate_text",
            "collateral_required_text",
            "repayment_required_text",
        ),
        limit=5,
    )
    for record in records:
        amount_parts = [
            part
            for part in (
                record.raw_minimum_amount,
                record.raw_maximum_amount,
            )
            if part
        ]
        amount_text = " to ".join(amount_parts) or "Not specified"
        local_items.append(
            {
                "title": (
                    f"Capital and Loan Catalog: {record.support_name}"
                ),
                "url": (
                    f"internal://external-capital-support/{record.id}"
                ),
                "source_type": _catalog_source_type(record),
                "content_excerpt": (
                    f"{_catalog_notice(record)} "
                    f"Support type: {record.support_type or 'Not specified'}; "
                    f"Category: {record.funding_category or 'Not specified'}; "
                    f"Amount: {amount_text} {record.currency or 'INR'}; "
                    f"Interest: {record.interest_rate_text or 'Not specified'}; "
                    f"Collateral: {record.collateral_required_text or 'Not specified'}; "
                    f"Repayment: {record.repayment_required_text or 'Not specified'}; "
                    f"Stages: {record.startup_stage or []}; "
                    f"Industries: {record.industry or []}; "
                    f"Purpose: {record.funding_purpose or 'Not specified'}; "
                    f"Agency: {record.implementing_agency or 'Not specified'}"
                ),
            }
        )


def _append_external_requirements(
    local_items: list[dict[str, Any]],
    *,
    profile_terms: set[str],
) -> None:
    queryset = (
        ExternalCertificationRequirementRecord.objects.filter(
            dataset__is_active=True,
            display_eligible=True,
        )
        .exclude(
            review_status=(
                ExternalCertificationRequirementRecord
                .ReviewStatus.REJECTED
            )
        )
        .select_related("dataset")
    )
    records = _rank_records(
        queryset.iterator(chunk_size=_RANKING_ITERATOR_CHUNK_SIZE),
        profile_terms=profile_terms,
        fields=(
            "certificate_name",
            "certificate_type",
            "description",
            "industry",
            "startup_stage",
            "requirement_level",
            "eligibility",
            "benefits",
            "issuing_authority",
        ),
        limit=5,
    )
    for record in records:
        local_items.append(
            {
                "title": (
                    f"Certification Requirement: {record.certificate_name}"
                ),
                "url": (
                    record.official_apply_url
                    or f"internal://external-requirements/{record.id}"
                ),
                "source_type": _catalog_source_type(record),
                "content_excerpt": (
                    f"{_catalog_notice(record)} "
                    f"Type: {record.certificate_type or 'Not specified'}; "
                    f"Requirement level: {record.requirement_level or 'Not specified'}; "
                    f"Industries: {record.industry or []}; "
                    f"Stages: {record.startup_stage or []}; "
                    f"Description: {record.description[:400] or 'Not specified'}; "
                    f"Eligibility: {record.eligibility[:400] or 'Not specified'}; "
                    f"Validity: {record.validity or 'Not specified'}; "
                    f"Renewal: {record.renewal_period or 'Not specified'}; "
                    f"Authority: {record.issuing_authority or 'Not specified'}"
                ),
            }
        )


def retrieve_local_verified_knowledge(
    profile,
) -> list[dict[str, Any]]:
    """Retrieve founder facts, reviewed records, and curated support catalogs."""
    local_items: list[dict[str, Any]] = [
        {
            "title": f"Verified Profile: {profile.startup_name}",
            "url": f"internal://startups/{profile.id}",
            "source_type": "verified_internal",
            "content_excerpt": (
                f"Stage: {profile.stage}; "
                f"State: {profile.state or 'Not specified'}; "
                f"Sectors: {profile.sectors or []}; "
                f"Technologies: {profile.technologies or []}"
            ),
        }
    ]

    sectors = profile.sectors or []
    company_query = Company.objects.filter(
        verification_status__in=[
            Company.VerificationStatus.VERIFIED,
            Company.VerificationStatus.PARTIALLY_VERIFIED,
        ],
    )
    if sectors:
        company_query = company_query.filter(
            industry__icontains=sectors[0],
        )

    companies = list(
        company_query.prefetch_related("metrics", "outcomes")[:5]
    )
    for company in companies:
        recent_metrics = ", ".join(
            (
                f"{metric.get_metric_name_display()}: "
                f"{metric.metric_value:g} {metric.metric_unit} "
                f"({metric.observation_date.isoformat()})"
            )
            for metric in list(company.metrics.all())[:3]
        )
        recent_outcomes = ", ".join(
            (
                f"{outcome.get_outcome_type_display()}"
                + (
                    f" ({outcome.outcome_date.isoformat()})"
                    if outcome.outcome_date
                    else ""
                )
            )
            for outcome in list(company.outcomes.all())[:3]
        )
        local_items.append(
            {
                "title": (
                    f"Historical Peer: {company.canonical_name}"
                ),
                "url": f"internal://companies/{company.id}",
                "source_type": "verified_internal",
                "content_excerpt": (
                    f"Industry: {company.industry}; "
                    f"Sub-industry: "
                    f"{company.sub_industry or 'Not specified'}; "
                    f"Business model: {company.business_model}; "
                    f"Operating status: {company.operating_status}; "
                    f"Verification: {company.verification_status}; "
                    f"Recent metrics: "
                    f"{recent_metrics or 'None recorded'}; "
                    f"Outcomes: "
                    f"{recent_outcomes or 'None recorded'}"
                ),
            }
        )

    schemes = list(
        Scheme.objects.filter(
            lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
            current_version__verification_status=(
                SchemeVersion.VerificationStatus.VERIFIED
            ),
        )
        .select_related("authority", "current_version")[:5]
    )
    for scheme in schemes:
        version = scheme.current_version
        if version is None:
            continue
        local_items.append(
            {
                "title": (
                    f"Official Scheme: {scheme.canonical_name}"
                ),
                "url": version.official_url,
                "source_type": "verified_internal",
                "content_excerpt": (
                    f"Authority: {scheme.authority.name}; "
                    f"Ministry: "
                    f"{scheme.authority.ministry or 'Not specified'}; "
                    f"Description: {version.description[:300]}; "
                    f"Eligible sectors: {version.eligible_sectors}; "
                    f"Eligible stages: {version.eligible_stages}; "
                    f"Application status: "
                    f"{version.application_status}"
                ),
            }
        )

    profile_terms = _profile_terms(profile)
    _append_external_schemes(
        local_items,
        profile_terms=profile_terms,
    )
    _append_external_capital_support(
        local_items,
        profile_terms=profile_terms,
    )
    _append_external_requirements(
        local_items,
        profile_terms=profile_terms,
    )

    # Qdrant retrieval belongs only in the explicit
    # orchestration.retrieve_vector_evidence step. This avoids duplicate
    # searches and keeps vector status/error metadata accurate.
    return local_items
