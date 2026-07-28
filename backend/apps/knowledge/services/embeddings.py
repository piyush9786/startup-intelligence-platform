from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import httpx
from django.conf import settings


class EmbeddingProviderError(RuntimeError):
    """Base error raised by the embedding provider."""


class EmbeddingProviderUnavailableError(EmbeddingProviderError):
    """Raised when the embedding service cannot be reached."""


class EmbeddingProviderResponseError(EmbeddingProviderError):
    """Raised when the embedding service returns an invalid response."""


@dataclass(frozen=True)
class EmbeddingBatch:
    vectors: list[list[float]]
    model_name: str
    dimension: int


class OllamaEmbeddingProvider:
    provider_name = "ollama"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model_name: str | None = None,
        timeout_seconds: float | None = None,
        keep_alive: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model_name = (
            model_name or settings.STARTUP_ADVISOR_EMBEDDING_MODEL
        )
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.STARTUP_ADVISOR_EMBEDDING_TIMEOUT_SECONDS
        )
        self.keep_alive = (
            keep_alive
            if keep_alive is not None
            else settings.STARTUP_ADVISOR_EMBEDDING_KEEP_ALIVE
        )
        self._client = client

    def embed(self, texts: Sequence[str]) -> EmbeddingBatch:
        values = [str(text).strip() for text in texts]
        if not values or any(not value for value in values):
            raise EmbeddingProviderResponseError(
                "Embedding input must contain non-empty text."
            )

        payload = {
            "model": self.model_name,
            "input": values,
            "truncate": True,
            "keep_alive": self.keep_alive,
        }

        try:
            if self._client is not None:
                response = self._client.post(
                    f"{self.base_url}/api/embed",
                    json=payload,
                    timeout=self.timeout_seconds,
                )
            else:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(
                        f"{self.base_url}/api/embed",
                        json=payload,
                    )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise EmbeddingProviderUnavailableError(
                f"Ollama embedding request failed: {exc}"
            ) from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise EmbeddingProviderResponseError(
                "Ollama embedding response was not valid JSON."
            ) from exc

        vectors = body.get("embeddings")
        if not isinstance(vectors, list) or len(vectors) != len(values):
            raise EmbeddingProviderResponseError(
                "Ollama embedding response did not contain one vector per input."
            )

        normalized_vectors: list[list[float]] = []
        dimension = 0
        for vector in vectors:
            if not isinstance(vector, list) or not vector:
                raise EmbeddingProviderResponseError(
                    "Ollama returned an empty or invalid embedding vector."
                )
            try:
                normalized = [float(item) for item in vector]
            except (TypeError, ValueError) as exc:
                raise EmbeddingProviderResponseError(
                    "Ollama returned a non-numeric embedding vector."
                ) from exc

            if dimension == 0:
                dimension = len(normalized)
            elif len(normalized) != dimension:
                raise EmbeddingProviderResponseError(
                    "Ollama returned vectors with inconsistent dimensions."
                )
            normalized_vectors.append(normalized)

        return EmbeddingBatch(
            vectors=normalized_vectors,
            model_name=self.model_name,
            dimension=dimension,
        )


def get_embedding_provider() -> OllamaEmbeddingProvider:
    return OllamaEmbeddingProvider()
