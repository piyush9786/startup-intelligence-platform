"""Validate the local Ollama, structured generation, and embedding path."""
from __future__ import annotations

import json
from time import monotonic
from typing import Any

import httpx
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.startups.services.llm_provider import (
    LLMProviderError,
    get_startup_advisor_llm_provider,
)


def _installed_model_names(payload: Any) -> set[str]:
    if not isinstance(payload, dict):
        return set()

    names: set[str] = set()
    for item in payload.get("models") or []:
        if not isinstance(item, dict):
            continue
        for key in ("name", "model"):
            value = str(item.get(key) or "").strip()
            if value:
                names.add(value)
    return names


def _model_available(required: str, installed: set[str]) -> bool:
    if required in installed:
        return True
    if ":" not in required:
        return any(name.startswith(f"{required}:") for name in installed)
    return False


class Command(BaseCommand):
    help = "Validate Ollama models and run a structured local generation test."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-generation",
            action="store_true",
            help="Check installation and embeddings without warming the generation model.",
        )

    def handle(self, *args, **options):
        base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        timeout = httpx.Timeout(30.0, connect=10.0)

        try:
            response = httpx.get(f"{base_url}/api/tags", timeout=timeout)
            response.raise_for_status()
            installed = _installed_model_names(response.json())
        except (httpx.HTTPError, ValueError) as exc:
            raise CommandError(f"Ollama is unavailable at {base_url}: {exc}") from exc

        required = {
            settings.STARTUP_ADVISOR_LLM_MODEL,
            settings.CHATBOT_LLM_MODEL,
        }
        if settings.STARTUP_ADVISOR_RAG_ENABLED or settings.RESEARCH_VECTOR_RAG_ENABLED:
            required.add(settings.STARTUP_ADVISOR_EMBEDDING_MODEL)

        missing = sorted(
            model for model in required if not _model_available(model, installed)
        )
        self.stdout.write(f"ollama=ok")
        self.stdout.write(f"installed_models={len(installed)}")
        self.stdout.write(f"advisor_model={settings.STARTUP_ADVISOR_LLM_MODEL}")
        self.stdout.write(f"context_length={settings.OLLAMA_CONTEXT_LENGTH}")
        self.stdout.write(f"temperature={settings.STARTUP_ADVISOR_LLM_TEMPERATURE}")
        if missing:
            raise CommandError("Missing Ollama models: " + ", ".join(missing))

        if settings.STARTUP_ADVISOR_RAG_ENABLED or settings.RESEARCH_VECTOR_RAG_ENABLED:
            try:
                embed_response = httpx.post(
                    f"{base_url}/api/embed",
                    json={
                        "model": settings.STARTUP_ADVISOR_EMBEDDING_MODEL,
                        "input": "startup funding eligibility evidence",
                        "truncate": True,
                        "keep_alive": settings.STARTUP_ADVISOR_EMBEDDING_KEEP_ALIVE,
                    },
                    timeout=httpx.Timeout(
                        settings.STARTUP_ADVISOR_EMBEDDING_TIMEOUT_SECONDS,
                        connect=10.0,
                    ),
                )
                embed_response.raise_for_status()
                embed_payload = embed_response.json()
                vector = (embed_payload.get("embeddings") or [[]])[0]
            except (httpx.HTTPError, ValueError, IndexError, TypeError) as exc:
                raise CommandError(f"Embedding test failed: {exc}") from exc
            if not vector:
                raise CommandError("Embedding test returned an empty vector.")
            self.stdout.write(
                f"embedding_model={settings.STARTUP_ADVISOR_EMBEDDING_MODEL}"
            )
            self.stdout.write(f"embedding_dimensions={len(vector)}")

        if options["skip_generation"]:
            self.stdout.write(self.style.SUCCESS("LLM installation checks passed."))
            return

        provider = get_startup_advisor_llm_provider()
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "status": {"type": "string", "enum": ["ok"]},
                "message": {"type": "string"},
            },
            "required": ["status", "message"],
        }
        started = monotonic()
        try:
            result = provider.generate(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Return only the JSON object required by the supplied schema. "
                            "Do not include markdown or analysis."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "Confirm that the local startup advisor model is ready. "
                            "Set status to ok and use a short message."
                        ),
                    },
                ],
                response_schema=schema,
            )
        except LLMProviderError as exc:
            raise CommandError(f"Structured generation test failed: {exc}") from exc

        if result.payload.get("status") != "ok":
            raise CommandError(
                "Structured generation returned an unexpected payload: "
                + json.dumps(result.payload, ensure_ascii=False)
            )

        elapsed = monotonic() - started
        self.stdout.write(f"generation_seconds={elapsed:.2f}")
        self.stdout.write(f"prompt_tokens={result.prompt_token_count}")
        self.stdout.write(f"output_tokens={result.output_token_count}")
        self.stdout.write(
            self.style.SUCCESS("Local LLM structured-generation test passed.")
        )
