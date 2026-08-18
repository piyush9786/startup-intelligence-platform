from apps.research.services.search_router import decide_live_search


def test_strategic_adviser_question_requires_live_search():
    decision = decide_live_search(
        "Recommend the best strategy for my startup over the next 90 days."
    )
    assert decision.required is True


def test_saved_profile_summary_can_remain_internal():
    decision = decide_live_search("Summarize my saved startup profile")
    assert decision.required is False
