from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class LLMProviderError(RuntimeError):
    pass


class LLMProviderUnavailableError(LLMProviderError):
    pass


class LLMProviderResponseError(LLMProviderError):
    def __init__(self, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


class LLMOutputTruncatedError(LLMProviderResponseError):
    """Raised when LLM generation exceeds max output tokens or finishes prematurely."""


class LLMResponseFormatError(LLMProviderResponseError):
    """Raised when LLM output cannot be parsed as a valid JSON object."""


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


def _clean_and_parse_json_payload(content: Any) -> dict[str, Any]:
    """Robust JSON cleaning and parsing for LLM output.

    Strips markdown code fences (```json ... ```), extracts outer JSON objects,
    repairs trailing commas, and parses into a dictionary.
    """
    if isinstance(content, dict):
        return content

    if not isinstance(content, str) or not content.strip():
        raise LLMResponseFormatError("LLM response content is empty.")

    cleaned = content.strip()

    # Remove markdown code fences if present
    if "```" in cleaned:
        fence_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", cleaned, re.IGNORECASE)
        if fence_match:
            cleaned = fence_match.group(1).strip()
        else:
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)

    # Extract JSON object substring between first '{' and last '}'
    if not (cleaned.startswith("{") and cleaned.endswith("}")):
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            cleaned = cleaned[start_idx : end_idx + 1].strip()

    # Standard JSON parse
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except ValueError:
        pass

    # Secondary repair attempt: strip trailing commas before closing braces/brackets
    repaired = re.sub(r",\s*([\}\]])", r"\1", cleaned)
    try:
        data = json.loads(repaired)
        if isinstance(data, dict):
            return data
    except ValueError as exc:
        raise LLMResponseFormatError("The local Ollama model returned an invalid response.") from exc

    raise LLMResponseFormatError("The local Ollama model returned an invalid response.")


def _ollama_generation_schema(schema: Any) -> Any:
    """Reduce JSON Schema to the subset needed for Ollama generation."""
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
            status_code = exc.response.status_code

            if status_code == 400:
                raise LLMResponseFormatError(
                    "Ollama rejected the structured response schema.",
                    retryable=False,
                ) from exc

            if status_code == 404:
                raise LLMProviderUnavailableError(
                    f"The configured Ollama model {self.model_name!r} was not found."
                ) from exc

            if status_code >= 500:
                raise LLMProviderUnavailableError(
                    "Ollama failed while generating the advisor response."
                ) from exc

            raise LLMProviderUnavailableError(
                f"Ollama returned HTTP {status_code}."
            ) from exc
        except (
            httpx.ConnectError,
            httpx.TimeoutException,
        ) as exc:
            raise LLMProviderUnavailableError(
                "The local Ollama model service is unavailable or configured model is not ready."
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderUnavailableError("The local Ollama request failed.") from exc

        response_data: Any = None
        content: Any = None

        try:
            response_data = response.json()
        except ValueError as exc:
            _log_invalid_ollama_advisor_response(
                model_name=self.model_name,
                response=response,
                response_data=response_data,
                content=content,
            )
            raise LLMResponseFormatError(
                "The local Ollama model returned invalid non-JSON HTTP body."
            ) from exc

        if not isinstance(response_data, dict):
            _log_invalid_ollama_advisor_response(
                model_name=self.model_name,
                response=response,
                response_data=response_data,
                content=content,
            )
            raise LLMResponseFormatError(
                "The local Ollama model response is not a dict."
            )

        try:
            content = response_data.get("response")
            if content is None:
                content = response_data["message"]["content"]
        except (KeyError, TypeError) as exc:
            _log_invalid_ollama_advisor_response(
                model_name=self.model_name,
                response=response,
                response_data=response_data,
                content=content,
            )
            raise LLMResponseFormatError(
                "The local Ollama model payload lacks a 'response' or 'message' field."
            ) from exc

        if response_data.get("done_reason") == "length":
            _log_invalid_ollama_advisor_response(
                model_name=self.model_name,
                response=response,
                response_data=response_data,
                content=content,
            )
            raise LLMOutputTruncatedError(
                "The advisor response was truncated because the output token limit was reached."
            )

        if response_data.get("done") is False:
            _log_invalid_ollama_advisor_response(
                model_name=self.model_name,
                response=response,
                response_data=response_data,
                content=content,
            )
            raise LLMResponseFormatError(
                "Ollama did not finish generating the advisor response."
            )

        try:
            payload = _clean_and_parse_json_payload(content)
        except LLMResponseFormatError as exc:
            _log_invalid_ollama_advisor_response(
                model_name=self.model_name,
                response=response,
                response_data=response_data,
                content=content,
            )
            raise exc

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


def _log_invalid_ollama_advisor_response(
    *,
    model_name: str,
    response: httpx.Response,
    response_data: Any,
    content: Any,
) -> None:
    metadata = response_data if isinstance(response_data, dict) else {}

    logger.warning(
        "Invalid Ollama advisor response",
        extra={
            "model": model_name,
            "http_status": response.status_code,
            "done": metadata.get("done"),
            "done_reason": metadata.get("done_reason"),
            "eval_count": metadata.get("eval_count"),
            "content_length": len(content) if isinstance(content, str) else None,
            "content_preview": content[:300] if isinstance(content, str) else None,
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
