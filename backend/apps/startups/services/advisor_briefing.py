from __future__ import annotations

import json
import re
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

BRIEFING_PROMPT_VERSION = "startup-advisor-briefing-prompt-v3"

SYSTEM_PROMPT = """
You are a grounded startup advisor for Indian founders.

Use only facts present in the supplied persisted startup advisor snapshot.
Never invent eligibility, application status, deadlines, benefits,
government requirements, scores, or founder facts.

Every top priority, scheme-guidance item, and risk must cite one or more
exact source references. Each field_path must use RFC 6901 JSON Pointer
syntax, begin with "/", and resolve inside the cited source object.
Array indexes are zero-based. For an array containing N items, valid indexes
are 0 through N-1; never cite N as an array index.

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

When citation_contract.evidence_citation_expected is true, cite at least one
retrieved evidence chunk if it directly supports a briefing item. Keep the
deterministic source citation as well when the statement concerns eligibility,
readiness, ranking, deadlines or founder facts. Never cite retrieved evidence
merely to satisfy the contract when it does not support the specific item.

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
        "evidence_citation_expected": bool(
            source_ids_by_type["evidence_chunk"]
        ),
    }


_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    {
        "about",
        "after",
        "against",
        "application",
        "apply",
        "available",
        "before",
        "briefing",
        "business",
        "complete",
        "current",
        "document",
        "eligible",
        "eligibility",
        "evidence",
        "founder",
        "founders",
        "funding",
        "government",
        "guidance",
        "india",
        "official",
        "provide",
        "recommendation",
        "requirements",
        "scheme",
        "startup",
        "startups",
        "status",
        "support",
        "verify",
        "with",
    }
)
_HIGH_SIGNAL_TERMS = frozenset(
    {
        "cgss",
        "collateral",
        "dpiit",
        "incubator",
        "recognised",
        "recognition",
        "sisfs",
        "udyam",
    }
)


def _meaningful_terms(*values: Any) -> set[str]:
    combined = " ".join(
        str(value)
        for value in values
        if value is not None
    ).lower()
    return {
        token
        for token in _TOKEN_PATTERN.findall(combined)
        if len(token) >= 4 and token not in _STOPWORDS
    }


def _briefing_item_candidates(payload: dict[str, Any]):
    field_names = {
        "top_priorities": (
            "title",
            "reason",
            "recommended_action",
        ),
        "scheme_guidance": (
            "scheme_name",
            "guidance",
        ),
        "risks": (
            "title",
            "reason",
            "mitigation",
        ),
    }
    for section, fields in field_names.items():
        for index, item in enumerate(payload.get(section) or []):
            if not isinstance(item, dict):
                continue
            yield {
                "section": section,
                "index": index,
                "item": item,
                "terms": _meaningful_terms(
                    *(item.get(field) for field in fields)
                ),
            }


def _existing_evidence_references(
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    for candidate in _briefing_item_candidates(payload):
        references.extend(
            reference
            for reference in (
                candidate["item"].get("source_references")
                or []
            )
            if reference.get("source_type") == "evidence_chunk"
        )
    return references


def _best_item_evidence_match(
    payload: dict[str, Any],
    evidence_documents: list[dict[str, Any]],
) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None

    for candidate in _briefing_item_candidates(payload):
        item_terms = candidate["terms"]
        if not item_terms:
            continue

        for evidence in evidence_documents:
            if not isinstance(evidence, dict) or not evidence.get("id"):
                continue

            evidence_terms = _meaningful_terms(
                evidence.get("title"),
                evidence.get("heading"),
                evidence.get("text"),
            )
            overlap = item_terms & evidence_terms
            has_high_signal = bool(overlap & _HIGH_SIGNAL_TERMS)
            if len(overlap) < 2 and not has_high_signal:
                continue

            match_score = (
                len(overlap) * 100
                + sum(len(term) for term in overlap)
                + int(float(evidence.get("score") or 0) * 10)
            )
            if best is None or match_score > best["match_score"]:
                best = {
                    **candidate,
                    "evidence": evidence,
                    "matched_terms": sorted(overlap),
                    "match_score": match_score,
                }

    return best


def _apply_retrieved_evidence_usage(
    *,
    payload: Any,
    source_snapshot: StartupAdvisorSnapshot,
    evidence_documents: list[dict[str, Any]],
    retrieval: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    validated = validate_startup_advisor_briefing(
        payload=payload,
        source_snapshot=source_snapshot,
        evidence_documents=evidence_documents,
    )

    existing = _existing_evidence_references(validated)
    if existing:
        return validated, {
            "status": "model_cited",
            "reason": "The model cited retrieved evidence directly.",
            "citation_count": len(existing),
            "evidence_source_ids": sorted(
                {
                    reference["source_id"]
                    for reference in existing
                }
            ),
        }

    if not evidence_documents:
        return validated, {
            "status": "not_available",
            "reason": (
                "No retrieved evidence document was available; "
                f"retrieval status was {retrieval.get('status', 'unknown')}."
            ),
            "citation_count": 0,
            "evidence_source_ids": [],
        }

    match = _best_item_evidence_match(
        validated,
        evidence_documents,
    )
    if match is None:
        return validated, {
            "status": "not_used",
            "reason": (
                "Retrieved evidence was available, but no briefing item "
                "had sufficient item-level term overlap."
            ),
            "citation_count": 0,
            "evidence_source_ids": [],
        }

    reference = {
        "source_type": "evidence_chunk",
        "source_id": str(match["evidence"]["id"]),
        "field_path": "/text",
    }
    match["item"].setdefault(
        "source_references",
        [],
    ).append(reference)

    validated = validate_startup_advisor_briefing(
        payload=validated,
        source_snapshot=source_snapshot,
        evidence_documents=evidence_documents,
        require_evidence_citation=True,
    )
    return validated, {
        "status": "deterministic_attachment",
        "reason": (
            "A retrieved evidence citation was attached after a "
            "deterministic item-level relevance match."
        ),
        "citation_count": 1,
        "evidence_source_ids": [
            str(match["evidence"]["id"]),
        ],
        "section": match["section"],
        "item_index": match["index"],
        "matched_terms": match["matched_terms"],
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
        "citation_contract": citation_contract,
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
    briefing_payload, evidence_usage = (
        _apply_retrieved_evidence_usage(
            payload=generation_result.payload,
            source_snapshot=source_snapshot,
            evidence_documents=prompt_snapshot[
                "retrieved_evidence"
            ],
            retrieval=prompt_snapshot["retrieval"],
        )
    )
    prompt_snapshot["evidence_usage"] = deepcopy(
        evidence_usage,
    )
    response_metadata = deepcopy(
        generation_result.response_metadata or {},
    )
    response_metadata["evidence_usage"] = deepcopy(
        evidence_usage,
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
            response_metadata=response_metadata,
            completed_at=timezone.now(),
        )
