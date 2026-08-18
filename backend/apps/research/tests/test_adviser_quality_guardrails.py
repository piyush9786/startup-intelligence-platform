from apps.research.orchestration.steps import _research_fields_for_finding
from apps.research.services.decision_engine import normalize_adviser_report


def test_challenge_portal_is_not_a_business_risk():
    fields = _research_fields_for_finding(
        "Defence innovation funding",
        "Provides prototype funding through a dedicated challenge portal.",
    )
    assert "funding_opportunities" in fields
    assert "risks" not in fields


def test_action_plan_gets_safe_fallbacks_when_model_omits_periods():
    report = normalize_adviser_report(
        {
            "recommended_next_actions": ["Verify official eligibility."],
            "risks": ["Application window is uncertain."],
        }
    )
    assert report["thirty_day_plan"] == ["Verify official eligibility."]
    assert report["sixty_day_plan"]
    assert report["ninety_day_plan"]
    assert report["risk_mitigations"]
