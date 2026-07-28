from unittest.mock import Mock, patch

from django.test import override_settings
from rest_framework.test import APIClient


@override_settings(
    STARTUP_ADVISOR_LLM_MODEL="qwen3:4b",
    CHATBOT_LLM_ENABLED=True,
    CHATBOT_LLM_MODEL="qwen3:4b",
    STARTUP_ADVISOR_RAG_ENABLED=True,
    RESEARCH_VECTOR_RAG_ENABLED=False,
    STARTUP_ADVISOR_EMBEDDING_MODEL="embeddinggemma",
)
def test_ai_readiness_reports_installed_models():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "models": [
            {"name": "qwen3:4b"},
            {"name": "embeddinggemma:latest"},
        ]
    }

    with patch("apps.core.views.httpx.get", return_value=response):
        result = APIClient().get("/api/v1/ai-readiness/")

    assert result.status_code == 200
    assert result.data["ready"] is True
    assert result.data["missing_models"] == []


@override_settings(
    STARTUP_ADVISOR_LLM_MODEL="qwen3:4b",
    CHATBOT_LLM_ENABLED=False,
    STARTUP_ADVISOR_RAG_ENABLED=False,
    RESEARCH_VECTOR_RAG_ENABLED=False,
)
def test_ai_readiness_reports_missing_generation_model():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"models": []}

    with patch("apps.core.views.httpx.get", return_value=response):
        result = APIClient().get("/api/v1/ai-readiness/")

    assert result.status_code == 200
    assert result.data["ready"] is False
    assert result.data["missing_models"] == ["qwen3:4b"]
