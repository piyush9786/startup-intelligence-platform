from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.startups.models import (
    StartupAdvisorBriefing,
    StartupAdvisorSnapshot,
)

from .briefing_schema import (
    BRIEFING_SCHEMA_VERSION,
    STARTUP_ADVISOR_BRIEFING_SCHEMA,
    validate_startup_advisor_briefing,
)
from .llm_provider import (
    StartupAdvisorLLMProvider,
    get_startup_advisor_llm_provider,
)

BRIEFING_PROMPT_VERSION = "startup-advisor-briefing-prompt-v1"

SYSTEM_PROMPT = """
You are a grounded startup advisor for Indian founders.

Use only facts present in the supplied persisted startup advisor snapshot.
Never invent eligibility, application status, deadlines, benefits,
government requirements, scores, or founder facts.

Every top priority, scheme-guidance item, and risk must cite one or more
exact source references. Each field_path must be a JSON Pointer beginning
with "/" and must resolve inside the cited source object.

Source types:
- profile
- readiness
- action_plan
- recommendation_generation
- recommendation

Use the source record's UUID as source_id. When information is absent,
state that it is unknown and add a practical question for the founder.
Return only a JSON object matching the supplied JSON schema.
""".strip()


class AdvisorSnapshotChangedError(RuntimeError):
    pass


def snapshot_to_llm_input(
    source_snapshot: StartupAdvisorSnapshot,
) -> dict[str, Any]:
    return {
        "advisor_snapshot_id": str(source_snapshot.id),
        "startup_profile_id": str(
            source_snapshot.startup_profile_id,
        ),
        "snapshot_version": source_snapshot.snapshot_version,
        "created_at": source_snapshot.created_at.isoformat(),
        "availability": {
            "has_readiness_assessment": (source_snapshot.has_readiness_assessment),
            "has_action_plan": source_snapshot.has_action_plan,
            "has_recommendation_generation": (source_snapshot.has_recommendation_generation),
        },
        "source_ids": {
            "readiness_assessment_id": (
                str(source_snapshot.readiness_assessment_id)
                if source_snapshot.readiness_assessment_id
                else None
            ),
            "readiness_action_plan_id": (
                str(source_snapshot.readiness_action_plan_id)
                if source_snapshot.readiness_action_plan_id
                else None
            ),
            "recommendation_generation_run_id": (
                str(
                    source_snapshot.recommendation_generation_run_id,
                )
                if source_snapshot.recommendation_generation_run_id
                else None
            ),
        },
        "profile": deepcopy(source_snapshot.profile_snapshot),
        "readiness": deepcopy(source_snapshot.readiness_snapshot),
        "action_plan": deepcopy(
            source_snapshot.action_plan_snapshot,
        ),
        "recommendation_generation": deepcopy(
            source_snapshot.recommendation_generation_snapshot,
        ),
        "recommendations": deepcopy(
            source_snapshot.recommendations_snapshot,
        ),
    }


def build_startup_advisor_briefing_prompt(
    *,
    source_snapshot: StartupAdvisorSnapshot,
) -> dict[str, Any]:
    input_payload = snapshot_to_llm_input(source_snapshot)
    user_payload = {
        "response_schema": STARTUP_ADVISOR_BRIEFING_SCHEMA,
        "startup_advisor_snapshot": input_payload,
    }
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": json.dumps(
                user_payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        },
    ]
    return {
        "prompt_version": BRIEFING_PROMPT_VERSION,
        "schema_version": BRIEFING_SCHEMA_VERSION,
        "messages": messages,
        "response_schema": deepcopy(
            STARTUP_ADVISOR_BRIEFING_SCHEMA,
        ),
        "source_input": input_payload,
    }


def generate_startup_advisor_briefing(
    *,
    source_snapshot: StartupAdvisorSnapshot,
    requested_by: Any,
    provider: StartupAdvisorLLMProvider | None = None,
) -> StartupAdvisorBriefing:
    prompt_snapshot = build_startup_advisor_briefing_prompt(
        source_snapshot=source_snapshot,
    )
    active_provider = provider if provider is not None else get_startup_advisor_llm_provider()
    generation_result = active_provider.generate(
        messages=prompt_snapshot["messages"],
        response_schema=prompt_snapshot["response_schema"],
    )
    briefing_payload = validate_startup_advisor_briefing(
        payload=generation_result.payload,
        source_snapshot=source_snapshot,
    )

    with transaction.atomic():
        locked_snapshot = (
            StartupAdvisorSnapshot.objects.select_for_update(
                of=("self",),
            )
            .select_related("startup_profile")
            .get(pk=source_snapshot.pk)
        )
        locked_input = snapshot_to_llm_input(locked_snapshot)
        if locked_input != prompt_snapshot["source_input"]:
            raise AdvisorSnapshotChangedError("The advisor snapshot changed during LLM generation.")

        return StartupAdvisorBriefing.objects.create(
            requested_by=requested_by,
            startup_profile=locked_snapshot.startup_profile,
            source_snapshot=locked_snapshot,
            provider=generation_result.provider,
            model_name=generation_result.model_name,
            prompt_version=BRIEFING_PROMPT_VERSION,
            schema_version=BRIEFING_SCHEMA_VERSION,
            generation_parameters=deepcopy(
                active_provider.generation_parameters,
            ),
            prompt_snapshot=prompt_snapshot,
            briefing=briefing_payload,
            prompt_token_count=(generation_result.prompt_token_count),
            output_token_count=(generation_result.output_token_count),
            total_duration_ns=(generation_result.total_duration_ns),
            response_metadata=deepcopy(
                generation_result.response_metadata,
            ),
            completed_at=timezone.now(),
        )
