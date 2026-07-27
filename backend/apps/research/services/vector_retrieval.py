"""Owner-scoped Qdrant retrieval for startup document evidence."""
from __future__ import annotations

import hashlib
import logging
from typing import Any

import httpx
from django.conf import settings
from qdrant_client import QdrantClient
from qdrant_client import models as qdrant_models

logger = logging.getLogger(__name__)


class VectorRetrievalError(RuntimeError):
    """Raised when configured vector retrieval cannot complete safely."""


def _generate_query_embedding(query: str) -> list[float]:
    timeout_seconds = float(
        settings.STARTUP_ADVISOR_EMBEDDING_TIMEOUT_SECONDS,
    )
    try:
        with httpx.Client(
            timeout=httpx.Timeout(
                timeout_seconds,
                connect=min(10.0, timeout_seconds),
            ),
        ) as client:
            response = client.post(
                f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/embed",
                json={
                    "model": settings.STARTUP_ADVISOR_EMBEDDING_MODEL,
                    "input": query,
                    "truncate": True,
                },
            )
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise VectorRetrievalError(
            "The embedding request timed out.",
        ) from exc
    except httpx.HTTPError as exc:
        raise VectorRetrievalError(
            "The embedding service is unavailable.",
        ) from exc

    try:
        payload = response.json()
        embeddings = payload["embeddings"]
        embedding = embeddings[0]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise VectorRetrievalError(
            "The embedding service returned an invalid response.",
        ) from exc

    if not embedding or not all(
        isinstance(value, int | float) for value in embedding
    ):
        raise VectorRetrievalError(
            "The embedding service returned an invalid vector.",
        )
    return [float(value) for value in embedding]


def _build_qdrant_client() -> QdrantClient:
    api_key = str(getattr(settings, "QDRANT_API_KEY", "")).strip()
    return QdrantClient(
        url=settings.QDRANT_URL,
        api_key=api_key or None,
        timeout=float(
            settings.STARTUP_ADVISOR_QDRANT_TIMEOUT_SECONDS,
        ),
    )


def _payload_text(payload: dict[str, Any]) -> str:
    for key in (
        "content",
        "text",
        "chunk_text",
        "page_content",
        "content_excerpt",
    ):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _payload_source_url(
    payload: dict[str, Any],
    *,
    point_id: Any,
) -> str:
    for key in ("source_url", "url", "document_url"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    document_id = payload.get("document_id") or payload.get(
        "source_document_id",
    )
    chunk_index = payload.get("chunk_index")
    if document_id:
        suffix = (
            f"#chunk={chunk_index}"
            if chunk_index is not None
            else ""
        )
        return f"internal://startup-documents/{document_id}{suffix}"
    return f"internal://qdrant-points/{point_id}"


def retrieve_startup_vector_evidence(
    *,
    startup_profile_id: str,
    query: str,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """Retrieve only vector chunks belonging to the selected startup."""
    clean_query = " ".join(query.split())
    if not clean_query:
        return []

    embedding = _generate_query_embedding(clean_query)
    profile_field = str(
        getattr(
            settings,
            "STARTUP_ADVISOR_QDRANT_PROFILE_FIELD",
            "startup_profile_id",
        )
    ).strip()
    if not profile_field:
        raise VectorRetrievalError(
            "The startup profile payload field is not configured.",
        )
    expected_profile_id = str(startup_profile_id)
    limit = max(
        1,
        int(top_k or settings.STARTUP_ADVISOR_RAG_TOP_K),
    )

    client = _build_qdrant_client()
    try:
        response = client.query_points(
            collection_name=(
                settings.STARTUP_ADVISOR_QDRANT_COLLECTION
            ),
            query=embedding,
            query_filter=qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key=profile_field,
                        match=qdrant_models.MatchValue(
                            value=expected_profile_id,
                        ),
                    )
                ]
            ),
            limit=limit,
            score_threshold=float(
                settings.STARTUP_ADVISOR_RAG_MIN_SCORE,
            ),
            with_payload=True,
            with_vectors=False,
        )
    except Exception as exc:
        logger.warning(
            "Qdrant retrieval failed for startup profile %s: %s",
            startup_profile_id,
            exc,
        )
        raise VectorRetrievalError(
            "The vector knowledge store is unavailable.",
        ) from exc
    finally:
        client.close()

    evidence: list[dict[str, Any]] = []
    for point in response.points:
        payload = dict(point.payload or {})
        if str(payload.get(profile_field, "")) != expected_profile_id:
            logger.warning(
                "Discarded Qdrant point %s with mismatched startup profile",
                point.id,
            )
            continue

        content = _payload_text(payload)
        if not content:
            continue

        title = str(
            payload.get("title")
            or payload.get("filename")
            or payload.get("document_name")
            or "Startup document evidence"
        ).strip()
        source_url = _payload_source_url(
            payload,
            point_id=point.id,
        )
        content_hash = str(
            payload.get("content_hash")
            or hashlib.sha256(content.encode("utf-8")).hexdigest()
        )

        evidence.append(
            {
                "title": title,
                "url": source_url,
                "publisher": "founder_document",
                "published_at": str(
                    payload.get("published_at")
                    or payload.get("captured_at")
                    or ""
                ),
                "source_type": "verified_internal",
                "content_excerpt": content[:1800],
                "content_hash": content_hash,
                "confidence_score": float(point.score or 0.0),
                "verification_status": "verified_internal",
            }
        )

    return evidence
