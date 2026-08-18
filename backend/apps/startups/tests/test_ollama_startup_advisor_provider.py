import json
import logging

import httpx
import pytest

from apps.startups.services import (
    LLMProviderResponseError,
    LLMProviderUnavailableError,
    OllamaStartupAdvisorProvider,
)


def provider(transport, *, max_output_tokens=2048):
    return OllamaStartupAdvisorProvider(
        base_url="http://ollama:11434",
        model_name="qwen3.5:9b",
        timeout_seconds=30,
        temperature=0,
        seed=7,
        max_output_tokens=max_output_tokens,
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


def test_ollama_provider_simplifies_complex_generation_schema():
    seen = {}

    def handler(request):
        seen["request"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": "qwen3.5:9b",
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "summary": "Ready",
                            "disclaimer": "Fixed",
                            "items": [],
                        }
                    ),
                },
                "done": True,
            },
        )

    provider(httpx.MockTransport(handler)).generate(
        messages=[],
        response_schema={
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "summary": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 2000,
                    "pattern": "^.+$",
                },
                "disclaimer": {
                    "const": "Fixed",
                },
                "items": {
                    "type": "array",
                    "maxItems": 10,
                    "items": {
                        "type": "string",
                        "maxLength": 500,
                    },
                },
            },
            "required": [
                "summary",
                "disclaimer",
                "items",
            ],
        },
    )

    generation_schema = seen["request"]["format"]

    assert generation_schema == {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "summary": {
                "type": "string",
                "minLength": 1,
                "maxLength": 2000,
                "pattern": "^.+$",
            },
            "disclaimer": {
                "enum": ["Fixed"],
            },
            "items": {
                "type": "array",
                "maxItems": 10,
                "items": {
                    "type": "string",
                    "maxLength": 500,
                },
            },
        },
        "required": [
            "summary",
            "disclaimer",
            "items",
        ],
    }


def test_ollama_provider_rejects_invalid_json_content_and_logs_diagnostics(caplog):
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

    with caplog.at_level(logging.WARNING, logger="apps.startups.services.llm_provider"):
        with pytest.raises(
            LLMProviderResponseError,
            match="invalid response",
        ) as exc_info:
            provider(transport).generate(
                messages=[],
                response_schema={"type": "object"},
            )

    assert exc_info.value.retryable is True
    record = caplog.records[-1]
    assert record.message == "Invalid Ollama advisor response"
    assert record.model == "qwen3.5:9b"
    assert record.http_status == 200
    assert record.done is True
    assert record.done_reason is None
    assert record.eval_count is None
    assert record.content_length == len("not-json")
    assert record.content_preview == "not-json"


@pytest.mark.parametrize(
    ("status_code", "exception_type", "message"),
    [
        (
            400,
            LLMProviderResponseError,
            "Ollama rejected the structured response schema.",
        ),
        (
            404,
            LLMProviderUnavailableError,
            "The configured Ollama model 'qwen3.5:9b' was not found.",
        ),
        (
            500,
            LLMProviderUnavailableError,
            "Ollama failed while generating the advisor response.",
        ),
        (
            429,
            LLMProviderUnavailableError,
            "Ollama returned HTTP 429.",
        ),
    ],
)
def test_ollama_provider_classifies_http_failures(
    status_code,
    exception_type,
    message,
):
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            status_code,
            json={"error": "model not found"},
        )
    )

    with pytest.raises(exception_type) as exc_info:
        provider(transport).generate(
            messages=[],
            response_schema={"type": "object"},
        )

    assert str(exc_info.value) == message
    if status_code == 400:
        assert exc_info.value.retryable is False


def test_ollama_provider_detects_truncated_production_like_output_before_json_parse(caplog):
    seen = {}
    truncated_content = '{"summary":"' + ("x" * 320)

    def handler(request):
        seen["request"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "response": truncated_content,
                "done": True,
                "done_reason": "length",
                "eval_count": 1024,
            },
        )

    with caplog.at_level(logging.WARNING, logger="apps.startups.services.llm_provider"):
        with pytest.raises(
            LLMProviderResponseError,
            match="truncated because the output token limit was reached",
        ) as exc_info:
            provider(
                httpx.MockTransport(handler),
                max_output_tokens=1024,
            ).generate(
                messages=[],
                response_schema={"type": "object"},
            )

    assert exc_info.value.retryable is True
    assert seen["request"]["options"]["num_predict"] == 1024
    record = caplog.records[-1]
    assert record.done is True
    assert record.done_reason == "length"
    assert record.eval_count == 1024
    assert record.content_length == len(truncated_content)
    assert record.content_preview == truncated_content[:300]


def test_ollama_provider_detects_unfinished_generation_before_json_parse():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "response": '{"summary":"unfinished"',
                "done": False,
                "done_reason": "stop",
            },
        )
    )

    with pytest.raises(
        LLMProviderResponseError,
        match="did not finish generating",
    ) as exc_info:
        provider(transport).generate(
            messages=[],
            response_schema={"type": "object"},
        )

    assert exc_info.value.retryable is True


def test_ollama_provider_uses_generate_endpoint_instead_of_chat_parser():
    seen = {}

    def handler(request):
        seen["path"] = request.url.path
        seen["request"] = json.loads(request.content)

        return httpx.Response(
            200,
            json={
                "model": "qwen3.5:9b",
                "response": json.dumps({"ok": True}),
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 10,
                "eval_count": 5,
            },
        )

    result = provider(
        httpx.MockTransport(handler),
    ).generate(
        messages=[
            {
                "role": "system",
                "content": "Return JSON.",
            },
            {
                "role": "user",
                "content": "Return ok.",
            },
        ],
        response_schema={
            "type": "object",
            "properties": {
                "ok": {
                    "type": "boolean",
                },
            },
            "required": ["ok"],
        },
    )

    assert seen["path"] == "/api/generate"
    assert seen["request"]["system"] == "Return JSON."
    assert seen["request"]["prompt"] == "Return ok."
    assert "messages" not in seen["request"]
    assert result.payload == {"ok": True}
