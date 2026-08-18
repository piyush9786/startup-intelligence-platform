"""Grounded live-research bridge for the Founder Assistant."""
from __future__ import annotations

from typing import Any

from django.db import IntegrityError, transaction

from apps.research.models import (
    ResearchEvidence,
    ResearchRequest,
)
from apps.research.services.report_generator import (
    generate_research_report,
)
from apps.startups.models import StartupProfile

from .tool_registry import (
    AgentToolContext,
    AgentToolInputError,
)

LIVE_RESEARCH_TOOL = "run_live_research"
LIVE_RESEARCH_VERSION = "v1"

_MAX_QUESTION_LENGTH = 1200

_TRUST_ORDER = {
    ResearchEvidence.VerificationStatus.VERIFIED_INTERNAL: 0,
    ResearchEvidence.VerificationStatus.OFFICIAL_LIVE: 1,
    ResearchEvidence.VerificationStatus.REPUTABLE_SECONDARY: 2,
    ResearchEvidence.VerificationStatus.UNVERIFIED_LIVE: 3,
}

_RESEARCH_FIELDS = (
    "historical_peers",
    "current_competitors",
    "recent_market_developments",
    "government_schemes",
    "compliance_requirements",
    "funding_opportunities",
    "loan_options",
    "risks",
    "market_gaps",
    "recommended_next_actions",
)

_FALLBACK_MARKERS = (
    "no verified historical peers were retrieved",
    "no current market events were retrieved",
    "review the verified scheme explorer",
    "review the requirements workspace",
    "review verified schemes and the funding workspace",
    "review the funding and loans workspace",
    "detailed market-gap analysis requires active model reasoning",
    "re-run research when live search and model generation are available",
    "live search or model generation was unavailable",
)


def _normalize(text: str) -> str:
    return " ".join(
        str(text).casefold().split()
    )


def requires_live_research(
    message: str,
) -> bool:
    """Return True only when current external evidence is useful."""

    text = _normalize(message)

    if not text:
        return False

    explicit_search = (
        "search online",
        "search the web",
        "search web",
        "look online",
        "look up online",
        "find online",
        "check online",
        "browse online",
        "web search",
    )

    if any(
        marker in text
        for marker in explicit_search
    ):
        return True

    inherently_live = (
        "competitor",
        "market trend",
        "market development",
        "industry trend",
        "market size",
        "startup news",
        "funding round",
        "investor activity",
        "government scheme",
        "schemes available",
        "scheme available",
        "grants available",
        "grant available",
        "loan option",
        "loan available",
        "credit support",
        "regulatory update",
        "compliance requirement",
        "certification requirement",
    )

    if any(
        marker in text
        for marker in inherently_live
    ):
        return True

    freshness = (
        "latest",
        "current",
        "currently",
        "recent",
        "today",
        "this week",
        "this month",
        "newest",
        "new ",
        "available now",
        "right now",
        "2026",
    )

    external_domains = (
        "scheme",
        "grant",
        "funding",
        "loan",
        "credit",
        "investor",
        "investment",
        "market",
        "industry",
        "competitor",
        "regulation",
        "regulatory",
        "compliance",
        "certification",
        "government",
        "startup ecosystem",
    )

    return (
        any(
            marker in text
            for marker in freshness
        )
        and any(
            marker in text
            for marker in external_domains
        )
    )


def _clean_values(
    value: Any,
) -> list[str]:
    if not isinstance(value, list):
        return []

    output: list[str] = []

    for raw in value:
        item = " ".join(
            str(raw).split()
        ).strip()

        if not item:
            continue

        lowered = item.casefold()

        if any(
            marker in lowered
            for marker in _FALLBACK_MARKERS
        ):
            continue

        if item not in output:
            output.append(item)

    return output[:4]


def _confidence(
    item: ResearchEvidence,
) -> float:
    try:
        value = float(
            item.confidence_score
        )
    except (TypeError, ValueError):
        return 0.0

    return max(
        0.0,
        min(1.0, value),
    )


def run_live_research(
    context: AgentToolContext,
    input_params: dict[str, Any],
) -> dict[str, Any]:
    """Run one founder-owned synchronous Research workflow."""

    accepted_keys = {
        "question",
    }

    unknown = (
        set(input_params)
        - accepted_keys
    )

    if unknown:
        raise AgentToolInputError(
            "Unsupported live research parameters: "
            f"{sorted(unknown)!r}."
        )

    question = " ".join(
        str(
            input_params.get(
                "question",
                "",
            )
        ).split()
    ).strip()

    if len(question) < 3:
        raise AgentToolInputError(
            "A research question is required."
        )

    if len(question) > _MAX_QUESTION_LENGTH:
        raise AgentToolInputError(
            "The research question is too long."
        )

    if context.startup_profile_id is None:
        raise AgentToolInputError(
            "A startup profile must be selected "
            "before live founder research can run."
        )

    profile = (
        StartupProfile.objects
        .filter(
            pk=context.startup_profile_id,
            owner_id=context.founder_id,
        )
        .first()
    )

    if profile is None:
        raise AgentToolInputError(
            "The session startup profile is unavailable."
        )

    active = (
        ResearchRequest.objects
        .filter(
            startup_profile=profile,
            status__in=(
                ResearchRequest.Status.QUEUED,
                ResearchRequest.Status.RUNNING,
            ),
        )
        .first()
    )

    if active is not None:
        raise AgentToolInputError(
            "A live research request is already "
            "running for this startup."
        )

    try:
        with transaction.atomic():
            request = (
                ResearchRequest.objects
                .create(
                    startup_profile=profile,
                    requested_by_id=(
                        context.actor_id
                    ),
                    question=question,
                )
            )
    except IntegrityError as exc:
        raise AgentToolInputError(
            "A live research request is already "
            "running for this startup."
        ) from exc

    report = generate_research_report(
        str(request.pk),
        task_id=(
            "assistant:"
            f"{context.session_id}"
        ),
    )

    request.refresh_from_db()

    report_data = dict(
        report.report
        or {}
    )

    metadata = dict(
        report_data.get(
            "research_metadata"
        )
        or {}
    )

    sections = {
        field: _clean_values(
            report_data.get(
                field,
                [],
            )
        )
        for field in _RESEARCH_FIELDS
    }

    used_urls = {
        str(url).strip()
        for url in (
            report_data.get(
                "sources"
            )
            or []
        )
        if str(url).strip()
    }

    evidence_items = list(
        ResearchEvidence.objects
        .filter(
            research_request=request,
        )
        .exclude(
            verification_status=(
                ResearchEvidence
                .VerificationStatus
                .REJECTED
            ),
        )
    )

    evidence_items.sort(
        key=lambda item: (
            0
            if item.url in used_urls
            else 1,
            _TRUST_ORDER.get(
                item.verification_status,
                99,
            ),
            -_confidence(item),
        )
    )

    sources = []

    for item in evidence_items[:6]:
        sources.append(
            {
                "title": item.title,
                "publisher": (
                    item.publisher
                    or ""
                ),
                "url": item.url,
                "source_type": (
                    item.source_type
                ),
                "verification_status": (
                    item.verification_status
                ),
                "confidence_score": (
                    _confidence(item)
                ),
                "used_by_report": (
                    item.url
                    in used_urls
                ),
                "excerpt": (
                    " ".join(
                        (
                            item.content_excerpt
                            or ""
                        ).split()
                    )[:360]
                ),
            }
        )

    summary = " ".join(
        str(
            report_data.get(
                "startup_summary",
                "",
            )
        ).split()
    ).strip()

    return {
        "research": {
            "request_id": str(
                request.pk
            ),
            "report_id": str(
                report.pk
            ),
            "question": question,
            "status": request.status,
            "model_name": (
                report.model_name
            ),
            "llm_status": (
                metadata.get(
                    "llm_status"
                )
            ),
            "live_search_status": (
                metadata.get(
                    "live_search_status"
                )
            ),
            "search_failure_count": (
                metadata.get(
                    "search_failure_count",
                    0,
                )
            ),
            "summary": summary,
            "sections": sections,
            "confidence_score": (
                report_data.get(
                    "confidence_score"
                )
            ),
        },
        "sources": sources,
    }
