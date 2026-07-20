from __future__ import annotations

from bs4 import BeautifulSoup
from django.utils import timezone

from apps.discovery.models import CrawlFrontierEntry, DiscoveredURL
from apps.sources.models import Source, SourceDocument
from apps.sources.services.storage import download_bytes

from .classifier import classify_page
from .url_tools import candidate_is_allowed, normalize_url


def seed_source_urls(source: Source) -> int:
    values = [
        (source.listing_url, DiscoveredURL.PageType.LISTING, 0),
        (
            f"https://{source.official_domain}/sitemap.xml",
            DiscoveredURL.PageType.SITEMAP,
            5,
        ),
        (
            f"https://www.{source.official_domain}/sitemap.xml",
            DiscoveredURL.PageType.SITEMAP,
            5,
        ),
    ]
    created_count = 0
    for raw_url, page_type, priority in values:
        normalized = normalize_url(source.listing_url, raw_url)
        if not normalized:
            continue
        allowed, reason = candidate_is_allowed(source, normalized)
        discovered, created = DiscoveredURL.objects.update_or_create(
            source=source,
            normalized_url=normalized,
            defaults={
                "original_url": raw_url,
                "page_type": page_type,
                "discovery_method": DiscoveredURL.DiscoveryMethod.SEED,
                "crawl_depth": 0,
                "priority": priority,
                "allowed": allowed,
                "rejection_reason": reason,
                "last_seen_at": timezone.now(),
                "status": (
                    DiscoveredURL.Status.DISCOVERED if allowed else DiscoveredURL.Status.REJECTED
                ),
            },
        )
        created_count += int(created)
        if discovered.last_collected_document_id:
            discovered.status = DiscoveredURL.Status.COLLECTED
            discovered.save(update_fields=["status", "updated_at"])
        elif allowed:
            CrawlFrontierEntry.objects.get_or_create(discovered_url=discovered)
    return created_count


def discover_sitemap_document(document: SourceDocument) -> int:
    content = download_bytes(document.storage_key)
    soup = BeautifulSoup(content, "xml")
    count = 0
    for location in soup.find_all("loc"):
        raw_url = location.get_text(" ", strip=True)
        normalized = normalize_url(document.final_url or document.source_url, raw_url)
        if not normalized:
            continue
        allowed, reason = candidate_is_allowed(document.source, normalized)
        page_type = classify_page(url=normalized)
        discovered, created = DiscoveredURL.objects.update_or_create(
            source=document.source,
            normalized_url=normalized,
            defaults={
                "parent_document": document,
                "original_url": raw_url,
                "page_type": page_type,
                "discovery_method": DiscoveredURL.DiscoveryMethod.SITEMAP,
                "crawl_depth": 1,
                "priority": 15 if page_type != "unknown" else 55,
                "allowed": allowed,
                "rejection_reason": reason,
                "last_seen_at": timezone.now(),
                "status": (
                    DiscoveredURL.Status.DISCOVERED if allowed else DiscoveredURL.Status.REJECTED
                ),
            },
        )
        count += int(created)
        if discovered.last_collected_document_id:
            discovered.status = DiscoveredURL.Status.COLLECTED
            discovered.save(update_fields=["status", "updated_at"])
        elif allowed:
            CrawlFrontierEntry.objects.get_or_create(discovered_url=discovered)
    return count
