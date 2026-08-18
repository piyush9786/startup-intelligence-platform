"""Production compact contracts for StartupIntel-SLM.

Django owns:
- source truth
- UUIDs and URLs
- eligibility/readiness decisions
- evidence trust filtering
- alias validation

The SLM only receives compact facts/evidence and emits compact aliases.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from jsonschema import Draft202012Validator

from .slm_alias_contract import (
    SLMAliasContractError,
    compact_advisor_schema,
    expand_compact_advisor_output,
)

ADVISOR_SYSTEM = (
    "TASK=FOUNDER_ADVISOR\n"
    "Use only supplied facts and REF_### aliases. "
    "Return concise JSON only. Never invent eligibility, schemes, "
    "deadlines, source IDs, URLs or facts."
)

RESEARCH_SYSTEM = (
    "TASK=RESEARCH_SYNTHESIS\n"
    "Use only supplied EVIDENCE_### items. "
    "This is a compact synthesis task, not an exhaustive report. "
    "Return no more than 3 distinct findings and no more than "
    "3 risks_or_unknowns. "
    "executive_summary must be at most 60 words. "
    "Each finding text must be at most 45 words. "
    "Each risk_or_unknown must be at most 25 words. "
    "source_quality_note must be at most 35 words. "
    "Prefer verified_internal and official_live evidence, then "
    "reputable_secondary evidence. "
    "Unverified evidence must never be described as official, "
    "verified, authoritative, or confirmed. "
    "Do not repeat equivalent findings. "
    "Do not claim counts, totals, dates, amounts, eligibility, "
    "deadlines, trends, or comparisons unless explicitly supported "
    "by the cited evidence. "
    "If evidence does not support a requested topic, put a short "
    "statement in risks_or_unknowns instead of inventing a fact. "
    "Return STRICT JSON only. "
    "The first character of the response MUST be { and the "
    "final character MUST be }. "
    "Use double quotes for JSON keys and string values. "
    "Do not output YAML, markdown, headings, bullets, code fences, "
    "comments, or prose outside JSON. "
    "Return exactly these top-level keys: \"executive_summary\", \"findings\", "
    "\"risks_or_unknowns\", \"source_quality_note\". "
    "Each \"findings\" item must contain exactly \"title\", \"finding\", "
    "\"confidence\", \"evidence_ids\". "
    "confidence must be high, medium, or low. "
    "evidence_ids must contain only supplied EVIDENCE_### aliases. "
    "Stop immediately after the closing top-level JSON brace. "
    "Never invent sources, URLs, numbers, IDs, or facts."
)

PROFILE_KEYS = {
    "id",
    "startup_name",
    "name",
    "legal_name",
    "stage",
    "state",
    "district",
    "sectors",
    "technologies",
    "team_size",
    "annual_turnover",
    "revenue_stage",
    "funding_required",
    "funding_purpose",
    "dpiit_recognized",
    "udyam_registered",
    "incorporation_type",
    "incorporation_date",
}


def _compact_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _compact_profile(
    profile: Any,
) -> dict[str, Any]:
    if not isinstance(profile, dict):
        return {}

    result = {
        key: value
        for key, value in profile.items()
        if (
            key in PROFILE_KEYS
            and value not in (None, "", [], {})
        )
    }

    profile_data = profile.get("profile_data")

    if isinstance(profile_data, dict):
        for key in (
            "team_size",
            "target_customer",
            "business_model",
            "revenue_model",
            "entity_types",
        ):
            value = profile_data.get(key)

            if value not in (
                None,
                "",
                [],
                {},
            ):
                result[key] = value

    return result


def _compact_schemes(
    recommendations: Any,
) -> list[dict[str, Any]]:
    if not isinstance(recommendations, list):
        return []

    result = []

    for index, item in enumerate(
        recommendations[:5],
        start=1,
    ):
        if not isinstance(item, dict):
            continue

        result.append(
            {
                "alias": f"SCHEME_{index:03d}",
                "name": (
                    item.get("scheme_name")
                    or item.get("canonical_name")
                    or item.get("name")
                    or f"Scheme {index}"
                ),
                "eligibility_status": (
                    item.get("assessment_result")
                    or item.get("eligibility_result")
                    or item.get("eligibility_status")
                    or item.get("status")
                ),
                "match_score": (
                    item.get("ranking_score")
                    or item.get("match_score")
                    or item.get("score")
                ),
                "reason": str(
                    item.get("explanation")
                    or item.get("reason")
                    or item.get("rationale")
                    or ""
                )[:500],
            }
        )

    return result


def build_compact_advisor_request(
    *,
    source_input: dict[str, Any],
    retrieved_evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the exact compact FOUNDER_ADVISOR runtime contract."""

    profile = (
        source_input.get("profile")
        if isinstance(
            source_input.get("profile"),
            dict,
        )
        else {}
    )

    readiness = (
        source_input.get("readiness")
        if isinstance(
            source_input.get("readiness"),
            dict,
        )
        else {}
    )

    action_plan = (
        source_input.get("action_plan")
        if isinstance(
            source_input.get("action_plan"),
            dict,
        )
        else {}
    )

    recommendations = (
        source_input.get("recommendations")
        if isinstance(
            source_input.get("recommendations"),
            list,
        )
        else []
    )

    evidence = [
        item
        for item in (
            retrieved_evidence or []
        )
        if isinstance(item, dict)
    ][:5]

    reference_facts: list[dict[str, Any]] = []
    reference_map: dict[
        str,
        dict[str, str],
    ] = {}

    def add_reference(
        *,
        source_alias: str,
        source_type: str,
        source_id: Any,
        path: str,
        value: Any,
    ) -> None:
        if (
            not source_id
            or value in (
                None,
                "",
                [],
                {},
            )
        ):
            return

        if len(reference_facts) >= 8:
            return

        alias = (
            f"REF_{len(reference_facts) + 1:03d}"
        )

        reference_facts.append(
            {
                "id": alias,
                "source": source_alias,
                "path": path,
                "value": value,
            }
        )

        reference_map[alias] = {
            "source_type": source_type,
            "source_id": str(source_id),
            "field_path": path,
        }

    readiness_id = readiness.get("id")

    blockers = readiness.get(
        "blocking_findings",
        [],
    )

    if isinstance(blockers, list):
        for index, blocker in enumerate(
            blockers[:3],
        ):
            if not isinstance(blocker, dict):
                continue

            value = (
                blocker.get("reason")
                or blocker.get("title")
                or blocker.get("action")
            )

            if blocker.get("reason"):
                path = (
                    f"/blocking_findings/"
                    f"{index}/reason"
                )
            elif blocker.get("title"):
                path = (
                    f"/blocking_findings/"
                    f"{index}/title"
                )
            else:
                path = (
                    f"/blocking_findings/"
                    f"{index}/action"
                )

            add_reference(
                source_alias="READINESS_001",
                source_type="readiness",
                source_id=readiness_id,
                path=path,
                value=value,
            )

    for index, recommendation in enumerate(
        recommendations[:3],
        start=1,
    ):
        if not isinstance(
            recommendation,
            dict,
        ):
            continue

        recommendation_id = (
            recommendation.get("id")
        )

        scheme_name = (
            recommendation.get("scheme_name")
            or recommendation.get(
                "canonical_name"
            )
        )

        scheme_path = (
            "/scheme_name"
            if recommendation.get("scheme_name")
            else "/canonical_name"
        )

        add_reference(
            source_alias=f"SCHEME_{index:03d}",
            source_type="recommendation",
            source_id=recommendation_id,
            path=scheme_path,
            value=scheme_name,
        )

    profile_id = profile.get("id")

    add_reference(
        source_alias="PROFILE_001",
        source_type="profile",
        source_id=profile_id,
        path="/sectors",
        value=profile.get("sectors"),
    )

    if not reference_facts:
        readiness_status_key = (
            "readiness_status"
            if readiness.get("readiness_status")
            else "status"
        )

        add_reference(
            source_alias="READINESS_001",
            source_type="readiness",
            source_id=readiness_id,
            path=f"/{readiness_status_key}",
            value=readiness.get(
                readiness_status_key
            ),
        )

    for index, item in enumerate(
        evidence[:2],
        start=1,
    ):
        evidence_id = item.get("id")

        text = (
            item.get("text")
            or item.get("content_excerpt")
            or item.get("content")
        )

        if text:
            path = (
                "/text"
                if item.get("text")
                else (
                    "/content_excerpt"
                    if item.get(
                        "content_excerpt"
                    )
                    else "/content"
                )
            )

            add_reference(
                source_alias=(
                    f"EVIDENCE_{index:03d}"
                ),
                source_type="evidence_chunk",
                source_id=evidence_id,
                path=path,
                value=str(text)[:700],
            )

    compact_readiness = {
        key: readiness[key]
        for key in (
            "readiness_status",
            "status",
            "overall_score",
            "critical_score",
            "score",
            "summary",
        )
        if key in readiness
    }

    if blockers:
        compact_readiness[
            "blocking_findings"
        ] = blockers[:3]

    compact_action = {
        key: action_plan[key]
        for key in (
            "readiness_status",
            "next_action",
            "blocker_count",
            "total_action_count",
        )
        if key in action_plan
    }

    payload = {
        "task": "FOUNDER_ADVISOR",
        "profile": _compact_profile(
            profile
        ),
        "readiness": compact_readiness,
        "action_plan": compact_action,
        "schemes": _compact_schemes(
            recommendations
        ),
        "evidence": [
            {
                "alias": (
                    f"EVIDENCE_{index:03d}"
                ),
                "title": item.get(
                    "title",
                    "",
                ),
                "verification_status": (
                    item.get(
                        "verification_status",
                        "",
                    )
                ),
                "excerpt": str(
                    item.get("text")
                    or item.get(
                        "content_excerpt"
                    )
                    or item.get("content")
                    or ""
                )[:700],
            }
            for index, item in enumerate(
                evidence[:5],
                start=1,
            )
        ],
        "reference_facts": (
            reference_facts
        ),
    }

    messages = [
        {
            "role": "system",
            "content": ADVISOR_SYSTEM,
        },
        {
            "role": "user",
            "content": _compact_json(
                payload
            ),
        },
    ]

    return {
        "messages": messages,
        "response_schema": (
            compact_advisor_schema()
        ),
        "payload": payload,
        "reference_map": reference_map,
    }


def compact_research_schema() -> dict[str, Any]:
    evidence_ids = {
        "type": "array",
        "minItems": 1,
        "maxItems": 4,
        "items": {
            "type": "string",
            "pattern": (
                "^EVIDENCE_[0-9]{3}$"
            ),
        },
    }

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "executive_summary": {
                "type": "string",
                "maxLength": 600,
            },
            "findings": {
                "type": "array",
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "title": {
                            "type": "string",
                            "maxLength": 180,
                        },
                        "finding": {
                            "type": "string",
                            "maxLength": 600,
                        },
                        "confidence": {
                            "type": "string",
                            "enum": [
                                "high",
                                "medium",
                                "low",
                            ],
                        },
                        "evidence_ids": (
                            evidence_ids
                        ),
                    },
                    "required": [
                        "title",
                        "finding",
                        "confidence",
                        "evidence_ids",
                    ],
                },
            },
            "risks_or_unknowns": {
                "type": "array",
                "maxItems": 3,
                "items": {
                    "type": "string",
                    "maxLength": 400,
                },
            },
            "source_quality_note": {
                "type": "string",
                "maxLength": 500,
            },
        },
        "required": [
            "executive_summary",
            "findings",
            "risks_or_unknowns",
            "source_quality_note",
        ],
    }

ADVISOR_VALIDATOR = Draft202012Validator(
    compact_advisor_schema()
)


def normalize_compact_advisor_output(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Apply only safe structural defaults.

    Missing collection fields become empty arrays.

    We deliberately do NOT manufacture:
    - summaries,
    - priorities,
    - risks,
    - citations,
    - facts,
    - scheme guidance.

    Wrongly typed fields are not corrected; schema validation
    must reject them.
    """

    if not isinstance(payload, dict):
        raise SLMAliasContractError(
            "Compact advisor output must be an object."
        )

    normalized = deepcopy(payload)

    for field in (
        "questions_for_founder",
        "risks",
        "scheme_guidance",
        "top_priorities",
    ):
        if field not in normalized:
            normalized[field] = []

    # Some real-world generations add descriptive fields such as
    # "reason" or "title" to scheme_guidance items even though they
    # are not part of the compact contract.
    #
    # Drop only unsupported keys. Required values are never created,
    # renamed, or inferred; the JSON Schema remains authoritative.
    scheme_guidance = normalized.get(
        "scheme_guidance"
    )

    if isinstance(scheme_guidance, list):
        schema = compact_advisor_schema()

        allowed_scheme_keys = set(
            schema["properties"]
            ["scheme_guidance"]
            ["items"]
            ["properties"]
        )

        normalized["scheme_guidance"] = [
            {
                key: value
                for key, value in item.items()
                if key in allowed_scheme_keys
            }
            if isinstance(item, dict)
            else item
            for item in scheme_guidance
        ]

    # Keep founder-facing output concise.
    # This only removes lower-priority generated items;
    # it never creates facts or citations.
    normalized["questions_for_founder"] = (
        normalized["questions_for_founder"][:2]
    )

    normalized["risks"] = (
        normalized["risks"][:3]
    )

    normalized["scheme_guidance"] = (
        normalized["scheme_guidance"][:3]
    )

    normalized["top_priorities"] = (
        normalized["top_priorities"][:3]
    )

    return normalized


def validate_and_expand_compact_advisor_output(
    payload: dict[str, Any],
    *,
    reference_map: dict[str, dict[str, str]],
) -> dict[str, Any]:
    """Validate compact Advisor JSON and expand REF aliases."""

    normalized = normalize_compact_advisor_output(
        payload
    )

    errors = sorted(
        ADVISOR_VALIDATOR.iter_errors(normalized),
        key=lambda error: list(error.path),
    )

    if errors:
        first = errors[0]

        location = "/".join(
            str(item)
            for item in first.path
        ) or "<root>"

        raise SLMAliasContractError(
            "Compact advisor schema validation "
            f"failed at {location}: "
            f"{first.message}"
        )

    return expand_compact_advisor_output(
        normalized,
        reference_map=reference_map,
    )


def normalize_compact_research_output(
    payload: dict[str, Any],
    *,
    evidence_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Normalize only the known legacy Research SLM shape.

    Django remains authoritative for schema and evidence aliases.
    Unknown properties are deliberately preserved so strict schema
    validation can still reject unexpected model behavior.
    """

    if not isinstance(payload, dict):
        return payload

    normalized = deepcopy(payload)

    legacy_risks = normalized.pop(
        "risks",
        None,
    )

    # These existed in the older SLM Research contract.
    # They are intentionally removed instead of being promoted
    # into factual report sections without evidence aliases.
    normalized.pop(
        "recommended_actions",
        None,
    )
    normalized.pop(
        "questions_for_guidance",
        None,
    )

    if "risks_or_unknowns" not in normalized:
        converted_risks: list[str] = []

        if isinstance(legacy_risks, list):
            for item in legacy_risks[:6]:
                if isinstance(item, str):
                    value = " ".join(
                        item.split()
                    ).strip()

                    if value:
                        converted_risks.append(
                            value[:450]
                        )

                    continue

                if not isinstance(item, dict):
                    continue

                raw_aliases = (
                    item.get("evidence")
                    or item.get("evidence_ids")
                    or []
                )

                if not isinstance(
                    raw_aliases,
                    list,
                ):
                    raise SLMAliasContractError(
                        "Legacy research risk evidence "
                        "must be a list."
                    )

                for alias in raw_aliases:
                    if (
                        not isinstance(alias, str)
                        or alias not in evidence_map
                    ):
                        raise SLMAliasContractError(
                            "Unknown legacy research "
                            f"evidence alias: {alias}"
                        )

                title = " ".join(
                    str(
                        item.get("title")
                        or ""
                    ).split()
                ).strip()

                reason = " ".join(
                    str(
                        item.get("reason")
                        or item.get("risk")
                        or item.get("finding")
                        or ""
                    ).split()
                ).strip()

                if title and reason:
                    value = (
                        f"{title}: {reason}"
                    )
                else:
                    value = reason or title

                if value:
                    converted_risks.append(
                        value[:450]
                    )

        normalized[
            "risks_or_unknowns"
        ] = converted_risks[:6]

    if "source_quality_note" not in normalized:
        primary_count = 0
        secondary_count = 0
        unverified_count = 0

        for item in evidence_map.values():
            if not isinstance(item, dict):
                continue

            status = str(
                item.get(
                    "verification_status"
                )
                or ""
            )

            if status in {
                "verified_internal",
                "official_live",
            }:
                primary_count += 1

            elif (
                status
                == "reputable_secondary"
            ):
                secondary_count += 1

            elif status == "unverified_live":
                unverified_count += 1

        normalized[
            "source_quality_note"
        ] = (
            "Evidence supplied by Django: "
            f"{primary_count} verified/official, "
            f"{secondary_count} reputable secondary, "
            f"{unverified_count} unverified."
        )

    return normalized


RESEARCH_VALIDATOR = Draft202012Validator(
    compact_research_schema()
)


def build_compact_research_request(
    *,
    question: str,
    live_evidence: list[dict[str, Any]],
    vector_evidence: list[dict[str, Any]],
    local_evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    """Apply deterministic evidence trust filtering before the SLM."""

    candidates: list[dict[str, Any]] = []

    def add_items(
        items: list[dict[str, Any]],
        *,
        default_status: str,
    ) -> None:
        for item in items:
            if not isinstance(item, dict):
                continue

            status = str(
                item.get(
                    "verification_status"
                )
                or default_status
            )

            if status == "rejected":
                continue

            excerpt = (
                item.get("content_excerpt")
                or item.get("text")
                or item.get("content")
                or item.get("excerpt")
                or ""
            )

            if not str(excerpt).strip():
                continue

            normalized = dict(item)

            normalized[
                "verification_status"
            ] = status

            normalized[
                "_excerpt"
            ] = " ".join(
                str(excerpt).split()
            )[:350]

            candidates.append(
                normalized
            )

    add_items(
        local_evidence,
        default_status="verified_internal",
    )

    add_items(
        vector_evidence,
        default_status="unverified_live",
    )

    add_items(
        live_evidence,
        default_status="unverified_live",
    )

    primary = [
        item
        for item in candidates
        if item[
            "verification_status"
        ]
        in {
            "verified_internal",
            "official_live",
        }
    ]

    secondary = [
        item
        for item in candidates
        if item[
            "verification_status"
        ]
        == "reputable_secondary"
    ]

    unverified = [
        item
        for item in candidates
        if item[
            "verification_status"
        ]
        == "unverified_live"
    ]

    def evidence_score(
        item: dict[str, Any],
    ) -> float:
        try:
            return float(
                item.get(
                    "confidence_score",
                    item.get("score", 0.0),
                )
                or 0.0
            )
        except (TypeError, ValueError):
            return 0.0

    # Research requires more than authority-only evidence.
    #
    # Keep verified/official evidence dominant, while reserving
    # bounded room for reputable market/competitor evidence and
    # limited unverified discovery evidence.
    primary = sorted(
        primary,
        key=evidence_score,
        reverse=True,
    )

    secondary = sorted(
        secondary,
        key=evidence_score,
        reverse=True,
    )

    unverified = sorted(
        unverified,
        key=evidence_score,
        reverse=True,
    )

    selected: list[dict[str, Any]] = []

    def evidence_identity(
        item: dict[str, Any],
    ) -> tuple[str, str]:
        url = str(
            item.get("url")
            or item.get("source_url")
            or ""
        ).strip().casefold()

        title = str(
            item.get("title")
            or item.get("heading")
            or ""
        ).strip().casefold()

        return url, title

    selected_identities: set[
        tuple[str, str]
    ] = set()

    def add_selected(
        items: list[dict[str, Any]],
        limit: int,
    ) -> None:
        for item in items:
            if len(selected) >= 4:
                return

            identity = evidence_identity(
                item
            )

            if identity in selected_identities:
                continue

            selected.append(item)
            selected_identities.add(
                identity
            )

            limit -= 1

            if limit <= 0:
                return

    # Compact balanced allocation.
    #
    # Strong evidence dominates the LLM context.
    # Unverified discovery evidence is used only when
    # stronger evidence leaves unused capacity.
    add_selected(primary, 3)
    add_selected(secondary, 1)
    add_selected(unverified, 1)

    # Fill any unused capacity from remaining evidence.
    # Trust remains deterministic:
    # primary > secondary > unverified.
    for tier in (
        primary,
        secondary,
        unverified,
    ):
        if len(selected) >= 4:
            break

        add_selected(
            tier,
            4 - len(selected),
        )

    evidence_payload = []
    evidence_map = {}

    for index, item in enumerate(
        selected,
        start=1,
    ):
        alias = (
            f"EVIDENCE_{index:03d}"
        )

        score = float(
            item.get(
                "confidence_score",
                item.get("score", 0.5),
            )
            or 0.5
        )

        score = max(
            0.0,
            min(1.0, score),
        )

        evidence_payload.append(
            {
                "id": alias,
                "title": (
                    item.get("title")
                    or item.get("heading")
                    or item.get("publisher")
                    or "Evidence"
                ),
                "source_type": (
                    item.get("source_type")
                    or "unknown"
                ),
                "verification_status": (
                    item[
                        "verification_status"
                    ]
                ),
                "confidence_score": score,
                "excerpt": (
                    item["_excerpt"]
                ),
            }
        )

        evidence_map[alias] = {
            "url": str(
                item.get("url")
                or item.get("source_url")
                or ""
            ),
            "title": str(
                item.get("title")
                or item.get("heading")
                or ""
            ),
            "verification_status": (
                item[
                    "verification_status"
                ]
            ),
            "confidence_score": score,
        }

    model_question = " ".join(
        str(question).split()
    )

    if model_question.casefold().startswith(
        "create a comprehensive founder research report"
    ):
        model_question = (
            "Identify the 3 strongest decision-useful, "
            "evidence-backed insights for this startup. "
            "Prioritize verified current opportunities, "
            "market developments, material risks, or "
            "requirements that the supplied evidence "
            "directly supports."
        )

    payload = {
        "task": "RESEARCH_SYNTHESIS",
        "question": model_question,
        "evidence": evidence_payload,
    }

    return {
        "messages": [
            {
                "role": "system",
                "content": RESEARCH_SYSTEM,
            },
            {
                "role": "user",
                "content": _compact_json(
                    payload
                ),
            },
        ],
        "response_schema": (
            compact_research_schema()
        ),
        "payload": payload,
        "evidence_map": evidence_map,
    }


def validate_compact_research_output(
    payload: dict[str, Any],
    *,
    evidence_map: dict[
        str,
        dict[str, Any],
    ],
) -> list[str]:
    """Validate shape and return cited evidence aliases."""

    RESEARCH_VALIDATOR.validate(
        payload
    )

    available = set(
        evidence_map
    )

    used: list[str] = []

    for finding in payload.get(
        "findings",
        [],
    ):
        for alias in finding.get(
            "evidence_ids",
            [],
        ):
            if alias not in available:
                raise SLMAliasContractError(
                    "Unknown research evidence "
                    f"alias: {alias}"
                )

            if alias not in used:
                used.append(alias)

    return used
