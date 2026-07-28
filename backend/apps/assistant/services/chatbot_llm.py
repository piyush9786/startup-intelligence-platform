"""LLM-powered chatbot reply service.

Calls the local Ollama ``/api/chat`` endpoint with a multi-turn message
history so the model has full conversation memory.  The caller is responsible
for catching :exc:`ChatbotLLMError` and falling back to the deterministic
rule-based reply when the provider is unavailable.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ChatbotLLMError(RuntimeError):
    """Raised when the LLM backend cannot produce a reply."""


# ---------------------------------------------------------------------------
# Navigation hint extraction
# ---------------------------------------------------------------------------

# Maps plain-language phrases in LLM replies to sidebar view slugs so we can
# still attach a navigation action button without forcing JSON output.
_NAV_HINT_MAP: list[tuple[tuple[str, ...], str]] = [
    (("scheme explorer", "schemes", "scheme match", "dpiit", "startup india"), "schemes"),
    (("action roadmap", "roadmap", "next action", "next step"), "roadmap"),
    (("founder advisor", "advisor briefing", "advisor"), "advisor"),
    (("execution", "milestones", "milestone"), "milestones"),
    (("capital planner", "runway", "burn rate"), "capital-planner"),
    (("startup builder", "builder", "business canvas", "persona"), "builder"),
    (("funding", "loan", "grant", "capital support"), "funding"),
    (("requirements", "evidence", "certification"), "requirements"),
    (("my startup", "startup profile", "profile"), "startup"),
    (("dashboard", "overview"), "dashboard"),
    (("assessment", "complete my profile", "wizard"), "assessment"),
]


def extract_navigation_hint(reply: str) -> str | None:
    """Return a view slug if the reply contains a recognisable navigation hint."""
    lower = reply.lower()
    for phrases, view in _NAV_HINT_MAP:
        if any(phrase in lower for phrase in phrases):
            return view
    return None


# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------

_PLATFORM_PAGES = """\
PLATFORM PAGES (sidebar navigation slugs in parentheses):
• Dashboard (dashboard): Overview card, readiness gauge, quick actions
• My Startup (startup): Executive profile factsheet, assessment wizard, document intake
• Scheme Explorer (schemes): Government schemes ranked by eligibility match
• Action Roadmap (roadmap): Ordered remediation actions from readiness gaps
• Founder Advisor (advisor): Deep AI briefing grounded in all profile data
• Execution & Milestones (milestones): Dependency-enforced task tracker with evidence
• Capital Planner (capital-planner): Burn rate, runway, Conservative/Balanced/Growth scenarios
• Startup Builder (builder): Problem statement, customer persona, validation experiments
• Funding & Loans (funding): Capital support records and external scheme comparison
• Requirements (requirements): Evidence and certification requirement tracker"""


def _profile_summary(startup_profile: dict[str, Any] | None) -> str:
    if not startup_profile:
        return "No startup profile is linked to this session."

    lines: list[str] = []

    def add(label: str, key: str) -> None:
        val = startup_profile.get(key)
        if val:
            lines.append(f"• {label}: {val}")

    add("Startup name", "startup_name")
    add("Sector", "sector")
    add("Stage", "stage")
    add("Founded", "founded_year")
    add("City", "city")
    add("State", "state")
    add("Legal structure", "legal_structure")
    add("Team size", "team_size")
    add("Revenue model", "revenue_model")
    add("Annual revenue (INR)", "annual_revenue_inr")

    readiness = startup_profile.get("readiness_score")
    if readiness is not None:
        lines.append(f"• Readiness score: {readiness}/100")

    if not lines:
        return "Startup profile is linked but contains no filled fields yet."

    return "LINKED STARTUP:\n" + "\n".join(lines)


def _build_system_prompt(
    *,
    current_view: str | None,
    startup_profile: dict[str, Any] | None,
) -> str:
    page_line = (
        f"CURRENT PAGE: {current_view}" if current_view else "CURRENT PAGE: unknown"
    )
    profile_block = _profile_summary(startup_profile)

    return f"""\
You are the Founder Assistant embedded in the Startup Intelligence Platform \
— an AI-powered operating system for Indian startup founders.

{_PLATFORM_PAGES}

{page_line}

{profile_block}

BEHAVIOUR RULES:
1. Answer concisely — 2 to 4 sentences unless the founder asks for detail.
2. Only cite profile facts that appear in LINKED STARTUP above. Never invent data.
3. When navigation is helpful, name the exact page and say you can take them there.
4. Do NOT include chain-of-thought, preambles, or markdown headers in your reply.
5. If you genuinely do not know something, say so briefly and offer to help otherwise.
6. Use plain, friendly language — not formal corporate tone.\
"""


# ---------------------------------------------------------------------------
# Ollama /api/chat caller
# ---------------------------------------------------------------------------


def _ollama_base_url() -> str:
    return getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")


def _chatbot_model() -> str:
    return getattr(
        settings,
        "CHATBOT_LLM_MODEL",
        getattr(settings, "STARTUP_ADVISOR_LLM_MODEL", "qwen3:4b"),
    )


def _chatbot_timeout() -> float:
    return max(
        10.0,
        float(getattr(settings, "CHATBOT_LLM_TIMEOUT_SECONDS", 180)),
    )


def _chatbot_max_tokens() -> int:
    return max(
        64,
        int(getattr(settings, "CHATBOT_LLM_MAX_OUTPUT_TOKENS", 512)),
    )


def _chatbot_context_length() -> int:
    return max(
        1024,
        int(getattr(settings, "OLLAMA_CONTEXT_LENGTH", 4096)),
    )


def _chatbot_history_turns() -> int:
    return max(
        0,
        int(getattr(settings, "CHATBOT_LLM_HISTORY_TURNS", 6)),
    )


def _chatbot_keep_alive() -> str:
    return str(
        getattr(
            settings,
            "CHATBOT_LLM_KEEP_ALIVE",
            getattr(settings, "STARTUP_ADVISOR_LLM_KEEP_ALIVE", "10m"),
        )
    )


def get_llm_chatbot_reply(
    *,
    history: list[dict[str, str]],
    current_message: str,
    current_view: str | None = None,
    startup_profile: dict[str, Any] | None = None,
) -> str:
    """Call Ollama /api/chat and return the assistant's plain-text reply.

    Args:
        history: Previous messages in ``[{"role": ..., "content": ...}]`` format,
                 excluding the current user turn.
        current_message: The user's latest message text.
        current_view: The sidebar slug of the currently active page.
        startup_profile: Serialised startup profile dict (may be ``None``).

    Raises:
        ChatbotLLMError: When Ollama is unavailable or returns an invalid response.
    """
    if not getattr(settings, "CHATBOT_LLM_ENABLED", True):
        raise ChatbotLLMError("Chatbot LLM is disabled via CHATBOT_LLM_ENABLED=false.")

    system_prompt = _build_system_prompt(
        current_view=current_view,
        startup_profile=startup_profile,
    )

    ollama_messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": system_prompt,
        },
    ]

    # Do not send the complete lifetime conversation to a 4 GB GPU.
    # Six turns means at most twelve previous user/assistant messages.
    history_message_limit = _chatbot_history_turns() * 2

    bounded_history = (
        history[-history_message_limit:]
        if history_message_limit > 0
        else []
    )

    for msg in bounded_history:
        role = msg.get("role", "")
        content = str(msg.get("content", "")).strip()

        if role in ("user", "assistant") and content:
            ollama_messages.append(
                {
                    "role": role,
                    "content": content,
                }
            )

    ollama_messages.append(
        {
            "role": "user",
            "content": current_message.strip(),
        }
    )

    request_payload = {
        "model": _chatbot_model(),
        "messages": ollama_messages,
        "stream": False,
        "think": False,
        "keep_alive": _chatbot_keep_alive(),
        "options": {
            "temperature": 0.3,
            "num_ctx": _chatbot_context_length(),
            "num_predict": _chatbot_max_tokens(),
        },
    }

    base_url = _ollama_base_url()

    try:
        timeout_seconds = _chatbot_timeout()

        timeout = httpx.Timeout(
            timeout_seconds,
            connect=min(10.0, timeout_seconds),
        )

        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{base_url}/api/chat",
                json=request_payload,
            )
            response.raise_for_status()

    except httpx.HTTPStatusError as exc:
        response_body = exc.response.text[:1000]

        logger.warning(
            "Ollama chatbot request returned HTTP %s. Response: %s",
            exc.response.status_code,
            response_body,
        )

        raise ChatbotLLMError(
            f"Ollama returned HTTP {exc.response.status_code}."
        ) from exc

    except httpx.TimeoutException as exc:
        logger.warning(
            "Ollama chatbot request timed out after %.1f seconds.",
            _chatbot_timeout(),
        )

        raise ChatbotLLMError(
            "The local model exceeded the chatbot generation timeout."
        ) from exc

    except httpx.ConnectError as exc:
        logger.warning(
            "Could not connect to Ollama at %s: %s",
            base_url,
            exc,
        )

        raise ChatbotLLMError(
            "The backend could not connect to the Ollama service."
        ) from exc

    except httpx.HTTPError as exc:
        logger.warning(
            "Ollama chatbot request failed: %s",
            exc,
        )

        raise ChatbotLLMError(
            "The local Ollama request failed."
        ) from exc

    try:
        data = response.json()
        message = data.get("message") or {}
        reply_text = str(message.get("content") or "")
    except (TypeError, ValueError) as exc:
        logger.warning(
            "Ollama returned invalid chatbot JSON: %s",
            exc,
        )

        raise ChatbotLLMError(
            "The local model returned an invalid response."
        ) from exc

    reply_text = _strip_think_tags(reply_text).strip()

    if not reply_text:
        done_reason = data.get("done_reason")

        logger.warning(
            "Ollama completed without response text. done_reason=%s",
            done_reason,
        )

        raise ChatbotLLMError(
            "The local model returned an empty response."
        )

    return reply_text


def _strip_think_tags(text: str) -> str:
    """Remove <think>…</think> chain-of-thought blocks from Qwen3 output."""
    import re
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
