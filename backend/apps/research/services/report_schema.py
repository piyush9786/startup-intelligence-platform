"""Schemas for generated and persisted grounded research reports."""
from __future__ import annotations

LLM_RESEARCH_REPORT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "startup_summary",
        "historical_peers",
        "current_competitors",
        "recent_market_developments",
        "government_schemes",
        "risks",
        "market_gaps",
        "capital_scenarios",
        "recommended_next_actions",
        "sources",
        "confidence_score",
    ],
    "properties": {
        "startup_summary": {
            "type": "string",
            "minLength": 1,
        },
        "historical_peers": {
            "type": "array",
            "items": {"type": "string"},
        },
        "current_competitors": {
            "type": "array",
            "items": {"type": "string"},
        },
        "recent_market_developments": {
            "type": "array",
            "items": {"type": "string"},
        },
        "government_schemes": {
            "type": "array",
            "items": {"type": "string"},
        },
        "risks": {
            "type": "array",
            "items": {"type": "string"},
        },
        "market_gaps": {
            "type": "array",
            "items": {"type": "string"},
        },
        "capital_scenarios": {
            "type": "string",
            "minLength": 1,
        },
        "recommended_next_actions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "sources": {
            "type": "array",
            "items": {"type": "string"},
        },
        "confidence_score": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
        },
    },
}

RESEARCH_METADATA_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "live_search_status",
        "llm_status",
        "local_evidence_status",
        "vector_retrieval_status",
        "local_evidence_count",
        "vector_evidence_count",
        "live_evidence_count",
        "search_failure_count",
    ],
    "properties": {
        "live_search_status": {
            "type": "string",
            "enum": [
                "not_required",
                "available",
                "partial",
                "unavailable",
            ],
        },
        "llm_status": {
            "type": "string",
            "enum": ["generated", "fallback"],
        },
        "local_evidence_status": {
            "type": "string",
            "enum": ["available", "unavailable"],
        },
        "vector_retrieval_status": {
            "type": "string",
            "enum": [
                "disabled",
                "available",
                "empty",
                "unavailable",
            ],
        },
        "local_evidence_count": {
            "type": "integer",
            "minimum": 0,
        },
        "vector_evidence_count": {
            "type": "integer",
            "minimum": 0,
        },
        "live_evidence_count": {
            "type": "integer",
            "minimum": 0,
        },
        "search_failure_count": {
            "type": "integer",
            "minimum": 0,
        },
    },
}

FINAL_RESEARCH_REPORT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        *LLM_RESEARCH_REPORT_SCHEMA["required"],
        "research_metadata",
    ],
    "properties": {
        **LLM_RESEARCH_REPORT_SCHEMA["properties"],
        "research_metadata": RESEARCH_METADATA_SCHEMA,
    },
}

# Backward-compatible name for existing imports. The model only generates
# the LLM-owned portion; Python adds and validates research_metadata later.
RESEARCH_REPORT_SCHEMA = LLM_RESEARCH_REPORT_SCHEMA
