"""Tests for reusable adviser research memory."""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.research.models import (
    DecisionRecommendation,
    ResearchInsight,
    ResearchRequest,
    StartupResearchReport,
)
from apps.research.services.intelligence_memory import (
    get_prior_intelligence,
    persist_report_intelligence,
)
from apps.startups.models import StartupProfile

# ADVISER_DECISION_INTELLIGENCE_V1

User = get_user_model()


@pytest.mark.django_db
def test_report_is_materialized_into_reusable_intelligence():
    user = User.objects.create_user(username="memory-founder", password="password123")
    profile = StartupProfile.objects.create(
        owner=user,
        startup_name="Memory Startup",
        stage=StartupProfile.Stage.IDEA,
    )
    request = ResearchRequest.objects.create(
        startup_profile=profile,
        requested_by=user,
        question="Should we enter this market?",
        status=ResearchRequest.Status.SUCCEEDED,
    )
    report = StartupResearchReport.objects.create(
        startup_profile=profile,
        research_request=request,
        model_name="test-model",
        report={
            "benefits": ["Strong demand signal"],
            "current_competitors": ["Example competitor"],
            "success_cases": [],
            "failure_cases": [{
                "company": "Example Failure",
                "what_happened": "Expanded before validating demand.",
                "failure_reasons": ["Premature scaling"],
                "lesson": "Validate demand before large fixed investment.",
                "relevance_score": 0.8,
                "sources": [],
            }],
            "government_schemes": [],
            "funding_opportunities": [],
            "loan_options": [],
            "application_opportunities": [],
            "major_challenges": ["Customer acquisition"],
            "risks": ["High capital intensity"],
            "market_gaps": ["Underserved SME segment"],
            "strategic_options": [{"name": "Pilot first"}],
            "decision_comparison": [{"option": "Pilot first", "score": 0.85, "reasoning": "Lower irreversible risk"}],
            "recommended_direction": "Run a limited pilot before scaling.",
            "recommendation_reason": "It tests demand while preserving capital.",
            "conditions_that_change_decision": ["Signed long-term customer contract"],
            "immediate_actions": ["Interview 20 target customers"],
            "thirty_day_plan": ["Complete interviews"],
            "sixty_day_plan": ["Run pilot"],
            "ninety_day_plan": ["Review pilot economics"],
            "sources": [],
            "confidence_score": 0.82,
        },
    )

    persist_report_intelligence(report)

    assert ResearchInsight.objects.filter(startup_profile=profile).exists()
    assert ResearchInsight.objects.filter(
        startup_profile=profile,
        insight_type=ResearchInsight.InsightType.FAILURE_CASE,
    ).exists()
    decision = DecisionRecommendation.objects.get(source_report=report)
    assert decision.recommended_direction == "Run a limited pilot before scaling."
    assert get_prior_intelligence(profile)
