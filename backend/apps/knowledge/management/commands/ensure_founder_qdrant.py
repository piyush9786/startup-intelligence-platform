"""Create the founder-document Qdrant collection with the real embedding size."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def _setting_or_env(names, default):
    for name in names:
        value = getattr(settings, name, None)
        if value not in (None, ""):
            return str(value)
        value = os.environ.get(name)
        if value:
            return value
    return default


def _json_request(url, *, method="GET", payload=None, timeout=60):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(
        request,
        timeout=timeout,
    ) as response:
        raw = response.read()
        return (
            json.loads(raw.decode("utf-8"))
            if raw
            else {}
        )


class Command(BaseCommand):
    help = (
        "Ensure startup_founder_document_chunks_v1 exists "
        "using the actual Ollama embedding dimension."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--collection",
            default=(
                "startup_founder_document_chunks_v1"
            ),
        )
        parser.add_argument(
            "--distance",
            default="Cosine",
            choices=[
                "Cosine",
                "Dot",
                "Euclid",
                "Manhattan",
            ],
        )

    def handle(self, *args, **options):
        qdrant_url = _setting_or_env(
            [
                "QDRANT_URL",
                "QDRANT_BASE_URL",
            ],
            "http://qdrant:6333",
        ).rstrip("/")

        ollama_url = _setting_or_env(
            [
                "OLLAMA_BASE_URL",
            ],
            "http://host.docker.internal:11434",
        ).rstrip("/")

        embedding_model = _setting_or_env(
            [
                "OLLAMA_EMBEDDING_MODEL",
                "EMBEDDING_MODEL",
                "RAG_EMBEDDING_MODEL",
                "KNOWLEDGE_EMBEDDING_MODEL",
            ],
            "embeddinggemma",
        )

        collection = options["collection"]
        collection_url = (
            f"{qdrant_url}/collections/{collection}"
        )

        try:
            current = _json_request(
                collection_url,
                timeout=10,
            )
            result = current.get("result") or {}
            vectors = (
                (result.get("config") or {})
                .get("params", {})
                .get("vectors")
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Collection already exists: "
                    f"{collection}"
                )
            )
            self.stdout.write(
                f"Current vector config: {vectors}"
            )
            return
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise CommandError(
                    f"Qdrant check failed: {exc}"
                ) from exc
        except Exception as exc:
            raise CommandError(
                f"Cannot reach Qdrant at "
                f"{qdrant_url}: {exc}"
            ) from exc

        try:
            embed = _json_request(
                f"{ollama_url}/api/embed",
                method="POST",
                payload={
                    "model": embedding_model,
                    "input": (
                        "startup intelligence "
                        "vector dimension probe"
                    ),
                },
                timeout=120,
            )
            vectors = embed.get("embeddings") or []
            vector = vectors[0] if vectors else []
            dimension = len(vector)
        except Exception as exc:
            raise CommandError(
                f"Cannot obtain embedding from "
                f"{embedding_model}: {exc}"
            ) from exc

        if dimension <= 0:
            raise CommandError(
                "Ollama returned an empty embedding."
            )

        self.stdout.write(
            f"Embedding model: {embedding_model}"
        )
        self.stdout.write(
            f"Detected dimension: {dimension}"
        )

        try:
            _json_request(
                collection_url,
                method="PUT",
                payload={
                    "vectors": {
                        "size": dimension,
                        "distance": options["distance"],
                    },
                    "on_disk_payload": True,
                },
                timeout=30,
            )
        except Exception as exc:
            raise CommandError(
                f"Could not create collection: {exc}"
            ) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {collection} "
                f"({dimension}D, "
                f"{options['distance']})."
            )
        )
        self.stdout.write(
            "The collection is now valid but empty; "
            "existing document-ingestion/indexing flows "
            "should populate it."
        )
