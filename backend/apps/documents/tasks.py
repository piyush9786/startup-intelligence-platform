from __future__ import annotations

from celery import shared_task

from apps.documents.services.processor import process_document
from apps.sources.models import SourceDocument


@shared_task(
    autoretry_for=(RuntimeError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_source_document_task(
    document_id: str,
    *,
    force: bool = False,
) -> dict[str, object]:
    document = SourceDocument.objects.get(id=document_id)
    result = process_document(document, force=force)
    return {
        "document_id": str(document.id),
        "extraction_id": str(result.extraction.id),
        "created": result.created,
        "unchanged": result.unchanged,
        "chunk_count": result.extraction.chunk_count,
    }
