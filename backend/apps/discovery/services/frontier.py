from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.discovery.models import CrawlFrontierEntry, DiscoveredURL
from apps.documents.services.processor import process_document
from apps.sources.models import CrawlRun
from apps.sources.services.collector import CollectionError, collect_source

from .discovery import discover_document
from .sitemaps import discover_sitemap_document


@dataclass(frozen=True)
class FrontierResult:
    entry: CrawlFrontierEntry
    document_id: str | None
    created: bool
    unchanged: bool


def process_frontier_entry(entry: CrawlFrontierEntry) -> FrontierResult:
    with transaction.atomic():
        locked = CrawlFrontierEntry.objects.select_for_update().get(id=entry.id)
        if locked.status == CrawlFrontierEntry.Status.RUNNING:
            return FrontierResult(locked, None, False, True)
        locked.status = CrawlFrontierEntry.Status.RUNNING
        locked.started_at = timezone.now()
        locked.finished_at = None
        locked.error_message = ""
        locked.save()

    discovered = locked.discovered_url
    try:
        result = collect_source(
            discovered.source,
            url=discovered.normalized_url,
            trigger=CrawlRun.Trigger.SCHEDULED,
        )
        document = result.document
        document.metadata = {
            **document.metadata,
            "crawl_depth": discovered.crawl_depth,
            "discovered_url_id": str(discovered.id),
        }
        document.save(update_fields=["metadata", "updated_at"])

        discovered.last_collected_document = document
        discovered.status = DiscoveredURL.Status.COLLECTED
        discovered.save(
            update_fields=[
                "last_collected_document",
                "status",
                "updated_at",
            ]
        )

        normalized_mime = (document.mime_type or "").split(";", 1)[0].lower()
        if normalized_mime in {"application/xml", "text/xml"}:
            discover_sitemap_document(document)
        else:
            process_document(document)
            discover_document(document)

        locked.status = CrawlFrontierEntry.Status.SUCCEEDED
        locked.finished_at = timezone.now()
        locked.save(update_fields=["status", "finished_at", "updated_at"])
        return FrontierResult(
            entry=locked,
            document_id=str(document.id),
            created=result.created,
            unchanged=result.unchanged,
        )
    except Exception as exc:
        locked.retry_count += 1
        locked.finished_at = timezone.now()
        locked.error_message = str(exc)[:5000]
        if locked.retry_count < locked.max_retries:
            locked.status = CrawlFrontierEntry.Status.PENDING
            locked.next_retry_at = timezone.now() + timedelta(
                minutes=5 * (2 ** (locked.retry_count - 1))
            )
        else:
            locked.status = CrawlFrontierEntry.Status.FAILED
            discovered.status = DiscoveredURL.Status.FAILED
            discovered.rejection_reason = str(exc)[:2000]
            discovered.save(
                update_fields=[
                    "status",
                    "rejection_reason",
                    "updated_at",
                ]
            )
        locked.save()
        if isinstance(exc, CollectionError):
            raise
        raise RuntimeError(str(exc)) from exc
