from celery import shared_task

from apps.discovery.models import CrawlFrontierEntry
from apps.discovery.services.discovery import discover_document
from apps.discovery.services.frontier import process_frontier_entry
from apps.discovery.services.quality import assess_extraction
from apps.documents.models import DocumentExtraction
from apps.sources.models import SourceDocument


@shared_task
def discover_document_task(document_id: str) -> dict[str, object]:
    document = SourceDocument.objects.get(id=document_id)
    result = discover_document(document)
    return {
        "document_id": str(document.id),
        "discovered": result.discovered_count,
        "queued": result.queued_count,
        "rejected": result.rejected_count,
    }


@shared_task(
    autoretry_for=(OSError, RuntimeError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def process_frontier_entry_task(entry_id: str) -> dict[str, object]:
    entry = CrawlFrontierEntry.objects.get(id=entry_id)
    result = process_frontier_entry(entry)
    return {
        "entry_id": str(entry.id),
        "document_id": result.document_id,
        "created": result.created,
        "unchanged": result.unchanged,
    }


@shared_task
def assess_extraction_task(extraction_id: str) -> dict[str, object]:
    extraction = DocumentExtraction.objects.get(id=extraction_id)
    result = assess_extraction(extraction)
    return {
        "extraction_id": str(extraction.id),
        "score": result.score,
        "page_type": result.assessment.page_type,
    }
