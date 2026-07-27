from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class LLMProviderError(RuntimeError):
    pass


class LLMProviderUnavailableError(LLMProviderError):
    pass


class LLMProviderResponseError(LLMProviderError):
    pass


@dataclass(frozen=True)
class LLMGenerationResult:
    payload: dict[str, Any]
    provider: str
    model_name: str
    prompt_token_count: int | None
    output_token_count: int | None
    total_duration_ns: int | None
    response_metadata: dict[str, Any]


class StartupAdvisorLLMProvider(Protocol):
    @property
    def generation_parameters(self) -> dict[str, Any]: ...

    def generate(
        self,
        *,
        messages: list[dict[str, str]],
        response_schema: dict[str, Any],
    ) -> LLMGenerationResult: ...


def _ollama_generation_schema(schema: Any) -> Any:
    """Reduce JSON Schema to the subset needed for Ollama generation.

    Django still validates the returned payload against the complete schema,
    including lengths, item counts, constants, formats, patterns and grounding.
    """
    if isinstance(schema, list):
        return [_ollama_generation_schema(item) for item in schema]

    if not isinstance(schema, dict):
        return schema

    simplified: dict[str, Any] = {}

    for key in (
        "type",
        "additionalProperties",
        "required",
        "enum",
    ):
        if key in schema:
            simplified[key] = schema[key]

    if "const" in schema:
        simplified["enum"] = [schema["const"]]

    if "properties" in schema:
        simplified["properties"] = {
            name: _ollama_generation_schema(value) for name, value in schema["properties"].items()
        }

    if "items" in schema:
        simplified["items"] = _ollama_generation_schema(
            schema["items"],
        )

    # Preserve only the inexpensive zero-item constraint. This lets
    # callers require an unsupported result group to remain empty.
    if schema.get("maxItems") == 0:
        simplified["maxItems"] = 0

    return simplified


def _messages_to_generate_prompt(
    messages: list[dict[str, str]],
) -> tuple[str, str]:
    """Convert advisor messages for Ollama's generate endpoint."""
    system_parts: list[str] = []
    conversation: list[tuple[str, str]] = []

    for message in messages:
        role = message["role"]
        content = message["content"]

        if role == "system":
            system_parts.append(content)
        else:
            conversation.append((role, content))

    system_prompt = "\n\n".join(system_parts)

    if len(conversation) == 1 and conversation[0][0] == "user":
        prompt = conversation[0][1]
    else:
        prompt = "\n\n".join(f"{role.upper()}:\n{content}" for role, content in conversation)

    return system_prompt, prompt


class OllamaStartupAdvisorProvider:
    provider_name = "ollama"

    def __init__(
        self,
        *,
        base_url: str,
        model_name: str,
        timeout_seconds: float,
        temperature: float,
        seed: int,
        max_output_tokens: int,
        keep_alive: str,
        context_length: int = 4096,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.seed = seed
        self.max_output_tokens = max(256, int(max_output_tokens))
        self.keep_alive = keep_alive
        self.context_length = max(1024, int(context_length))
        self.transport = transport

    @property
    def generation_parameters(self) -> dict[str, Any]:
        return {
            "temperature": self.temperature,
            "seed": self.seed,
            "max_output_tokens": self.max_output_tokens,
            "context_length": self.context_length,
            "think": False,
            "stream": False,
            "keep_alive": self.keep_alive,
        }

    def generate(
        self,
        *,
        messages: list[dict[str, str]],
        response_schema: dict[str, Any],
    ) -> LLMGenerationResult:
        system_prompt, prompt = _messages_to_generate_prompt(
            messages,
        )

        request_payload = {
            "model": self.model_name,
            "system": system_prompt,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "format": _ollama_generation_schema(response_schema),
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": self.temperature,
                "seed": self.seed,
                "num_ctx": self.context_length,
                "num_predict": self.max_output_tokens,
            },
        }

        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json=request_payload,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 400 or exc.response.status_code >= 500:
                raise LLMProviderResponseError(
                    "The local Ollama model rejected the structured response request."
                ) from exc
            raise LLMProviderUnavailableError(
                "The local Ollama model service is unavailable or "
                "the configured model is not ready."
            ) from exc
        except (
            httpx.ConnectError,
            httpx.TimeoutException,
        ) as exc:
            raise LLMProviderUnavailableError(
                "The local Ollama model service is unavailable or "
                "the configured model is not ready."
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderUnavailableError("The local Ollama request failed.") from exc

        try:
            response_data = response.json()
            content = response_data.get("response")
            if content is None:
                content = response_data["message"]["content"]
            payload = json.loads(content)
        except (
            KeyError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            raise LLMProviderResponseError(
                "The local Ollama model returned an invalid response."
            ) from exc

        if not isinstance(payload, dict):
            raise LLMProviderResponseError("The local Ollama model response must be a JSON object.")

        return LLMGenerationResult(
            payload=payload,
            provider=self.provider_name,
            model_name=str(
                response_data.get("model") or self.model_name,
            ),
            prompt_token_count=_optional_nonnegative_int(
                response_data.get("prompt_eval_count"),
            ),
            output_token_count=_optional_nonnegative_int(
                response_data.get("eval_count"),
            ),
            total_duration_ns=_optional_nonnegative_int(
                response_data.get("total_duration"),
            ),
            response_metadata={
                "done": bool(response_data.get("done", False)),
                "done_reason": response_data.get("done_reason"),
                "created_at": response_data.get("created_at"),
            },
        )


def _optional_nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def get_startup_advisor_llm_provider() -> StartupAdvisorLLMProvider:
    provider_name = settings.STARTUP_ADVISOR_LLM_PROVIDER

    if provider_name != "ollama":
        raise ImproperlyConfigured(
            "STARTUP_ADVISOR_LLM_PROVIDER must be 'ollama'."
        )

    return OllamaStartupAdvisorProvider(
        base_url=settings.OLLAMA_BASE_URL,
        model_name=settings.STARTUP_ADVISOR_LLM_MODEL,
        timeout_seconds=settings.STARTUP_ADVISOR_LLM_TIMEOUT_SECONDS,
        temperature=settings.STARTUP_ADVISOR_LLM_TEMPERATURE,
        seed=settings.STARTUP_ADVISOR_LLM_SEED,
        max_output_tokens=settings.STARTUP_ADVISOR_LLM_MAX_OUTPUT_TOKENS,
        keep_alive=settings.STARTUP_ADVISOR_LLM_KEEP_ALIVE,
        context_length=settings.OLLAMA_CONTEXT_LENGTH,
    )
