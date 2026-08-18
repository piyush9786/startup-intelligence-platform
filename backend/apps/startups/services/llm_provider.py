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


def _repair_missing_object_comma(
    text: str,
    error: json.JSONDecodeError,
) -> str | None:
    """Conservatively repair a missing comma between object members.

    Example:

        {"a":"x" "b":"y"}

    becomes:

        {"a":"x","b":"y"}

    This deliberately does NOT attempt arbitrary semantic JSON repair.
    Downstream JSON Schema and alias validation remain authoritative.
    """

    if error.msg != "Expecting ',' delimiter":
        return None

    index = error.pos

    while (
        index < len(text)
        and text[index].isspace()
    ):
        index += 1

    if index >= len(text):
        return None

    # Most common model failure:
    #
    #   "previous value" "next_key":
    #
    # Only insert a comma when the unexpected quoted token is
    # clearly followed by a colon, meaning it is an object key.
    if text[index] == '"':
        cursor = index + 1
        escaped = False

        while cursor < len(text):
            char = text[cursor]

            if escaped:
                escaped = False

            elif char == "\\":
                escaped = True

            elif char == '"':
                break

            cursor += 1

        if cursor >= len(text):
            return None

        after_key = cursor + 1

        while (
            after_key < len(text)
            and text[after_key].isspace()
        ):
            after_key += 1

        if (
            after_key < len(text)
            and text[after_key] == ":"
        ):
            return (
                text[:index]
                + ","
                + text[index:]
            )

    # Also handle a missing comma before a nested object/array
    # after another completed object/array:
    #
    #   [{...} {...}]
    #
    previous = index - 1

    while (
        previous >= 0
        and text[previous].isspace()
    ):
        previous -= 1

    if (
        previous >= 0
        and text[previous] in "}]"
        and text[index] in "{["
    ):
        return (
            text[:index]
            + ","
            + text[index:]
        )

    return None



def _repair_mismatched_container_close(
    text: str,
    error: json.JSONDecodeError,
) -> str | None:
    """Repair one missing container closer.

    Examples:

        [{"a":"b"]
    becomes:
        [{"a":"b"}]

    and:

        {"a":[1,2}
    becomes:
        {"a":[1,2]}

    The repair is allowed only when a lightweight structural scan
    proves that the current closing token does not match the
    innermost still-open JSON container.
    """

    if error.msg != "Expecting ',' delimiter":
        return None

    index = error.pos

    while (
        index < len(text)
        and text[index].isspace()
    ):
        index += 1

    if index >= len(text):
        return None

    current = text[index]

    if current not in "]}":
        return None

    stack: list[str] = []
    in_string = False
    escaped = False

    for char in text[:index]:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False

            continue

        if char == '"':
            in_string = True

        elif char in "{[":
            stack.append(char)

        elif char in "}]":
            if not stack:
                return None

            expected = (
                "}"
                if stack[-1] == "{"
                else "]"
            )

            if char != expected:
                # Do not repair if the structure was already
                # malformed earlier in the document.
                return None

            stack.pop()

    if not stack:
        return None

    innermost = stack[-1]

    # Object is still open but model emitted array close.
    if (
        innermost == "{"
        and current == "]"
    ):
        return (
            text[:index]
            + "}"
            + text[index:]
        )

    # Array is still open but model emitted object close.
    if (
        innermost == "["
        and current == "}"
    ):
        return (
            text[:index]
            + "]"
            + text[index:]
        )

    return None



def _clean_and_parse_json_payload(
    content: Any,
) -> dict[str, Any]:
    """Clean and deterministically parse structured LLM JSON.

    Repairs only bounded syntax defects:
    - outer markdown fences,
    - text surrounding the outer JSON object,
    - trailing commas,
    - missing commas between clearly identifiable object members.

    Semantic repair is intentionally forbidden. JSON Schema and alias
    validation remain responsible for validating model meaning.
    """

    if isinstance(content, dict):
        return content

    if (
        not isinstance(content, str)
        or not content.strip()
    ):
        raise LLMResponseFormatError(
            "LLM response content is empty."
        )

    cleaned = content.strip()

    if "```" in cleaned:
        cleaned = re.sub(
            r"^\s*```(?:json)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

        cleaned = re.sub(
            r"\s*```\s*$",
            "",
            cleaned,
        )

    if not (
        cleaned.startswith("{")
        and cleaned.endswith("}")
    ):
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")

        if (
            start_idx != -1
            and end_idx != -1
            and end_idx > start_idx
        ):
            cleaned = cleaned[
                start_idx : end_idx + 1
            ].strip()

    # Strict JSON first.
    try:
        data = json.loads(cleaned)

        if isinstance(data, dict):
            return data

    except json.JSONDecodeError:
        pass

    # Existing bounded repair:
    # remove trailing commas before } or ].
    repaired = re.sub(
        r",\s*([\}\]])",
        r"\1",
        cleaned,
    )

    # Bounded missing-comma repair.
    #
    # Multiple passes are supported because a response can contain
    # more than one missing delimiter. Four is intentionally small
    # to avoid turning this into a general-purpose semantic repairer.
    for _ in range(4):
        try:
            data = json.loads(repaired)

            if isinstance(data, dict):
                return data

            break

        except json.JSONDecodeError as exc:
            next_repair = (
                _repair_missing_object_comma(
                    repaired,
                    exc,
                )
            )

            if next_repair is None:
                next_repair = (
                    _repair_mismatched_container_close(
                        repaired,
                        exc,
                    )
                )

            if (
                next_repair is None
                or next_repair == repaired
            ):
                raise LLMResponseFormatError(
                    "The model returned an invalid response: malformed JSON."
                ) from exc

            repaired = next_repair

    try:
        data = json.loads(repaired)

        if isinstance(data, dict):
            return data

    except json.JSONDecodeError as exc:
        raise LLMResponseFormatError(
            "The model returned an invalid response: malformed JSON."
        ) from exc

    raise LLMResponseFormatError(
        "The model response JSON must be an object."
    )


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
        "minItems",
        "maxItems",
        "minLength",
        "maxLength",
        "pattern",
        "minimum",
        "maximum",
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

            if (
                response_data.get("done_reason")
                == "length"
            ):
                raise LLMOutputTruncatedError(
                    "The Ollama structured response was "
                    "truncated because the output token "
                    "limit was reached before completing "
                    "valid JSON."
                ) from exc

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



class StartupIntelSLMProvider:
    """HTTP client for the host-side StartupIntel NF4 + PEFT service."""

    provider_name = "startupintel_slm"

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        max_output_tokens: int,
        api_token: str = "",
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model_name = "StartupIntel-SLM-0.6B-NF4-PEFT"
        self.timeout_seconds = float(timeout_seconds)
        self.max_output_tokens = max(
            64,
            int(max_output_tokens),
        )
        self.api_token = api_token.strip()
        self.transport = transport

    @property
    def generation_parameters(self) -> dict[str, Any]:
        return {
            "runtime": "transformers_nf4_peft",
            "do_sample": False,
            "max_output_tokens": self.max_output_tokens,
            "generation_serialized": True,
        }

    def generate(
        self,
        *,
        messages: list[dict[str, str]],
        response_schema: dict[str, Any],
    ) -> LLMGenerationResult:
        # response_schema remains a Django-side validation contract.
        # The SLM server only performs deterministic text generation.
        del response_schema

        headers = {
            "Content-Type": "application/json",
        }

        if self.api_token:
            headers["Authorization"] = (
                f"Bearer {self.api_token}"
            )

        request_payload = {
            "messages": messages,
            "max_new_tokens": self.max_output_tokens,
        }

        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = client.post(
                    f"{self.base_url}/generate",
                    json=request_payload,
                    headers=headers,
                )
                response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code

            if status == 400:
                raise LLMProviderResponseError(
                    "StartupIntel SLM rejected the generation request.",
                    retryable=False,
                ) from exc

            if status in {401, 403}:
                raise LLMProviderUnavailableError(
                    "StartupIntel SLM authentication failed."
                ) from exc

            if status >= 500:
                raise LLMProviderUnavailableError(
                    "StartupIntel SLM failed during generation."
                ) from exc

            raise LLMProviderUnavailableError(
                f"StartupIntel SLM returned HTTP {status}."
            ) from exc

        except (
            httpx.ConnectError,
            httpx.TimeoutException,
        ) as exc:
            raise LLMProviderUnavailableError(
                "StartupIntel SLM service is unavailable."
            ) from exc

        except httpx.HTTPError as exc:
            raise LLMProviderUnavailableError(
                "StartupIntel SLM request failed."
            ) from exc

        try:
            response_data = response.json()
        except ValueError as exc:
            raise LLMResponseFormatError(
                "StartupIntel SLM returned invalid HTTP JSON."
            ) from exc

        if not isinstance(response_data, dict):
            raise LLMResponseFormatError(
                "StartupIntel SLM response must be an object."
            )

        if response_data.get("done") is False:
            raise LLMResponseFormatError(
                "StartupIntel SLM generation did not complete."
            )

        content = response_data.get("response")

        try:
            payload = _clean_and_parse_json_payload(
                content,
            )
        except LLMResponseFormatError as exc:
            if (
                response_data.get("done_reason")
                == "length"
            ):
                raise LLMOutputTruncatedError(
                    "StartupIntel SLM output reached "
                    "its token limit before completing "
                    "valid JSON."
                ) from exc

            content_length = (
                len(content)
                if isinstance(content, str)
                else None
            )

            content_preview = (
                content[:1200]
                if isinstance(content, str)
                else None
            )

            content_tail = (
                content[-600:]
                if isinstance(content, str)
                else None
            )

            logger.warning(
                "Invalid StartupIntel SLM response: "
                "error=%s parser_cause=%r "
                "done_reason=%r eval_count=%r "
                "content_length=%r "
                "preview=%r tail=%r",
                exc,
                exc.__cause__,
                response_data.get(
                    "done_reason"
                ),
                response_data.get(
                    "eval_count"
                ),
                content_length,
                content_preview,
                content_tail,
            )

            raise

        return LLMGenerationResult(
            payload=payload,
            provider=self.provider_name,
            model_name=str(
                response_data.get("model")
                or self.model_name
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
                "done": bool(
                    response_data.get("done", True)
                ),
                "done_reason": response_data.get(
                    "done_reason"
                ),
                "runtime": response_data.get(
                    "runtime",
                    "transformers_nf4_peft",
                ),
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



def get_startupintel_slm_provider() -> StartupAdvisorLLMProvider:
    """Return the dedicated compact StartupIntel SLM provider."""

    return StartupIntelSLMProvider(
        base_url=settings.STARTUPINTEL_SLM_BASE_URL,
        timeout_seconds=(
            settings.STARTUP_ADVISOR_LLM_TIMEOUT_SECONDS
        ),
        max_output_tokens=(
            settings.STARTUP_ADVISOR_LLM_MAX_OUTPUT_TOKENS
        ),
        api_token=settings.STARTUPINTEL_SLM_API_TOKEN,
    )


def get_startupintel_runtime_provider() -> StartupAdvisorLLMProvider:
    """Provider used only by trained StartupIntel SLM tasks.

    Founder Advisor and Research may use the custom SLM.
    Other LLM features continue using the normal Ollama provider.
    """

    if getattr(
        settings,
        "STARTUPINTEL_SLM_ENABLED",
        False,
    ):
        return get_startupintel_slm_provider()

    return get_startup_advisor_llm_provider()



def get_startup_advisor_llm_provider() -> StartupAdvisorLLMProvider:
    provider_name = (
        settings.STARTUP_ADVISOR_LLM_PROVIDER
        .strip()
        .lower()
    )

    if provider_name == "ollama":
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

    if provider_name == "startupintel_slm":
        return StartupIntelSLMProvider(
            base_url=settings.STARTUPINTEL_SLM_BASE_URL,
            timeout_seconds=(
                settings.STARTUP_ADVISOR_LLM_TIMEOUT_SECONDS
            ),
            max_output_tokens=(
                settings.STARTUP_ADVISOR_LLM_MAX_OUTPUT_TOKENS
            ),
            api_token=settings.STARTUPINTEL_SLM_API_TOKEN,
        )

    raise ImproperlyConfigured(
        "STARTUP_ADVISOR_LLM_PROVIDER must be "
        "'ollama' or 'startupintel_slm'."
    )
