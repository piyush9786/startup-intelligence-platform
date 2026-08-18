"""Compact alias contract for a task-specific StartupIntel SLM.

The SLM sees short aliases (REF_001, EVIDENCE_001, SCHEME_001).
Django remains responsible for database UUIDs, JSON pointers, URLs, and final
legacy-schema validation.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .briefing_schema import BRIEFING_DISCLAIMER


class SLMAliasContractError(ValueError):
    """Raised when compact SLM output cites an unavailable alias."""


def _expand_citations(
    aliases: list[str],
    *,
    reference_map: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    for alias in aliases:
        item = reference_map.get(alias)
        if item is None:
            raise SLMAliasContractError(
                f"Unknown citation alias: {alias}"
            )

        reference = {
            "source_type": item["source_type"],
            "source_id": item["source_id"],
            "field_path": item["field_path"],
        }
        key = (
            reference["source_type"],
            reference["source_id"],
            reference["field_path"],
        )
        if key not in seen:
            result.append(reference)
            seen.add(key)

    return result


def expand_compact_advisor_output(
    payload: dict[str, Any],
    *,
    reference_map: dict[str, dict[str, str]],
) -> dict[str, Any]:
    """Expand compact alias citations into the existing briefing schema."""
    result = deepcopy(payload)

    for item in result.get("top_priorities", []):
        aliases = item.pop("citations", [])
        item["source_references"] = _expand_citations(
            aliases,
            reference_map=reference_map,
        )

    for item in result.get("scheme_guidance", []):
        aliases = item.pop("citations", [])
        item["source_references"] = _expand_citations(
            aliases,
            reference_map=reference_map,
        )

    for item in result.get("risks", []):
        aliases = item.pop("citations", [])
        item["source_references"] = _expand_citations(
            aliases,
            reference_map=reference_map,
        )

    result["disclaimer"] = BRIEFING_DISCLAIMER
    return result


def compact_advisor_schema() -> dict[str, Any]:
    """Small JSON schema for model generation before alias expansion."""
    citation_array = {
        "type": "array",
        "maxItems": 6,
        "items": {
            "type": "string",
            "pattern": "^REF_[0-9]{3}$",
        },
    }

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "executive_summary": {
                "type": "string",
                "maxLength": 900,
            },
            "current_position": {
                "type": "string",
                "maxLength": 900,
            },
            "top_priorities": {
                "type": "array",
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "priority": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 3,
                        },
                        "title": {
                            "type": "string",
                            "maxLength": 180,
                        },
                        "reason": {
                            "type": "string",
                            "maxLength": 600,
                        },
                        "recommended_action": {
                            "type": "string",
                            "maxLength": 600,
                        },
                        "citations": citation_array,
                    },
                    "required": [
                        "priority",
                        "title",
                        "reason",
                        "recommended_action",
                        "citations",
                    ],
                },
            },
            "scheme_guidance": {
                "type": "array",
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "scheme_name": {
                            "type": "string",
                            "maxLength": 240,
                        },
                        "guidance": {
                            "type": "string",
                            "maxLength": 600,
                        },
                        "citations": citation_array,
                    },
                    "required": [
                        "scheme_name",
                        "guidance",
                        "citations",
                    ],
                },
            },
            "risks": {
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
                        "reason": {
                            "type": "string",
                            "maxLength": 600,
                        },
                        "mitigation": {
                            "type": "string",
                            "maxLength": 600,
                        },
                        "citations": citation_array,
                    },
                    "required": [
                        "title",
                        "reason",
                        "mitigation",
                        "citations",
                    ],
                },
            },
            "questions_for_founder": {
                "type": "array",
                "maxItems": 5,
                "items": {
                    "type": "string",
                    "maxLength": 300,
                },
            },
        },
        "required": [
            "executive_summary",
            "current_position",
            "top_priorities",
            "scheme_guidance",
            "risks",
            "questions_for_founder",
        ],
    }
