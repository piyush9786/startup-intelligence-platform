"""Verified local retrieval for the research workflow."""
from __future__ import annotations

from typing import Any

from apps.companies.models import Company
from apps.schemes.models import Scheme, SchemeVersion


def retrieve_local_verified_knowledge(
    profile,
) -> list[dict[str, Any]]:
    """Retrieve founder-owned profile facts and reviewed local records."""
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

    # Add Qdrant vector search retrieval if RESEARCH_RAG_ENABLED is active
    from django.conf import settings
    if getattr(settings, "RESEARCH_RAG_ENABLED", True):
        try:
            from apps.knowledge.services.vector_search import search_document_chunks
            query_str = f"{profile.startup_name} {' '.join(profile.sectors or [])}".strip()
            chunks = search_document_chunks(
                query=query_str or "startup scheme eligibility",
                startup_profile_id=str(profile.id),
                top_k=3,
            )
            for chunk in chunks:
                local_items.append(
                    {
                        "title": f"Vector Document: {chunk.title}",
                        "url": chunk.source_url or f"internal://documents/{chunk.document_id}",
                        "source_type": "verified_internal",
                        "content_excerpt": chunk.text[:300],
                    }
                )
        except Exception:
            pass

    return local_items
