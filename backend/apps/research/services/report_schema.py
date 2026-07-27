"""Schemas for generated and persisted grounded research reports."""
from __future__ import annotations


def _string_list() -> dict:
    return {
        "type": "array",
        "items": {"type": "string"},
    }


LLM_RESEARCH_REPORT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "startup_summary",
        "historical_peers",
        "current_competitors",
        "recent_market_developments",
        "government_schemes",
        "compliance_requirements",
        "funding_opportunities",
        "loan_options",
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
        "historical_peers": _string_list(),
        "current_competitors": _string_list(),
        "recent_market_developments": _string_list(),
        "government_schemes": _string_list(),
        "compliance_requirements": _string_list(),
        "funding_opportunities": _string_list(),
        "loan_options": _string_list(),
        "risks": _string_list(),
        "market_gaps": _string_list(),
        "capital_scenarios": {
            "type": "string",
            "minLength": 1,
        },
        "recommended_next_actions": _string_list(),
        "sources": _string_list(),
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

RESEARCH_REPORT_SCHEMA = LLM_RESEARCH_REPORT_SCHEMA
