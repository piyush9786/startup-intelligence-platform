import json

import httpx
import pytest

from apps.startups.services import (
    LLMProviderResponseError,
    LLMProviderUnavailableError,
    OllamaStartupAdvisorProvider,
)


def provider(transport):
    return OllamaStartupAdvisorProvider(
        base_url="http://ollama:11434",
        model_name="qwen3.5:9b",
        timeout_seconds=30,
        temperature=0,
        seed=7,
        max_output_tokens=2048,
        keep_alive="5m",
        transport=transport,
    )


def test_ollama_provider_uses_structured_output_and_parses_usage():
    seen = {}

    def handler(request):
        seen["request"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": "qwen3.5:9b",
                "created_at": "2026-07-21T00:00:00Z",
                "message": {
                    "role": "assistant",
                    "content": json.dumps({"ok": True}),
                },
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 100,
                "eval_count": 20,
                "total_duration": 123456,
            },
        )

    result = provider(
        httpx.MockTransport(handler),
    ).generate(
        messages=[{"role": "user", "content": "grounded"}],
        response_schema={
            "type": "object",
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
        },
    )

    assert seen["request"]["model"] == "qwen3.5:9b"
    assert seen["request"]["stream"] is False
    assert seen["request"]["think"] is False
    assert seen["request"]["format"]["type"] == "object"
    assert seen["request"]["options"]["temperature"] == 0
    assert result.payload == {"ok": True}
    assert result.prompt_token_count == 100
    assert result.output_token_count == 20
    assert result.total_duration_ns == 123456


def test_ollama_provider_rejects_invalid_json_content():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "model": "qwen3.5:9b",
                "message": {
                    "role": "assistant",
                    "content": "not-json",
                },
                "done": True,
            },
        )
    )

    with pytest.raises(
        LLMProviderResponseError,
        match="invalid response",
    ):
        provider(transport).generate(
            messages=[],
            response_schema={"type": "object"},
        )


def test_ollama_provider_maps_http_failure_to_unavailable():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            404,
            json={"error": "model not found"},
        )
    )

    with pytest.raises(
        LLMProviderUnavailableError,
        match="unavailable",
    ):
        provider(transport).generate(
            messages=[],
            response_schema={"type": "object"},
        )
