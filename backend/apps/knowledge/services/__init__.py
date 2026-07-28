from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

from .embeddings import (
    EmbeddingBatch,
    EmbeddingProviderError,
    EmbeddingProviderResponseError,
    EmbeddingProviderUnavailableError,
    OllamaEmbeddingProvider,
    get_embedding_provider,
)
from .extractor import KnowledgeExtractionResult, extract_knowledge
from .vector_search import (
    EmbeddingIndexResult,
    RetrievedDocumentChunk,
    VectorSearchError,
    VectorSearchUnavailableError,
    index_document_extraction,
    search_document_chunks as _search_document_chunks,
)

_STARTUP_PROFILE_VECTOR_SCOPE: ContextVar[str | None] = ContextVar(
    "startup_profile_vector_scope",
    default=None,
)


@contextmanager
def startup_profile_vector_scope(
    startup_profile_id: str,
) -> Iterator[None]:
    """Bind private vector retrieval to one startup for this execution."""
    normalized = str(startup_profile_id or "").strip()
    if not normalized:
        raise ValueError("A startup profile ID is required for vector retrieval.")

    token = _STARTUP_PROFILE_VECTOR_SCOPE.set(normalized)
    try:
        yield
    finally:
        _STARTUP_PROFILE_VECTOR_SCOPE.reset(token)


def search_document_chunks(
    query: str,
    *,
    top_k: int | None = None,
    min_score: float | None = None,
    startup_profile_id: str | None = None,
    provider: Any = None,
    client: Any = None,
) -> list[RetrievedDocumentChunk]:
    """Require explicit or execution-scoped ownership for private RAG."""
    effective_profile_id = (
        str(startup_profile_id).strip()
        if startup_profile_id is not None
        else (_STARTUP_PROFILE_VECTOR_SCOPE.get() or "")
    )
    if not effective_profile_id:
        raise VectorSearchUnavailableError(
            "Startup-scoped vector retrieval requires a startup profile ID."
        )

    return _search_document_chunks(
        query,
        top_k=top_k,
        min_score=min_score,
        startup_profile_id=effective_profile_id,
        provider=provider,
        client=client,
    )


__all__ = (
    "EmbeddingBatch",
    "EmbeddingIndexResult",
    "EmbeddingProviderError",
    "EmbeddingProviderResponseError",
    "EmbeddingProviderUnavailableError",
    "KnowledgeExtractionResult",
    "OllamaEmbeddingProvider",
    "RetrievedDocumentChunk",
    "VectorSearchError",
    "VectorSearchUnavailableError",
    "extract_knowledge",
    "get_embedding_provider",
    "index_document_extraction",
    "search_document_chunks",
    "startup_profile_vector_scope",
)
