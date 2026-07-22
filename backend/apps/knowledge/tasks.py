from celery import shared_task

from apps.documents.models import DocumentExtraction

from .services import extract_knowledge, index_document_extraction


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def extract_knowledge_task(extraction_id: str, force: bool = False) -> dict:
    extraction = DocumentExtraction.objects.get(pk=extraction_id)
    result = extract_knowledge(extraction, force=force)
    return {
        "run_id": str(result.run.id),
        "candidate_count": result.candidate_count,
        "unchanged": result.unchanged,
    }

@shared_task(
    autoretry_for=(RuntimeError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def index_document_extraction_task(
    extraction_id: str,
    force: bool = False,
) -> dict:
    extraction = DocumentExtraction.objects.get(pk=extraction_id)
    result = index_document_extraction(
        extraction,
        force=force,
    )
    return {
        "run_id": str(result.run.id),
        "embedded_count": result.embedded_count,
        "unchanged": result.unchanged,
        "skipped": result.skipped,
    }
