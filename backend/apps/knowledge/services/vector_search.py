from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote, urlparse
from uuid import NAMESPACE_URL, uuid5

from django.conf import settings
from django.utils import timezone
from qdrant_client import QdrantClient, models

from apps.documents.models import DocumentChunk, DocumentExtraction
from apps.knowledge.models import EmbeddingRun

from .embeddings import OllamaEmbeddingProvider, get_embedding_provider

VECTOR_PAYLOAD_VERSION = "document-chunk-payload-v1"


class VectorSearchError(RuntimeError):
    """Base error for Qdrant indexing and retrieval."""


class VectorSearchUnavailableError(VectorSearchError):
    """Raised when Qdrant or the embedding provider is unavailable."""


@dataclass(frozen=True)
class EmbeddingIndexResult:
    run: EmbeddingRun
    embedded_count: int
    unchanged: bool
    skipped: bool


@dataclass(frozen=True)
class RetrievedDocumentChunk:
    chunk_id: str
    score: float
    text: str
    source_url: str
    title: str
    page_number: int | None
    heading: str
    extraction_id: str
    document_id: str

    def as_prompt_document(self) -> dict[str, Any]:
        return {
            "id": self.chunk_id,
            "score": round(self.score, 6),
            "text": self.text,
            "source_url": self.source_url,
            "title": self.title,
            "page_number": self.page_number,
            "heading": self.heading,
            "extraction_id": self.extraction_id,
            "document_id": self.document_id,
        }


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(
        url=settings.QDRANT_URL,
        timeout=settings.STARTUP_ADVISOR_QDRANT_TIMEOUT_SECONDS,
    )


def _point_id(extraction_id: str, chunk_index: int) -> str:
    return str(
        uuid5(
            NAMESPACE_URL,
            f"startup-document-chunk:{extraction_id}:{chunk_index}",
        )
    )


def _chunks_for_extraction(
    extraction: DocumentExtraction,
) -> list[DocumentChunk]:
    return list(
        extraction.chunks.select_related(
            "extraction",
            "extraction__source_document",
            "extraction__source_document__source",
        ).order_by("chunk_index")
    )


def _batches(
    values: Sequence[DocumentChunk],
    size: int,
) -> Iterable[Sequence[DocumentChunk]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def _ensure_collection(
    client: QdrantClient,
    *,
    collection_name: str,
    dimension: int,
) -> None:
    try:
        if not client.collection_exists(collection_name):
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=dimension,
                    distance=models.Distance.COSINE,
                ),
            )
    except Exception as exc:
        raise VectorSearchUnavailableError(
            f"Qdrant collection setup failed: {exc}"
        ) from exc


def _delete_existing_extraction_points(
    client: QdrantClient,
    *,
    collection_name: str,
    extraction_id: str,
) -> None:
    selector = models.FilterSelector(
        filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="extraction_id",
                    match=models.MatchValue(value=extraction_id),
                )
            ]
        )
    )
    try:
        client.delete(
            collection_name=collection_name,
            points_selector=selector,
            wait=True,
        )
    except Exception as exc:
        raise VectorSearchUnavailableError(
            f"Qdrant cleanup failed: {exc}"
        ) from exc



def _readable_document_title(
    extraction: DocumentExtraction,
    document,
) -> str:
    supplied = (
        extraction.detected_title
        or document.title
        or ""
    ).strip()
    if supplied and not supplied.lower().startswith(
        ("http://", "https://")
    ):
        return supplied

    source_url = (
        document.final_url
        or document.source_url
        or supplied
    )
    try:
        filename = unquote(
            urlparse(source_url).path.rsplit("/", 1)[-1]
        )
    except ValueError:
        filename = ""

    cleaned = re.sub(
        r"\.(pdf|html?|aspx?)$",
        "",
        filename,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"[_-]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")

    return cleaned or "Official source document"


def _point_for_chunk(
    *,
    chunk: DocumentChunk,
    vector: list[float],
) -> models.PointStruct:
    extraction = chunk.extraction
    document = extraction.source_document
    return models.PointStruct(
        id=_point_id(str(extraction.id), chunk.chunk_index),
        vector=vector,
        payload={
            "payload_version": VECTOR_PAYLOAD_VERSION,
            "chunk_id": str(chunk.id),
            "chunk_index": chunk.chunk_index,
            "extraction_id": str(extraction.id),
            "document_id": str(document.id),
            "source_id": str(document.source_id),
            "source_url": document.final_url or document.source_url,
            "title": _readable_document_title(
                extraction,
                document,
            ),
            "page_number": chunk.page_number,
            "heading": chunk.heading,
            "text": chunk.text,
            "text_hash": chunk.text_hash,
            "retrieved_at": document.retrieved_at.isoformat(),
            "usable_for_rag": True,
        },
    )


def index_document_extraction(
    extraction: DocumentExtraction,
    *,
    force: bool = False,
    provider: OllamaEmbeddingProvider | None = None,
    client: QdrantClient | None = None,
) -> EmbeddingIndexResult:
    if extraction.status != DocumentExtraction.Status.SUCCEEDED:
        raise VectorSearchError(
            "Only successful document extractions can be indexed."
        )

    embedding_version = settings.STARTUP_ADVISOR_EMBEDDING_VERSION
    model_name = settings.STARTUP_ADVISOR_EMBEDDING_MODEL
    collection_name = settings.STARTUP_ADVISOR_QDRANT_COLLECTION

    run, _created = EmbeddingRun.objects.get_or_create(
        extraction=extraction,
        model_name=model_name,
        embedding_version=embedding_version,
        defaults={
            "provider": "ollama",
            "collection_name": collection_name,
        },
    )

    if run.status == EmbeddingRun.Status.SUCCEEDED and not force:
        return EmbeddingIndexResult(
            run=run,
            embedded_count=run.embedded_count,
            unchanged=True,
            skipped=False,
        )

    quality = getattr(extraction, "quality_assessment", None)
    if quality is None or not quality.usable_for_rag:
        now = timezone.now()
        run.status = EmbeddingRun.Status.SKIPPED
        run.chunk_count = extraction.chunk_count
        run.embedded_count = 0
        run.started_at = now
        run.finished_at = now
        run.error_message = ""
        run.metadata = {
            "reason": "Document quality assessment is not RAG eligible.",
        }
        run.save()
        return EmbeddingIndexResult(
            run=run,
            embedded_count=0,
            unchanged=False,
            skipped=True,
        )

    chunks = _chunks_for_extraction(extraction)
    if not chunks:
        raise VectorSearchError(
            "The extraction does not contain any document chunks."
        )

    active_provider = provider or get_embedding_provider()
    active_client = client or get_qdrant_client()

    run.provider = active_provider.provider_name
    run.collection_name = collection_name
    run.status = EmbeddingRun.Status.RUNNING
    run.chunk_count = len(chunks)
    run.embedded_count = 0
    run.vector_size = 0
    run.started_at = timezone.now()
    run.finished_at = None
    run.error_message = ""
    run.metadata = {
        "payload_version": VECTOR_PAYLOAD_VERSION,
        "batch_size": settings.STARTUP_ADVISOR_EMBEDDING_BATCH_SIZE,
    }
    run.save()

    embedded_count = 0
    try:
        first_batch = True
        for chunk_batch in _batches(
            chunks,
            settings.STARTUP_ADVISOR_EMBEDDING_BATCH_SIZE,
        ):
            embedded = active_provider.embed(
                [chunk.text for chunk in chunk_batch]
            )
            if first_batch:
                _ensure_collection(
                    active_client,
                    collection_name=collection_name,
                    dimension=embedded.dimension,
                )
                _delete_existing_extraction_points(
                    active_client,
                    collection_name=collection_name,
                    extraction_id=str(extraction.id),
                )
                run.vector_size = embedded.dimension
                first_batch = False

            points = [
                _point_for_chunk(
                    chunk=chunk,
                    vector=vector,
                )
                for chunk, vector in zip(
                    chunk_batch,
                    embedded.vectors,
                    strict=True,
                )
            ]
            active_client.upsert(
                collection_name=collection_name,
                points=points,
                wait=True,
            )
            embedded_count += len(points)
            run.embedded_count = embedded_count
            run.save(
                update_fields=[
                    "embedded_count",
                    "updated_at",
                ]
            )

        run.status = EmbeddingRun.Status.SUCCEEDED
        run.finished_at = timezone.now()
        run.error_message = ""
        run.save()
    except Exception as exc:
        run.status = EmbeddingRun.Status.FAILED
        run.finished_at = timezone.now()
        run.error_message = str(exc)[:5000]
        run.save()
        if isinstance(exc, VectorSearchError):
            raise
        raise VectorSearchUnavailableError(
            f"Embedding index failed: {exc}"
        ) from exc

    return EmbeddingIndexResult(
        run=run,
        embedded_count=embedded_count,
        unchanged=False,
        skipped=False,
    )


def _scored_points(response: Any) -> list[Any]:
    points = getattr(response, "points", None)
    if points is not None:
        return list(points)
    if isinstance(response, list):
        return response
    return []


def search_document_chunks(
    query: str,
    *,
    top_k: int | None = None,
    min_score: float | None = None,
    provider: OllamaEmbeddingProvider | None = None,
    client: QdrantClient | None = None,
) -> list[RetrievedDocumentChunk]:
    normalized_query = str(query or "").strip()
    if not normalized_query:
        return []

    active_provider = provider or get_embedding_provider()
    active_client = client or get_qdrant_client()
    limit = top_k or settings.STARTUP_ADVISOR_RAG_TOP_K
    threshold = (
        min_score
        if min_score is not None
        else settings.STARTUP_ADVISOR_RAG_MIN_SCORE
    )

    try:
        embedded = active_provider.embed([normalized_query])
        response = active_client.query_points(
            collection_name=settings.STARTUP_ADVISOR_QDRANT_COLLECTION,
            query=embedded.vectors[0],
            limit=limit,
            score_threshold=threshold,
            with_payload=True,
        )
    except Exception as exc:
        raise VectorSearchUnavailableError(
            f"Vector retrieval failed: {exc}"
        ) from exc

    results: list[RetrievedDocumentChunk] = []
    for point in _scored_points(response):
        payload = getattr(point, "payload", None) or {}
        chunk_id = str(payload.get("chunk_id") or "")
        text = str(payload.get("text") or "").strip()
        if not chunk_id or not text:
            continue
        results.append(
            RetrievedDocumentChunk(
                chunk_id=chunk_id,
                score=float(getattr(point, "score", 0.0)),
                text=text,
                source_url=str(payload.get("source_url") or ""),
                title=str(payload.get("title") or ""),
                page_number=payload.get("page_number"),
                heading=str(payload.get("heading") or ""),
                extraction_id=str(payload.get("extraction_id") or ""),
                document_id=str(payload.get("document_id") or ""),
            )
        )
    return results
