from __future__ import annotations

from typing import Any

import httpx
from django.conf import settings
from django.db import connection
from redis import Redis
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


def _clean_models(models: list[Any]) -> list[str]:
    return sorted(
        {
            str(model).strip()
            for model in models
            if str(model or "").strip()
        }
    )


def _capability_models() -> dict[str, dict[str, Any]]:
    advisor_models: list[Any] = [settings.STARTUP_ADVISOR_LLM_MODEL]
    if settings.STARTUP_ADVISOR_RAG_ENABLED:
        advisor_models.append(settings.STARTUP_ADVISOR_EMBEDDING_MODEL)

    chatbot_enabled = bool(settings.CHATBOT_LLM_ENABLED)
    chatbot_models = [settings.CHATBOT_LLM_MODEL] if chatbot_enabled else []

    research_enabled = bool(settings.RESEARCH_VECTOR_RAG_ENABLED)
    research_models = (
        [settings.STARTUP_ADVISOR_EMBEDDING_MODEL]
        if research_enabled
        else []
    )

    return {
        "advisor": {
            "enabled": True,
            "required_models": _clean_models(advisor_models),
        },
        "chatbot": {
            "enabled": chatbot_enabled,
            "required_models": _clean_models(chatbot_models),
        },
        "research_vector": {
            "enabled": research_enabled,
            "required_models": _clean_models(research_models),
        },
    }


def _installed_ollama_models(payload: Any) -> set[str]:
    if not isinstance(payload, dict):
        return set()

    installed: set[str] = set()
    for model in payload.get("models") or []:
        if not isinstance(model, dict):
            continue
        for key in ("name", "model"):
            value = str(model.get(key) or "").strip()
            if value:
                installed.add(value)
    return installed


def _model_is_installed(required: str, installed: set[str]) -> bool:
    if required in installed:
        return True
    if ":" not in required:
        return any(item.startswith(f"{required}:") for item in installed)
    return False


def _capability_statuses(
    *,
    installed_models: set[str],
    ollama_available: bool,
) -> dict[str, dict[str, Any]]:
    statuses: dict[str, dict[str, Any]] = {}

    for name, config in _capability_models().items():
        required = config["required_models"]
        missing = (
            [
                model
                for model in required
                if not _model_is_installed(model, installed_models)
            ]
            if ollama_available
            else list(required)
        )
        enabled = bool(config["enabled"])

        statuses[name] = {
            "enabled": enabled,
            "ready": (not enabled) or (ollama_available and not missing),
            "required_models": required,
            "missing_models": missing,
            "reason": (
                ""
                if (not enabled) or (ollama_available and not missing)
                else (
                    "The Ollama service is unavailable."
                    if not ollama_available
                    else "One or more required Ollama models are not installed."
                )
            ),
        }

    return statuses


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            database_ok = cursor.fetchone()[0] == 1
        return Response({"status": "ok", "database": database_ok})


class AIReadinessView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        endpoint = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags"
        ollama_available = False
        installed_models: set[str] = set()

        try:
            response = httpx.get(endpoint, timeout=5.0)
            response.raise_for_status()
            installed_models = _installed_ollama_models(response.json())
            ollama_available = True
        except (httpx.HTTPError, ValueError):
            pass

        capabilities = _capability_statuses(
            installed_models=installed_models,
            ollama_available=ollama_available,
        )
        advisor = capabilities["advisor"]

        # Backward-compatible top-level fields represent founder-advisor
        # readiness only. An unavailable chatbot must not disable guidance.
        return Response(
            {
                "ready": advisor["ready"],
                "ollama": ollama_available,
                "required_models": advisor["required_models"],
                "missing_models": advisor["missing_models"],
                "reason": advisor["reason"],
                "capabilities": capabilities,
            }
        )


class PlatformStatusView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        redis_ok = False
        try:
            redis_ok = bool(Redis.from_url(settings.CELERY_BROKER_URL).ping())
        except Exception:
            redis_ok = False
        return Response(
            {
                "api": True,
                "postgres": True,
                "redis": redis_ok,
                "qdrant_url": settings.QDRANT_URL,
                "neo4j_uri": settings.NEO4J_URI,
            }
        )
