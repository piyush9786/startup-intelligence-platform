from unittest.mock import Mock, patch

from django.test import override_settings
from rest_framework.test import APIClient


def _ollama_response(models):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "models": [{"name": model} for model in models]
    }
    return response


@override_settings(
    STARTUP_ADVISOR_LLM_MODEL="qwen3:4b",
    CHATBOT_LLM_ENABLED=True,
    CHATBOT_LLM_MODEL="qwen3:4b",
    STARTUP_ADVISOR_RAG_ENABLED=True,
    RESEARCH_VECTOR_RAG_ENABLED=False,
    STARTUP_ADVISOR_EMBEDDING_MODEL="embeddinggemma",
)
def test_ai_readiness_reports_installed_advisor_models():
    with patch(
        "apps.core.views.httpx.get",
        return_value=_ollama_response(
            ["qwen3:4b", "embeddinggemma:latest"],
        ),
    ):
        result = APIClient().get("/api/v1/ai-readiness/")

    assert result.status_code == 200
    assert result.data["ready"] is True
    assert result.data["capabilities"]["advisor"]["ready"] is True
    assert result.data["missing_models"] == []


@override_settings(
    STARTUP_ADVISOR_LLM_MODEL="qwen3:4b",
    CHATBOT_LLM_ENABLED=False,
    STARTUP_ADVISOR_RAG_ENABLED=False,
    RESEARCH_VECTOR_RAG_ENABLED=False,
)
def test_ai_readiness_reports_missing_generation_model():
    with patch(
        "apps.core.views.httpx.get",
        return_value=_ollama_response([]),
    ):
        result = APIClient().get("/api/v1/ai-readiness/")

    assert result.status_code == 200
    assert result.data["ready"] is False
    assert result.data["missing_models"] == ["qwen3:4b"]


@override_settings(
    STARTUP_ADVISOR_LLM_MODEL="qwen3:4b",
    CHATBOT_LLM_ENABLED=True,
    CHATBOT_LLM_MODEL="llama3.2:3b",
    STARTUP_ADVISOR_RAG_ENABLED=False,
    RESEARCH_VECTOR_RAG_ENABLED=False,
)
def test_missing_chatbot_model_does_not_disable_advisor():
    with patch(
        "apps.core.views.httpx.get",
        return_value=_ollama_response(["qwen3:4b"]),
    ):
        result = APIClient().get("/api/v1/ai-readiness/")

    assert result.data["ready"] is True
    assert result.data["capabilities"]["advisor"]["ready"] is True
    assert result.data["capabilities"]["chatbot"]["ready"] is False
    assert result.data["capabilities"]["chatbot"]["missing_models"] == [
        "llama3.2:3b",
    ]
