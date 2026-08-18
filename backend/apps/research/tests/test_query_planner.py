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

    combined = " ".join(queries).lower()

    # Search discovery should use the startup's actual market/problem
    # terms rather than depending on an unpublished startup name.
    assert "health" in combined
    assert "india" in combined


def test_query_planner_does_not_treat_question_grammar_as_industry():
    idea = extract_structured_idea(
        {},
        "What are current competitors for logistics software?",
    )

    assert idea["sub_industry"] == "logistics software"
    assert "are" not in idea["target_users"]
    assert idea["revenue_model"] == "unspecified"
