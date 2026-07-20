from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.documents.models import DocumentChunk, DocumentExtraction
from apps.sources.models import SourceDocument
from apps.sources.services.storage import download_bytes, upload_bytes

from .chunker import build_chunks
from .extractors import extract_document
from .normalizer import word_count


class ProcessingError(RuntimeError):
    """Raised when a collected document cannot be processed."""


@dataclass(frozen=True)
class ProcessingResult:
    extraction: DocumentExtraction
    created: bool
    unchanged: bool


def _processed_object_key(
    document: SourceDocument,
    extractor_version: str,
    text_hash: str,
) -> str:
    date_path = datetime.now(UTC).strftime("%Y/%m/%d")
    return (
        f"processed/{document.source_id}/{date_path}/"
        f"{document.id}/{extractor_version}/{text_hash}.txt"
    )


def process_document(
    document: SourceDocument,
    *,
    force: bool = False,
    extractor_version: str | None = None,
) -> ProcessingResult:
    version = extractor_version or settings.DOCUMENT_EXTRACTOR_VERSION
    existing = DocumentExtraction.objects.filter(
        source_document=document,
        extractor_version=version,
        status=DocumentExtraction.Status.SUCCEEDED,
    ).first()
    if existing and not force:
        return ProcessingResult(
            extraction=existing,
            created=False,
            unchanged=True,
        )

    extraction, created = DocumentExtraction.objects.get_or_create(
        source_document=document,
        extractor_version=version,
        defaults={"status": DocumentExtraction.Status.PENDING},
    )
    extraction.status = DocumentExtraction.Status.RUNNING
    extraction.started_at = timezone.now()
    extraction.finished_at = None
    extraction.error_message = ""
    extraction.save(
        update_fields=[
            "status",
            "started_at",
            "finished_at",
            "error_message",
            "updated_at",
        ]
    )

    try:
        raw_content = download_bytes(document.storage_key)
        payload = extract_document(raw_content, document.mime_type)
        normalized_text = payload.combined_text
        if not normalized_text:
            raise ProcessingError("Extraction produced empty normalized text.")

        text_hash = hashlib.sha256(normalized_text.encode("utf-8", errors="replace")).hexdigest()
        chunks = build_chunks(
            payload.sections,
            max_chars=settings.DOCUMENT_CHUNK_MAX_CHARS,
            overlap_chars=settings.DOCUMENT_CHUNK_OVERLAP_CHARS,
            max_chunks=settings.DOCUMENT_MAX_CHUNKS,
        )
        if not chunks:
            raise ProcessingError("Extraction produced no usable chunks.")

        object_key = _processed_object_key(document, version, text_hash)
        upload_bytes(
            object_key=object_key,
            content=normalized_text.encode("utf-8", errors="replace"),
            content_type="text/plain; charset=utf-8",
            bucket_name=settings.MINIO_BUCKET_PROCESSED,
        )

        with transaction.atomic():
            extraction.chunks.all().delete()
            DocumentChunk.objects.bulk_create(
                [
                    DocumentChunk(
                        extraction=extraction,
                        chunk_index=item.chunk_index,
                        heading=item.heading,
                        page_number=item.page_number,
                        text=item.text,
                        text_hash=item.text_hash,
                        character_start=item.character_start,
                        character_end=item.character_end,
                        token_estimate=item.token_estimate,
                        metadata=item.metadata,
                    )
                    for item in chunks
                ]
            )
            extraction.status = DocumentExtraction.Status.SUCCEEDED
            extraction.detected_title = payload.title[:500]
            extraction.language = document.source.language
            extraction.text_storage_key = object_key
            extraction.text_preview = normalized_text[:2000]
            extraction.text_hash = text_hash
            extraction.page_count = payload.page_count
            extraction.section_count = len(payload.sections)
            extraction.chunk_count = len(chunks)
            extraction.word_count = word_count(normalized_text)
            extraction.character_count = len(normalized_text)
            extraction.finished_at = timezone.now()
            extraction.metadata = payload.metadata
            extraction.error_message = ""
            extraction.save()

            document.status = SourceDocument.Status.EXTRACTED
            document.extractor_version = version
            document.metadata = {
                **(document.metadata or {}),
                "latest_extraction_id": str(extraction.id),
                "processed_text_hash": text_hash,
                "processed_chunk_count": len(chunks),
            }
            document.save(
                update_fields=[
                    "status",
                    "extractor_version",
                    "metadata",
                    "updated_at",
                ]
            )

        # automatic_quality_assessment
        try:
            from apps.discovery.services.quality import assess_extraction

            assess_extraction(extraction)
        except Exception as quality_error:
            extraction.metadata = {
                **(extraction.metadata or {}),
                "quality_assessment_warning": str(quality_error)[:1000],
            }
            extraction.save(update_fields=["metadata", "updated_at"])

        return ProcessingResult(
            extraction=extraction,
            created=created,
            unchanged=False,
        )
    except Exception as exc:
        extraction.status = DocumentExtraction.Status.FAILED
        extraction.finished_at = timezone.now()
        extraction.error_message = str(exc)[:5000]
        extraction.save(
            update_fields=[
                "status",
                "finished_at",
                "error_message",
                "updated_at",
            ]
        )
        document.status = SourceDocument.Status.FAILED
        document.metadata = {
            **(document.metadata or {}),
            "processing_error": str(exc)[:1000],
        }
        document.save(update_fields=["status", "metadata", "updated_at"])
        raise ProcessingError(str(exc)) from exc
