from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.discovery.models import CrawlFrontierEntry, DiscoveredURL
from apps.documents.models import DocumentExtraction
from apps.sources.models import SourceDocument
from apps.sources.services.storage import download_bytes

from .adapters import adapter_for
from .link_discovery import discover_links
from .quality import assess_extraction
from .url_tools import normalize_url


@dataclass(frozen=True)
class DiscoveryResult:
    document: SourceDocument
    discovered_count: int
    queued_count: int
    rejected_count: int


def discover_document(document: SourceDocument) -> DiscoveryResult:
    normalized_mime = (document.mime_type or "").split(";", 1)[0].lower()
    discovered_count = 0
    queued_count = 0
    rejected_count = 0

    extraction = (
        DocumentExtraction.objects.filter(
            source_document=document,
            status=DocumentExtraction.Status.SUCCEEDED,
        )
        .order_by("-created_at")
        .first()
    )
    if extraction:
        assess_extraction(extraction)

    if normalized_mime not in {"text/html", "application/xhtml+xml"}:
        return DiscoveryResult(document, 0, 0, 0)

    raw_content = download_bytes(document.storage_key)
    parent_url = document.final_url or document.source_url
    candidates = discover_links(
        source=document.source,
        parent_url=parent_url,
        content=raw_content,
    )
    adapter = adapter_for(document.source.official_domain)
    max_depth = min(
        int(adapter.get("max_depth", settings.DISCOVERY_MAX_DEPTH)),
        settings.DISCOVERY_MAX_DEPTH,
    )
    parent_depth = int(document.metadata.get("crawl_depth", 0))
    max_pages = min(
        int(adapter.get("max_pages", settings.DISCOVERY_MAX_PAGES_PER_SOURCE)),
        settings.DISCOVERY_MAX_PAGES_PER_SOURCE,
    )
    collected_pages = DiscoveredURL.objects.filter(
        source=document.source,
        status=DiscoveredURL.Status.COLLECTED,
    ).count()
    pending_pages = CrawlFrontierEntry.objects.filter(
        discovered_url__source=document.source,
        status=CrawlFrontierEntry.Status.PENDING,
    ).count()

    with transaction.atomic():
        for candidate in candidates[: settings.DISCOVERY_MAX_LINKS_PER_DOCUMENT]:
            normalized = normalize_url(parent_url, candidate.normalized_url)
            if not normalized:
                continue
            discovered, created = DiscoveredURL.objects.update_or_create(
                source=document.source,
                normalized_url=normalized,
                defaults={
                    "parent_document": document,
                    "original_url": candidate.original_url,
                    "anchor_text": candidate.anchor_text,
                    "page_type": candidate.page_type,
                    "discovery_method": candidate.discovery_method,
                    "crawl_depth": parent_depth + 1,
                    "priority": candidate.priority,
                    "allowed": candidate.allowed,
                    "rejection_reason": candidate.rejection_reason,
                    "signals": candidate.signals,
                    "last_seen_at": timezone.now(),
                    "status": (
                        DiscoveredURL.Status.DISCOVERED
                        if candidate.allowed
                        else DiscoveredURL.Status.REJECTED
                    ),
                },
            )
            discovered_count += int(created)
            if discovered.last_collected_document_id:
                if discovered.status != DiscoveredURL.Status.COLLECTED:
                    discovered.status = DiscoveredURL.Status.COLLECTED
                    discovered.save(update_fields=["status", "updated_at"])
                continue
            if not candidate.allowed or discovered.crawl_depth > max_depth:
                rejected_count += 1
                continue
            if collected_pages + pending_pages + queued_count >= max_pages:
                discovered.status = DiscoveredURL.Status.REJECTED
                discovered.rejection_reason = "source page limit reached"
                discovered.save(
                    update_fields=[
                        "status",
                        "rejection_reason",
                        "updated_at",
                    ]
                )
                rejected_count += 1
                continue
            _, frontier_created = CrawlFrontierEntry.objects.get_or_create(
                discovered_url=discovered,
                defaults={"status": CrawlFrontierEntry.Status.PENDING},
            )
            if frontier_created:
                discovered.status = DiscoveredURL.Status.QUEUED
                discovered.save(update_fields=["status", "updated_at"])
                queued_count += 1

    document.metadata = {
        **document.metadata,
        "discovery_completed": True,
        "discovered_url_count": DiscoveredURL.objects.filter(parent_document=document).count(),
    }
    document.save(update_fields=["metadata", "updated_at"])
    return DiscoveryResult(
        document=document,
        discovered_count=discovered_count,
        queued_count=queued_count,
        rejected_count=rejected_count,
    )
