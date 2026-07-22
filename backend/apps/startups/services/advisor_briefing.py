from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.knowledge.services import (
    VectorSearchUnavailableError,
    search_document_chunks,
)
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

BRIEFING_PROMPT_VERSION = "startup-advisor-briefing-prompt-v2"

SYSTEM_PROMPT = """
You are a grounded startup advisor for Indian founders.

Use only facts present in the supplied persisted startup advisor snapshot.
Never invent eligibility, application status, deadlines, benefits,
government requirements, scores, or founder facts.

Every top priority, scheme-guidance item, and risk must cite one or more
exact source references. Each field_path must use RFC 6901 JSON Pointer
syntax, begin with "/", and resolve inside the cited source object.

Use paths such as "/blocking_findings/0/reason".
Never use JavaScript notation such as "/blocking_findings[0].reason".
Do not prefix field_path with source_type: use "/blocking_findings/0",
not "/readiness/blocking_findings/0".

Source types:
- profile
- readiness
- action_plan
- recommendation_generation
- recommendation
- evidence_chunk

Retrieved evidence chunks are supporting official-source context. They never
override deterministic eligibility, readiness, recommendation or deadline
records. Cite a retrieved chunk with its listed chunk ID and a path such as
"/text", "/source_url", "/page_number" or "/title".

Use only source IDs listed in citation_contract.source_ids_by_type.
The source_id must exactly match an ID listed for its source_type.
Never use nested identifiers such as assessment_id, scheme_id or profile_id
as source_id unless they are explicitly listed in the citation contract.

Each scheme-guidance item must cite at least one persisted recommendation.
When citation_contract.scheme_guidance_must_be_empty is true, return
"scheme_guidance": [] exactly. Excluded schemes may instead inform risks or
priorities using the recommendation_generation document.

When information is absent, state that it is unknown and add a practical
question for the founder.
Return only a JSON object matching the supplied JSON schema.

Keep the briefing concise:
- return no more than 3 top priorities
- return no more than 3 scheme-guidance items
- return no more than 3 risks
- return no more than 5 founder questions
- keep each prose field to at most 2 short sentences
- normally use exactly 1 source reference per item
- do not fill arrays merely to reach their schema maximum
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




def _build_rag_query(input_payload: dict[str, Any]) -> str:
    profile = input_payload.get("profile") or {}
    recommendations = input_payload.get("recommendations") or []

    values: list[str] = [
        str(profile.get("startup_name") or ""),
        str(profile.get("description") or ""),
        str(profile.get("stage") or ""),
        str(profile.get("state") or ""),
        str(profile.get("district") or ""),
        str(profile.get("funding_purpose") or ""),
        str(profile.get("revenue_stage") or ""),
    ]
    for field in ("sectors", "technologies", "resource_needs"):
        value = profile.get(field)
        if isinstance(value, list):
            values.extend(str(item) for item in value)

    for recommendation in recommendations[:5]:
        if not isinstance(recommendation, dict):
            continue
        scheme_snapshot = recommendation.get("scheme_snapshot") or {}
        values.extend(
            [
                str(scheme_snapshot.get("canonical_name") or ""),
                str(scheme_snapshot.get("summary") or ""),
                str(recommendation.get("reason") or ""),
            ]
        )

    return "\n".join(
        value.strip()
        for value in values
        if value and value.strip()
    )[:12000]


def retrieve_startup_advisor_evidence(
    input_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    if not settings.STARTUP_ADVISOR_RAG_ENABLED:
        return []

    query = _build_rag_query(input_payload)
    if not query:
        return []

    return [
        result.as_prompt_document()
        for result in search_document_chunks(query)
    ]


def _retrieve_evidence(
    input_payload: dict[str, Any],
    retriever,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not settings.STARTUP_ADVISOR_RAG_ENABLED:
        return [], {
            "status": "disabled",
            "query": "",
            "result_count": 0,
        }

    query = _build_rag_query(input_payload)
    try:
        evidence = retriever(input_payload)
    except (VectorSearchUnavailableError, RuntimeError) as exc:
        return [], {
            "status": "unavailable",
            "query": query,
            "result_count": 0,
            "error": str(exc)[:1000],
        }

    return evidence, {
        "status": "succeeded",
        "query": query,
        "result_count": len(evidence),
    }


def _build_citation_contract(
    input_payload: dict[str, Any],
    retrieved_evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    source_ids = input_payload["source_ids"]

    recommendation_ids = [
        str(recommendation["id"])
        for recommendation in input_payload["recommendations"]
        if (isinstance(recommendation, dict) and recommendation.get("id"))
    ]

    source_ids_by_type = {
        "profile": [
            str(input_payload["startup_profile_id"]),
        ],
        "readiness": (
            [str(source_ids["readiness_assessment_id"])]
            if source_ids["readiness_assessment_id"]
            else []
        ),
        "action_plan": (
            [str(source_ids["readiness_action_plan_id"])]
            if source_ids["readiness_action_plan_id"]
            else []
        ),
        "recommendation_generation": (
            [str(source_ids["recommendation_generation_run_id"])]
            if source_ids["recommendation_generation_run_id"]
            else []
        ),
        "recommendation": recommendation_ids,
        "evidence_chunk": [
            str(item["id"])
            for item in retrieved_evidence
            if isinstance(item, dict) and item.get("id")
        ],
    }

    return {
        "source_ids_by_type": source_ids_by_type,
        "scheme_guidance_must_be_empty": (not recommendation_ids),
    }


def build_startup_advisor_briefing_prompt(
    *,
    source_snapshot: StartupAdvisorSnapshot,
    retrieved_evidence: list[dict[str, Any]] | None = None,
    retrieval: dict[str, Any] | None = None,
) -> dict[str, Any]:
    input_payload = snapshot_to_llm_input(source_snapshot)
    evidence_documents = deepcopy(retrieved_evidence or [])
    retrieval_snapshot = deepcopy(
        retrieval
        or {
            "status": "disabled",
            "query": "",
            "result_count": 0,
        }
    )
    citation_contract = _build_citation_contract(
        input_payload,
        evidence_documents,
    )

    response_schema = deepcopy(
        STARTUP_ADVISOR_BRIEFING_SCHEMA,
    )
    if citation_contract["scheme_guidance_must_be_empty"]:
        response_schema["properties"]["scheme_guidance"]["maxItems"] = 0

    user_payload = {
        "citation_contract": citation_contract,
        "startup_advisor_snapshot": input_payload,
        "retrieved_evidence": evidence_documents,
        "retrieval": retrieval_snapshot,
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
        "response_schema": response_schema,
        "source_input": input_payload,
        "retrieved_evidence": evidence_documents,
        "retrieval": retrieval_snapshot,
    }


def generate_startup_advisor_briefing(
    *,
    source_snapshot: StartupAdvisorSnapshot,
    requested_by: Any,
    provider: StartupAdvisorLLMProvider | None = None,
    retriever=None,
) -> StartupAdvisorBriefing:
    input_payload = snapshot_to_llm_input(source_snapshot)
    active_retriever = (
        retriever
        if retriever is not None
        else retrieve_startup_advisor_evidence
    )
    retrieved_evidence, retrieval = _retrieve_evidence(
        input_payload,
        active_retriever,
    )
    prompt_snapshot = build_startup_advisor_briefing_prompt(
        source_snapshot=source_snapshot,
        retrieved_evidence=retrieved_evidence,
        retrieval=retrieval,
    )
    active_provider = provider if provider is not None else get_startup_advisor_llm_provider()
    generation_result = active_provider.generate(
        messages=prompt_snapshot["messages"],
        response_schema=prompt_snapshot["response_schema"],
    )
    briefing_payload = validate_startup_advisor_briefing(
        payload=generation_result.payload,
        source_snapshot=source_snapshot,
        evidence_documents=prompt_snapshot["retrieved_evidence"],
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
