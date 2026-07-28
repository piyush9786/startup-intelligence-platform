from __future__ import annotations

from celery import shared_task
from django.conf import settings

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
    embedding_task_id = None
    if settings.STARTUP_ADVISOR_RAG_ENABLED:
        from apps.knowledge.tasks import (
            index_document_extraction_task,
        )

        embedding_task = index_document_extraction_task.delay(
            str(result.extraction.id),
            force=force,
        )
        embedding_task_id = embedding_task.id

    return {
        "document_id": str(document.id),
        "extraction_id": str(result.extraction.id),
        "created": result.created,
        "unchanged": result.unchanged,
        "chunk_count": result.extraction.chunk_count,
        "embedding_task_id": embedding_task_id,
    }
