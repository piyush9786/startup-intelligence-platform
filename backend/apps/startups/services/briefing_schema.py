from __future__ import annotations

import re
from typing import Any

from jsonschema import Draft202012Validator

from apps.startups.models import StartupAdvisorSnapshot

BRIEFING_SCHEMA_VERSION = "startup-advisor-briefing-schema-v3"
BRIEFING_DISCLAIMER = (
    "AI-generated guidance grounded in the cited persisted snapshot and "
    "retrieved official evidence; verify official requirements before acting."
)

SOURCE_TYPES = (
    "profile",
    "readiness",
    "action_plan",
    "recommendation_generation",
    "recommendation",
    "evidence_chunk",
)

SOURCE_REFERENCE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "source_type": {
            "type": "string",
            "enum": list(SOURCE_TYPES),
        },
        "source_id": {
            "type": "string",
            "format": "uuid",
        },
        "field_path": {
            "type": "string",
            "minLength": 1,
            "maxLength": 500,
            "pattern": "^/.*$",
        },
    },
    "required": [
        "source_type",
        "source_id",
        "field_path",
    ],
}

STARTUP_ADVISOR_BRIEFING_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "executive_summary": {
            "type": "string",
            "minLength": 1,
            "maxLength": 2000,
        },
        "current_position": {
            "type": "string",
            "minLength": 1,
            "maxLength": 2000,
        },
        "top_priorities": {
            "type": "array",
            "maxItems": 5,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "priority": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                    },
                    "title": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 300,
                    },
                    "reason": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 1500,
                    },
                    "recommended_action": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 1500,
                    },
                    "source_references": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 10,
                        "items": SOURCE_REFERENCE_SCHEMA,
                    },
                },
                "required": [
                    "priority",
                    "title",
                    "reason",
                    "recommended_action",
                    "source_references",
                ],
            },
        },
        "scheme_guidance": {
            "type": "array",
            "maxItems": 10,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "scheme_name": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 500,
                    },
                    "guidance": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 1500,
                    },
                    "source_references": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 10,
                        "items": SOURCE_REFERENCE_SCHEMA,
                    },
                },
                "required": [
                    "scheme_name",
                    "guidance",
                    "source_references",
                ],
            },
        },
        "risks": {
            "type": "array",
            "maxItems": 5,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 300,
                    },
                    "reason": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 1500,
                    },
                    "mitigation": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 1500,
                    },
                    "source_references": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 10,
                        "items": SOURCE_REFERENCE_SCHEMA,
                    },
                },
                "required": [
                    "title",
                    "reason",
                    "mitigation",
                    "source_references",
                ],
            },
        },
        "questions_for_founder": {
            "type": "array",
            "maxItems": 10,
            "items": {
                "type": "string",
                "minLength": 1,
                "maxLength": 500,
            },
        },
        "disclaimer": {
            "const": BRIEFING_DISCLAIMER,
        },
    },
    "required": [
        "executive_summary",
        "current_position",
        "top_priorities",
        "scheme_guidance",
        "risks",
        "questions_for_founder",
        "disclaimer",
    ],
}


class BriefingOutputValidationError(ValueError):
    pass


def _source_documents(
    snapshot: StartupAdvisorSnapshot,
    evidence_documents: list[dict[str, Any]] | None = None,
) -> dict[tuple[str, str], Any]:
    documents: dict[tuple[str, str], Any] = {
        (
            "profile",
            str(snapshot.startup_profile_id),
        ): snapshot.profile_snapshot,
    }

    if snapshot.readiness_assessment_id:
        documents[
            (
                "readiness",
                str(snapshot.readiness_assessment_id),
            )
        ] = snapshot.readiness_snapshot

    if snapshot.readiness_action_plan_id:
        documents[
            (
                "action_plan",
                str(snapshot.readiness_action_plan_id),
            )
        ] = snapshot.action_plan_snapshot

    if snapshot.recommendation_generation_run_id:
        documents[
            (
                "recommendation_generation",
                str(snapshot.recommendation_generation_run_id),
            )
        ] = snapshot.recommendation_generation_snapshot

    for recommendation in snapshot.recommendations_snapshot:
        if isinstance(recommendation, dict) and recommendation.get("id"):
            documents[
                (
                    "recommendation",
                    str(recommendation["id"]),
                )
            ] = recommendation

    for evidence in evidence_documents or []:
        if isinstance(evidence, dict) and evidence.get("id"):
            documents[
                (
                    "evidence_chunk",
                    str(evidence["id"]),
                )
            ] = evidence

    return documents


def _canonicalize_model_field_path(
    pointer: str,
    *,
    source_type: str,
) -> str:
    """Convert common model path notation to an RFC 6901 pointer."""
    candidate = pointer.strip()

    # /items[0].reason -> /items/0/reason
    candidate = re.sub(
        r"\[(\d+)\]",
        r"/\1",
        candidate,
    )
    candidate = re.sub(
        r"\.([A-Za-z_][A-Za-z0-9_]*)",
        r"/\1",
        candidate,
    )

    # /readiness/blocking_findings/0 -> /blocking_findings/0
    source_prefix = f"/{source_type}/"
    if candidate.startswith(source_prefix):
        candidate = "/" + candidate[len(source_prefix) :]

    # Handle plural array prefixes from the top-level payload structure 
    # that the LLM might incorrectly use
    if source_type == "recommendation":
        candidate = re.sub(r"^/recommendations?/\d+/", "/", candidate)
    elif source_type == "evidence_chunk":
        candidate = re.sub(r"^/retrieved_evidence/\d+/", "/", candidate)
        candidate = re.sub(r"^/evidence_chunks?/\d+/", "/", candidate)

    return candidate


def _resolve_json_pointer(document: Any, pointer: str) -> Any:
    if not pointer.startswith("/"):
        raise KeyError(pointer)

    current = document
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if token not in current:
                raise KeyError(pointer)
            current = current[token]
            continue
        if isinstance(current, list):
            if not token.isdigit():
                raise KeyError(pointer)
            index = int(token)
            if index >= len(current):
                raise KeyError(pointer)
            current = current[index]
            continue
        raise KeyError(pointer)

    return current


def _repair_one_based_boundary_pointer(
    document: Any,
    pointer: str,
) -> str | None:
    """Repair only an array index equal to the array length.

    Models sometimes count a final array item as N instead of the valid
    zero-based index N - 1. Exact in-range pointers remain unchanged, and
    indexes beyond the one-based boundary remain invalid.
    """
    if not pointer.startswith("/"):
        return None

    current = document
    raw_tokens = pointer[1:].split("/")
    repaired_tokens: list[str] = []
    repaired = False

    for raw_token in raw_tokens:
        token = raw_token.replace("~1", "/").replace("~0", "~")

        if isinstance(current, dict):
            if token not in current:
                return None
            current = current[token]
            repaired_tokens.append(raw_token)
            continue

        if isinstance(current, list):
            if not token.isdigit():
                return None

            index = int(token)
            if index < len(current):
                current = current[index]
                repaired_tokens.append(raw_token)
                continue

            if (
                not repaired
                and index > 0
                and index == len(current)
            ):
                repaired = True
                repaired_index = index - 1
                current = current[repaired_index]
                repaired_tokens.append(str(repaired_index))
                continue

            return None

        return None

    if not repaired:
        return None
    return "/" + "/".join(repaired_tokens)


def _iter_reference_groups(payload: dict[str, Any]):
    for item in payload["top_priorities"]:
        yield "top priority", item["source_references"]
    for item in payload["scheme_guidance"]:
        yield "scheme guidance", item["source_references"]
    for item in payload["risks"]:
        yield "risk", item["source_references"]


def validate_startup_advisor_briefing(
    *,
    payload: Any,
    source_snapshot: StartupAdvisorSnapshot,
    evidence_documents: list[dict[str, Any]] | None = None,
    require_evidence_citation: bool = False,
) -> dict[str, Any]:
    errors = sorted(
        Draft202012Validator(
            STARTUP_ADVISOR_BRIEFING_SCHEMA,
        ).iter_errors(payload),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        path = ".".join(str(item) for item in first.absolute_path)
        location = path or "<root>"
        raise BriefingOutputValidationError(
            f"LLM briefing output failed schema validation at {location}: {first.message}"
        )

    priorities = [item["priority"] for item in payload["top_priorities"]]
    expected_priorities = list(range(1, len(priorities) + 1))
    if priorities != expected_priorities:
        raise BriefingOutputValidationError(
            "LLM briefing priorities must be ordered and contiguous from 1."
        )

    documents = _source_documents(
        source_snapshot,
        evidence_documents=evidence_documents,
    )

    has_persisted_recommendations = any(
        source_type == "recommendation" for source_type, _source_id in documents
    )
    if payload["scheme_guidance"] and not has_persisted_recommendations:
        raise BriefingOutputValidationError(
            "Scheme guidance must be empty when the advisor "
            "snapshot contains no persisted recommendations."
        )

    for group_name, references in _iter_reference_groups(payload):
        for reference in references:
            source_key = (
                reference["source_type"],
                reference["source_id"],
            )
            document = documents.get(source_key)
            if document is None:
                raise BriefingOutputValidationError(
                    f"{group_name} cites an unavailable source: {source_key[0]} {source_key[1]}."
                )
            original_path = reference["field_path"]
            canonical_path = _canonicalize_model_field_path(
                original_path,
                source_type=reference["source_type"],
            )

            candidate_paths = [original_path]
            if canonical_path != original_path:
                candidate_paths.append(canonical_path)

            repaired_boundary_path = (
                _repair_one_based_boundary_pointer(
                    document,
                    canonical_path,
                )
            )
            if (
                repaired_boundary_path is not None
                and repaired_boundary_path not in candidate_paths
            ):
                candidate_paths.append(repaired_boundary_path)

            if reference["source_type"] == "profile" and not canonical_path.startswith(
                "/profile_data/"
            ):
                profile_data_path = f"/profile_data{canonical_path}"
                if profile_data_path not in candidate_paths:
                    candidate_paths.append(profile_data_path)

            for candidate_path in candidate_paths:
                try:
                    _resolve_json_pointer(
                        document,
                        candidate_path,
                    )
                except KeyError:
                    continue

                reference["field_path"] = candidate_path
                break
            else:
                reference["_invalid"] = True

    for _group_name, references in _iter_reference_groups(payload):
        references[:] = [ref for ref in references if not ref.pop("_invalid", False)]

    has_evidence_citation = any(
        reference["source_type"] == "evidence_chunk"
        for _group_name, references in _iter_reference_groups(payload)
        for reference in references
    )
    if require_evidence_citation and not has_evidence_citation:
        raise BriefingOutputValidationError(
            "At least one briefing item must cite a relevant "
            "retrieved evidence chunk."
        )

    return payload
