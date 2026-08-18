from apps.research.services.query_planner import (
    generate_search_queries,
)
from apps.research.services.research_intent import (
    COMPETITORS,
    detect_research_intents,
)

IDEA = {
    "product": "AegisSilicon",
    "industry": "DeepTech",
    "sub_industry": "semiconductor AI",
    "technology": [
        "AI",
        "semiconductors",
    ],
    "target_users": [
        "industrial enterprises",
    ],
    "geography": "Maharashtra",
}


def test_competitor_question_detects_only_competitors():
    intents = detect_research_intents(
        "who are my current competitors?"
    )

    assert intents == {COMPETITORS}


def test_competitor_queries_do_not_include_unrelated_topics():
    queries = generate_search_queries(
        IDEA,
        "who are my current competitors?",
    )

    assert queries
    assert len(queries) <= 6

    combined = " ".join(queries).lower()

    assert "competitor" in combined
    assert "government scheme" not in combined
    assert "grant" not in combined
    assert "funding" not in combined
    assert "loan" not in combined
    assert "regulatory" not in combined
    assert "shutdown" not in combined
    assert "failure" not in combined


def test_competitor_queries_use_market_terms():
    queries = generate_search_queries(
        IDEA,
        "who are my current competitors?",
    )

    combined = " ".join(queries).lower()

    assert "semiconductor" in combined
    assert "india" in combined


def test_multi_intent_question_keeps_requested_topics():
    queries = generate_search_queries(
        IDEA,
        (
            "show my competitors and current market trends"
        ),
    )

    combined = " ".join(queries).lower()

    assert "competitor" in combined
    assert "market" in combined
    assert "government scheme" not in combined
    assert "regulatory" not in combined
