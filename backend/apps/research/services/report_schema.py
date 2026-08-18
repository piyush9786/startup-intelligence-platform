"""Schemas for generated and persisted grounded research reports."""
from __future__ import annotations

# ADVISER_DECISION_INTELLIGENCE_V1


def _string_list() -> dict:
    return {"type": "array", "items": {"type": "string"}}


def _success_case_list() -> dict:
    return {
        "type": "array",
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "company", "why_it_worked", "success_factors", "lesson",
                "relevance_score", "sources",
            ],
            "properties": {
                "company": {"type": "string"},
                "why_it_worked": {"type": "string"},
                "success_factors": _string_list(),
                "lesson": {"type": "string"},
                "relevance_score": {"type": "number", "minimum": 0, "maximum": 1},
                "sources": _string_list(),
            },
        },
    }


def _failure_case_list() -> dict:
    return {
        "type": "array",
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "company", "what_happened", "failure_reasons", "lesson",
                "relevance_score", "sources",
            ],
            "properties": {
                "company": {"type": "string"},
                "what_happened": {"type": "string"},
                "failure_reasons": _string_list(),
                "lesson": {"type": "string"},
                "relevance_score": {"type": "number", "minimum": 0, "maximum": 1},
                "sources": _string_list(),
            },
        },
    }


def _application_opportunity_list() -> dict:
    return {
        "type": "array",
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ["name", "category", "why_relevant", "next_step", "source"],
            "properties": {
                "name": {"type": "string"},
                "category": {
                    "type": "string",
                    "enum": [
                        "scheme", "grant", "loan", "incubator", "accelerator",
                        "investor", "partnership", "tender", "export", "research", "other",
                    ],
                },
                "why_relevant": {"type": "string"},
                "next_step": {"type": "string"},
                "source": {"type": "string"},
            },
        },
    }


def _strategic_option_list() -> dict:
    return {
        "type": "array",
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "name", "summary", "benefits", "risks", "investment_level",
                "speed_level", "founder_fit_score",
            ],
            "properties": {
                "name": {"type": "string"},
                "summary": {"type": "string"},
                "benefits": _string_list(),
                "risks": _string_list(),
                "investment_level": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "very_high", "unknown"],
                },
                "speed_level": {
                    "type": "string",
                    "enum": ["slow", "medium", "fast", "unknown"],
                },
                "founder_fit_score": {"type": "number", "minimum": 0, "maximum": 1},
            },
        },
    }


def _decision_comparison_list() -> dict:
    return {
        "type": "array",
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ["option", "score", "reasoning"],
            "properties": {
                "option": {"type": "string"},
                "score": {"type": "number", "minimum": 0, "maximum": 1},
                "reasoning": {"type": "string"},
            },
        },
    }


LEGACY_REQUIRED_FIELDS = [
    "startup_summary", "historical_peers", "current_competitors",
    "recent_market_developments", "government_schemes",
    "compliance_requirements", "funding_opportunities", "loan_options",
    "risks", "market_gaps", "capital_scenarios", "recommended_next_actions",
    "sources", "confidence_score",
]

ADVISER_FIELDS = [
    "benefits", "success_cases", "failure_cases", "application_opportunities",
    "major_challenges", "risk_mitigations", "strategic_options",
    "decision_comparison", "recommended_direction", "recommendation_reason",
    "conditions_that_change_decision", "immediate_actions", "thirty_day_plan",
    "sixty_day_plan", "ninety_day_plan",
]

LLM_RESEARCH_REPORT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": LEGACY_REQUIRED_FIELDS,
    "properties": {
        "startup_summary": {"type": "string", "minLength": 1},
        "benefits": _string_list(),
        "historical_peers": _string_list(),
        "current_competitors": _string_list(),
        "success_cases": _success_case_list(),
        "failure_cases": _failure_case_list(),
        "recent_market_developments": _string_list(),
        "government_schemes": _string_list(),
        "compliance_requirements": _string_list(),
        "funding_opportunities": _string_list(),
        "loan_options": _string_list(),
        "application_opportunities": _application_opportunity_list(),
        "major_challenges": _string_list(),
        "risks": _string_list(),
        "risk_mitigations": _string_list(),
        "market_gaps": _string_list(),
        "capital_scenarios": {"type": "string", "minLength": 1},
        "strategic_options": _strategic_option_list(),
        "decision_comparison": _decision_comparison_list(),
        "recommended_direction": {"type": "string"},
        "recommendation_reason": {"type": "string"},
        "conditions_that_change_decision": _string_list(),
        "recommended_next_actions": _string_list(),
        "immediate_actions": _string_list(),
        "thirty_day_plan": _string_list(),
        "sixty_day_plan": _string_list(),
        "ninety_day_plan": _string_list(),
        "sources": _string_list(),
        "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
    },
}

RESEARCH_METADATA_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "live_search_status", "llm_status", "local_evidence_status",
        "vector_retrieval_status", "local_evidence_count", "vector_evidence_count",
        "live_evidence_count", "search_failure_count", "prior_intelligence_count",
        "search_query_count",
    ],
    "properties": {
        "live_search_status": {
            "type": "string",
            "enum": ["not_required", "available", "partial", "unavailable"],
        },
        "llm_status": {"type": "string", "enum": ["generated", "fallback"]},
        "local_evidence_status": {"type": "string", "enum": ["available", "unavailable"]},
        "vector_retrieval_status": {
            "type": "string",
            "enum": ["disabled", "available", "empty", "unavailable"],
        },
        "local_evidence_count": {"type": "integer", "minimum": 0},
        "vector_evidence_count": {"type": "integer", "minimum": 0},
        "live_evidence_count": {"type": "integer", "minimum": 0},
        "search_failure_count": {"type": "integer", "minimum": 0},
        "prior_intelligence_count": {"type": "integer", "minimum": 0},
        "search_query_count": {"type": "integer", "minimum": 0},
    },
}

FINAL_RESEARCH_REPORT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        *LEGACY_REQUIRED_FIELDS,
        *ADVISER_FIELDS,
        "research_timestamp",
        "research_metadata",
    ],
    "properties": {
        **LLM_RESEARCH_REPORT_SCHEMA["properties"],
        "research_timestamp": {"type": "string"},
        "research_metadata": RESEARCH_METADATA_SCHEMA,
    },
}

RESEARCH_REPORT_SCHEMA = LLM_RESEARCH_REPORT_SCHEMA
