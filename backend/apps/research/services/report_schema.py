"""JSON schema for grounded research-report generation."""
from __future__ import annotations

RESEARCH_REPORT_SCHEMA = {
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
