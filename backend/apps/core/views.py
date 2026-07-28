from __future__ import annotations

from typing import Any

import httpx
from django.conf import settings
from django.db import connection
from redis import Redis
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


def _required_ollama_models() -> list[str]:
    models = [settings.STARTUP_ADVISOR_LLM_MODEL]

    if settings.CHATBOT_LLM_ENABLED:
        models.append(settings.CHATBOT_LLM_MODEL)

    if settings.STARTUP_ADVISOR_RAG_ENABLED or settings.RESEARCH_VECTOR_RAG_ENABLED:
        models.append(settings.STARTUP_ADVISOR_EMBEDDING_MODEL)

    return sorted({str(model).strip() for model in models if str(model).strip()})


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
        required_models = _required_ollama_models()
        endpoint = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags"

        try:
            response = httpx.get(endpoint, timeout=5.0)
            response.raise_for_status()
            installed_models = _installed_ollama_models(response.json())
        except (httpx.HTTPError, ValueError):
            return Response(
                {
                    "ready": False,
                    "ollama": False,
                    "required_models": required_models,
                    "missing_models": required_models,
                    "reason": "The Ollama service is unavailable.",
                }
            )

        missing_models = [
            model
            for model in required_models
            if not _model_is_installed(model, installed_models)
        ]

        return Response(
            {
                "ready": not missing_models,
                "ollama": True,
                "required_models": required_models,
                "missing_models": missing_models,
                "reason": (
                    ""
                    if not missing_models
                    else "One or more configured Ollama models are not installed."
                ),
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
