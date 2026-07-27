"""Tests for dynamic research query planner and router."""
from apps.research.services.query_planner import (
    extract_structured_idea,
    generate_search_queries,
)
from apps.research.services.search_router import decide_live_search


def test_decide_live_search():
    res1 = decide_live_search("Who are my current competitors and latest market trends?")
    assert res1.required is True
    assert "latest" in res1.reason or "competitors" in res1.reason


def test_query_planner():
    profile = {"startup_name": "HealthPulse", "stage": "idea", "sectors": ["Healthcare"]}
    question = "I want to build a smart health wristband for elderly people."

    idea = extract_structured_idea(profile, question)
    assert idea["product"] == "HealthPulse"
    assert idea["industry"] == "Healthcare"

    queries = generate_search_queries(idea, question)
    assert len(queries) >= 3
    assert any("HealthPulse" in q for q in queries)
