"""
Orchestrates the Capital Planner engine and AI tradeoff explanation generation.
"""
from __future__ import annotations

import logging
from typing import Any

from apps.startups.models import CAPITAL_PLAN_VERSION, StartupCapitalPlan, StartupProfile
from apps.startups.services.llm_provider import (
    LLMProviderError,
    get_startup_advisor_llm_provider,
)

from .capital_planner_engine import (
    build_capital_scenarios,
    build_category_allocations,
    calculate_capital_metrics,
    calculate_sensitivity_matrix,
)

logger = logging.getLogger(__name__)

CAPITAL_EXPLANATION_PROMPT_VERSION = "capital-explanation-v1"

CAPITAL_EXPLANATION_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_summary": {
            "type": "string",
            "description": "Executive summary of the startup's runway and financial health.",
        },
        "key_risk_factors": {
            "type": "array",
            "items": {"type": "string"},
            "description": "2-4 key financial risk factors given the current burn.",
        },
        "scenario_tradeoffs": {
            "type": "string",
            "description": "Analysis comparing conservative vs. growth scenario tradeoffs.",
        },
        "actionable_recommendations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "3 concrete actions to extend runway or optimize burn.",
        },
    },
    "required": [
        "overall_summary",
        "key_risk_factors",
        "scenario_tradeoffs",
        "actionable_recommendations",
    ],
}


def _generate_capital_ai_explanation(
    profile: StartupProfile,
    metrics: dict[str, Any],
    scenarios: dict[str, Any],
    provider: Any | None = None,
) -> dict[str, Any]:
    if provider is None:
        provider = get_startup_advisor_llm_provider()

    system_message = (
        "You are an expert startup CFO and financial advisor assisting an Indian founder. "
        "Analyze the provided deterministic financial metrics and generate a clear, "
        "actionable tradeoff explanation. Ground your response strictly in the "
        "provided figures. Do not invent numbers or change calculated runway values."
    )

    user_message = (
        f"Startup Name: {profile.startup_name}\n"
        f"Stage: {profile.get_stage_display()}\n"
        f"Available Capital: ₹{metrics['available_capital']:,.2f}\n"
        f"Monthly Net Burn: ₹{metrics['net_burn']:,.2f}\n"
        f"Calculated Runway: {metrics['runway_months']} months ({metrics['runway_status']})\n"
        f"Conservative Runway: {scenarios['conservative']['runway_months']} months\n"
        f"Growth Runway: {scenarios['growth']['runway_months']} months\n\n"
        "Provide a grounded explanation of key risk factors, scenario tradeoffs, "
        "and runway extension recommendations."
    )

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]

    try:
        result = provider.generate(
            messages=messages,
            response_schema=CAPITAL_EXPLANATION_SCHEMA,
        )
        if isinstance(result.payload, dict):
            return result.payload
    except LLMProviderError as exc:
        logger.warning("LLM provider unavailable for capital planner explanation: %s", exc)

    # Fallback explanation if LLM is unavailable
    cons_m = scenarios["conservative"]["runway_months"]
    growth_m = scenarios["growth"]["runway_months"]
    return {
        "overall_summary": (
            f"Your current available capital provides {metrics['runway_months']} months of runway "
            f"at a net monthly burn of ₹{metrics['net_burn']:,.2f}."
        ),
        "key_risk_factors": [
            "Fixed costs represent a high baseline commitment before revenue scaling.",
            "Runway under 12 months requires immediate capital allocation or fundraising focus.",
        ],
        "scenario_tradeoffs": (
            f"The Conservative scenario extends runway to {cons_m} months, "
            f"whereas the Growth scenario reduces runway to {growth_m} months."
        ),
        "actionable_recommendations": [
            "Audit non-essential SaaS and recurring vendor subscriptions.",
            "Focus capital allocation on direct customer acquisition channels.",
            "Establish a minimum 15% contingency reserve in liquid accounts.",
        ],
    }


def _get_ml_runway(
    profile: StartupProfile,
    *,
    available_capital: float,
    monthly_revenue: float,
    fixed_costs: float,
    variable_costs: float,
) -> float | None:
    """Get ML-predicted runway from Random Forest; returns None if model unavailable."""
    try:
        from apps.ml_engine.services.models.random_forest_capital import predict_ml_runway
        return predict_ml_runway(
            profile,
            available_capital=available_capital,
            monthly_revenue=monthly_revenue,
            fixed_costs=fixed_costs,
            variable_costs=variable_costs,
        )
    except Exception:
        return None


def generate_startup_capital_plan(
    *,
    owner: Any,
    profile: StartupProfile,
    available_capital: Any,
    monthly_revenue: Any = 0,
    fixed_costs: Any,
    variable_costs: Any,
    provider: Any | None = None,
) -> StartupCapitalPlan:
    metrics = calculate_capital_metrics(
        available_capital=available_capital,
        monthly_revenue=monthly_revenue,
        fixed_costs=fixed_costs,
        variable_costs=variable_costs,
    )

    scenarios = build_capital_scenarios(metrics)
    allocations = build_category_allocations(
        available_capital=metrics["available_capital"],
        net_burn=metrics["net_burn"],
        stage=profile.stage,
    )
    sensitivity = calculate_sensitivity_matrix(metrics)

    # Enhance metrics with ML-predicted runway
    ml_runway = _get_ml_runway(
        profile,
        available_capital=metrics["available_capital"],
        monthly_revenue=metrics["monthly_revenue"],
        fixed_costs=metrics["fixed_costs"],
        variable_costs=metrics["variable_costs"],
    )
    if ml_runway is not None:
        metrics["ml_runway_months"] = ml_runway

    ai_explanation = _generate_capital_ai_explanation(
        profile=profile,
        metrics=metrics,
        scenarios=scenarios,
        provider=provider,
    )

    plan = StartupCapitalPlan.objects.create(
        owner=owner,
        startup_profile=profile,
        available_capital=metrics["available_capital"],
        monthly_revenue=metrics["monthly_revenue"],
        fixed_costs=metrics["fixed_costs"],
        variable_costs=metrics["variable_costs"],
        net_burn=metrics["net_burn"],
        runway_months=metrics["runway_months"],
        runway_status=metrics["runway_status"],
        scenarios=scenarios,
        allocations=allocations,
        sensitivity=sensitivity,
        ai_explanation=ai_explanation,
        plan_version=CAPITAL_PLAN_VERSION,
    )

    return plan
