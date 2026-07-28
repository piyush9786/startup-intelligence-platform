"""
AI Startup Builder section service.

Provides AI-draft generation for each builder section type using the existing
LLM provider infrastructure. Draft generation is best-effort; the founder is
always shown the draft for review before confirming content.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from django.utils import timezone

from ..models import BUILDER_PLAN_VERSION, StartupBuilderSection, StartupProfile
from .llm_provider import (
    LLMProviderError,
    get_startup_advisor_llm_provider,
)

logger = logging.getLogger(__name__)


BUILDER_DRAFT_PROMPT_VERSION = "builder-draft-v1"


# ---------------------------------------------------------------------------
# Section schemas — minimal structured output per section type
# ---------------------------------------------------------------------------

SECTION_SCHEMAS: dict[str, dict[str, Any]] = {
    StartupBuilderSection.SectionType.PROBLEM: {
        "type": "object",
        "properties": {
            "problem_statement": {
                "type": "string",
                "description": "A clear, specific description of the problem being solved.",
            },
            "who_has_this_problem": {
                "type": "string",
                "description": "Who experiences this problem and how severely.",
            },
            "current_alternatives": {
                "type": "string",
                "description": "How people currently solve or work around this problem.",
            },
            "why_now": {
                "type": "string",
                "description": "Why is this the right time to solve this problem.",
            },
            "evidence_of_problem": {
                "type": "string",
                "description": "Data, anecdotes, or observations that confirm the problem exists.",
            },
        },
        "required": [
            "problem_statement",
            "who_has_this_problem",
            "current_alternatives",
            "why_now",
            "evidence_of_problem",
        ],
    },
    StartupBuilderSection.SectionType.CUSTOMER: {
        "type": "object",
        "properties": {
            "primary_customer_segment": {
                "type": "string",
                "description": "The primary customer segment you are targeting.",
            },
            "customer_profile": {
                "type": "string",
                "description": "Specific demographics, roles, size, and location.",
            },
            "customer_pain_intensity": {
                "type": "string",
                "description": "How much does this customer care about solving this problem.",
            },
            "customer_willingness_to_pay": {
                "type": "string",
                "description": "Evidence or hypothesis for willingness to pay.",
            },
            "reach_channels": {
                "type": "string",
                "description": "Where and how you can reach this customer segment.",
            },
        },
        "required": [
            "primary_customer_segment",
            "customer_profile",
            "customer_pain_intensity",
            "customer_willingness_to_pay",
            "reach_channels",
        ],
    },
    StartupBuilderSection.SectionType.INTERVIEWS: {
        "type": "object",
        "properties": {
            "interview_goal": {
                "type": "string",
                "description": "What you want to learn from customer interviews.",
            },
            "target_interviewees": {
                "type": "string",
                "description": "Who to interview and how many.",
            },
            "key_questions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "5-8 open-ended questions to ask customers.",
            },
            "success_criteria": {
                "type": "string",
                "description": "What evidence from interviews would validate your hypothesis.",
            },
            "recruitment_approach": {
                "type": "string",
                "description": "How you will find and recruit interview participants.",
            },
        },
        "required": [
            "interview_goal",
            "target_interviewees",
            "key_questions",
            "success_criteria",
            "recruitment_approach",
        ],
    },
    StartupBuilderSection.SectionType.VALIDATION: {
        "type": "object",
        "properties": {
            "core_hypothesis": {
                "type": "string",
                "description": "The single most important assumption you need to validate.",
            },
            "experiments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "method": {"type": "string"},
                        "success_metric": {"type": "string"},
                        "timeline_weeks": {"type": "integer"},
                    },
                    "required": ["name", "method", "success_metric"],
                },
                "description": "2-4 lightweight experiments to validate demand.",
            },
            "minimum_evidence": {
                "type": "string",
                "description": "Minimum evidence needed before building the MVP.",
            },
        },
        "required": ["core_hypothesis", "experiments", "minimum_evidence"],
    },
    StartupBuilderSection.SectionType.BUSINESS_MODEL: {
        "type": "object",
        "properties": {
            "revenue_model": {
                "type": "string",
                "description": "How the business generates revenue (subscription, sales).",
            },
            "value_proposition": {
                "type": "string",
                "description": "The specific value delivered to customers.",
            },
            "key_activities": {
                "type": "string",
                "description": "The core activities required to deliver value.",
            },
            "key_resources": {
                "type": "string",
                "description": "Critical resources and capabilities needed.",
            },
            "cost_structure": {
                "type": "string",
                "description": "Primary cost drivers in the business.",
            },
            "unit_economics": {
                "type": "string",
                "description": "Revenue per customer and estimated cost to serve.",
            },
        },
        "required": [
            "revenue_model",
            "value_proposition",
            "key_activities",
            "key_resources",
            "cost_structure",
            "unit_economics",
        ],
    },
    StartupBuilderSection.SectionType.PRICING: {
        "type": "object",
        "properties": {
            "pricing_model": {
                "type": "string",
                "description": "Pricing model type (freemium, tiered, usage-based, etc.).",
            },
            "price_point": {
                "type": "string",
                "description": "Proposed price point with rationale.",
            },
            "pricing_basis": {
                "type": "string",
                "description": "What you are pricing on (outcome, feature, usage, value).",
            },
            "competitive_positioning": {
                "type": "string",
                "description": "How pricing compares to alternatives.",
            },
            "early_customer_offer": {
                "type": "string",
                "description": "Special pricing or terms for first customers.",
            },
        },
        "required": [
            "pricing_model",
            "price_point",
            "pricing_basis",
            "competitive_positioning",
            "early_customer_offer",
        ],
    },
}


# ---------------------------------------------------------------------------
# Draft generation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BuilderDraftResult:
    section_type: str
    draft: dict[str, Any]
    prompt_version: str
    model_name: str
    provider: str


class BuilderDraftError(RuntimeError):
    pass


def _build_section_prompt(
    section_type: str,
    profile: StartupProfile,
) -> list[dict[str, str]]:
    """Build the LLM messages for a builder section draft."""
    profile_summary = (
        f"Startup name: {profile.startup_name}\n"
        f"Description: {profile.description or 'Not provided'}\n"
        f"Stage: {profile.get_stage_display()}\n"
        f"Sectors: {', '.join(profile.sectors) if profile.sectors else 'Not specified'}\n"
        f"State: {profile.state or 'Not provided'}\n"
        f"Team size: {profile.team_size or 'Not provided'}\n"
        f"Annual turnover: {profile.annual_turnover or 'Pre-revenue'}\n"
        f"DPIIT recognised: {profile.dpiit_recognized}\n"
    )

    section_label = dict(StartupBuilderSection.SectionType.choices).get(
        section_type, section_type
    )

    system_message = (
        "You are an expert startup advisor helping an Indian founder structure "
        "their startup plan. Based on the founder's startup profile, generate a "
        "clear, specific, and actionable draft for the requested section. "
        "Your response must be grounded in the founder's context — do not invent "
        "facts not present in the profile. Use concrete, specific language. "
        "Avoid generic startup advice. Keep each field concise (2-4 sentences max). "
        "Respond only with valid JSON matching the required schema."
    )

    user_message = (
        f"Startup profile:\n{profile_summary}\n\n"
        f"Generate a draft for the '{section_label}' section of this startup's "
        f"AI Startup Builder plan. Use the founder's context where available "
        f"and flag areas where you have assumed information."
    )

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]


def generate_builder_section_draft(
    *,
    section_type: str,
    profile: StartupProfile,
    provider: Any | None = None,
) -> BuilderDraftResult:
    """
    Generate an AI draft for a single builder section.

    Uses the existing OllamaStartupAdvisorProvider. Raises BuilderDraftError
    if the provider is unavailable or the response cannot be parsed.
    """
    schema = SECTION_SCHEMAS.get(section_type)
    if schema is None:
        raise BuilderDraftError(
            f"No schema defined for section type '{section_type}'."
        )

    if provider is None:
        provider = get_startup_advisor_llm_provider()

    messages = _build_section_prompt(section_type, profile)

    try:
        result = provider.generate(
            messages=messages,
            response_schema=schema,
        )
    except LLMProviderError as exc:
        raise BuilderDraftError(
            f"LLM provider unavailable for builder draft: {exc}"
        ) from exc

    payload = result.payload
    if not isinstance(payload, dict):
        raise BuilderDraftError(
            "Provider returned a non-dict payload for builder draft."
        )

    return BuilderDraftResult(
        section_type=section_type,
        draft=payload,
        prompt_version=BUILDER_DRAFT_PROMPT_VERSION,
        model_name=result.model_name,
        provider=result.provider,
    )


# ---------------------------------------------------------------------------
# Section persistence helpers
# ---------------------------------------------------------------------------

def upsert_builder_section(
    *,
    owner,
    profile: StartupProfile,
    section_type: str,
    content: dict[str, Any],
    status: str = StartupBuilderSection.Status.DRAFT,
) -> StartupBuilderSection:
    """
    Create or update a builder section with founder-provided content.
    """
    section, _ = StartupBuilderSection.objects.get_or_create(
        owner=owner,
        startup_profile=profile,
        section_type=section_type,
        defaults={
            "content": content,
            "status": status,
            "plan_version": BUILDER_PLAN_VERSION,
        },
    )

    if _:
        return section

    # Update existing
    section.content = content
    if status == StartupBuilderSection.Status.CONFIRMED:
        section.status = status
        section.confirmed_at = timezone.now()
    else:
        section.status = status

    section.save(update_fields=["content", "status", "confirmed_at", "updated_at"])
    return section


def apply_ai_draft_to_section(
    *,
    owner,
    profile: StartupProfile,
    section_type: str,
    draft: dict[str, Any],
    model_name: str,
    prompt_version: str,
) -> StartupBuilderSection:
    """
    Persist an AI-generated draft onto a builder section.
    The section status is set to AI_DRAFTED; the founder must confirm.
    """
    section, _ = StartupBuilderSection.objects.get_or_create(
        owner=owner,
        startup_profile=profile,
        section_type=section_type,
        defaults={
            "ai_draft": draft,
            "status": StartupBuilderSection.Status.AI_DRAFTED,
            "plan_version": BUILDER_PLAN_VERSION,
        },
    )

    if _:
        return section

    section.ai_draft = draft
    section.status = StartupBuilderSection.Status.AI_DRAFTED
    section.save(update_fields=["ai_draft", "status", "updated_at"])
    return section
