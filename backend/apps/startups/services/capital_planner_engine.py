"""
Pure deterministic calculation engine for the AI Capital Planner.

Calculates:
- Net Burn Rate & Runway Months
- Runway Health Status (healthy > 18m, caution 6-18m, critical < 6m)
- 3 Scenario Projections (Conservative, Balanced, Growth)
- Recommended Category Allocations (Hiring, Marketing, Cloud, Legal, Contingency)
- Sensitivity Matrix (+/- 10%, 25%, 50% revenue & cost shifts)
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any


def _to_decimal(val: Any) -> Decimal:
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val or 0))
    except Exception:
        return Decimal(0)


def calculate_capital_metrics(
    available_capital: Any,
    monthly_revenue: Any,
    fixed_costs: Any,
    variable_costs: Any,
) -> dict[str, Any]:
    cap = max(Decimal(0), _to_decimal(available_capital))
    rev = max(Decimal(0), _to_decimal(monthly_revenue))
    fixed = max(Decimal(0), _to_decimal(fixed_costs))
    variable = max(Decimal(0), _to_decimal(variable_costs))

    total_gross_costs = fixed + variable
    net_burn = total_gross_costs - rev

    if net_burn <= Decimal(0):
        # Default infinite or default 99.0 for zero net burn
        runway_months = Decimal("99.0")
        status = "healthy"
    else:
        runway_raw = cap / net_burn
        runway_months = runway_raw.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        if runway_months < Decimal("6.0"):
            status = "critical"
        elif runway_months <= Decimal("18.0"):
            status = "caution"
        else:
            status = "healthy"

    return {
        "available_capital": float(cap),
        "monthly_revenue": float(rev),
        "fixed_costs": float(fixed),
        "variable_costs": float(variable),
        "total_gross_costs": float(total_gross_costs),
        "net_burn": float(net_burn),
        "runway_months": float(runway_months),
        "runway_status": status,
    }


def build_capital_scenarios(metrics: dict[str, Any]) -> dict[str, Any]:
    cap = Decimal(str(metrics["available_capital"]))
    rev = Decimal(str(metrics["monthly_revenue"]))
    fixed = Decimal(str(metrics["fixed_costs"]))
    var = Decimal(str(metrics["variable_costs"]))

    # Scenario 1: Conservative (Cost reduction by 15%, conservative revenue growth +0%)
    cons_fixed = fixed * Decimal("0.85")
    cons_var = var * Decimal("0.85")
    cons_net_burn = max(Decimal(0), (cons_fixed + cons_var) - rev)
    cons_runway = (
        float((cap / cons_net_burn).quantize(Decimal("0.1")))
        if cons_net_burn > 0
        else 99.0
    )

    # Scenario 2: Balanced (Current baseline)
    bal_net_burn = max(Decimal(0), (fixed + var) - rev)
    bal_runway = metrics["runway_months"]

    # Scenario 3: Growth (Expansion investment: costs +25%, revenue +30%)
    growth_fixed = fixed * Decimal("1.25")
    growth_var = var * Decimal("1.25")
    growth_rev = rev * Decimal("1.30")
    growth_net_burn = max(Decimal(0), (growth_fixed + growth_var) - growth_rev)
    growth_runway = (
        float((cap / growth_net_burn).quantize(Decimal("0.1")))
        if growth_net_burn > 0
        else 99.0
    )

    return {
        "conservative": {
            "name": "Conservative",
            "description": "Trim non-essential variable costs by 15% to extend runway.",
            "monthly_burn": float(cons_net_burn),
            "runway_months": cons_runway,
            "cost_change_pct": -15,
        },
        "balanced": {
            "name": "Balanced Baseline",
            "description": "Maintain existing operational budget and current burn trajectory.",
            "monthly_burn": float(bal_net_burn),
            "runway_months": bal_runway,
            "cost_change_pct": 0,
        },
        "growth": {
            "name": "Growth Acceleration",
            "description": "Increase team and marketing spend by 25% expecting 30% revenue uplift.",
            "monthly_burn": float(growth_net_burn),
            "runway_months": growth_runway,
            "cost_change_pct": 25,
        },
    }


def build_category_allocations(
    available_capital: float,
    net_burn: float,
    stage: str = "mvp",
) -> dict[str, Any]:
    """
    Produce stage-appropriate recommended capital allocations.
    """
    total = max(float(available_capital), 1.0)

    # Standard early-stage allocation percentages
    pcts = {
        "hiring": 0.40,
        "marketing": 0.20,
        "cloud_software": 0.15,
        "legal_compliance": 0.10,
        "contingency": 0.15,
    }

    allocations = {}
    for cat, pct in pcts.items():
        amount = round(total * pct, 2)
        allocations[cat] = {
            "percentage": int(pct * 100),
            "amount": amount,
        }

    return allocations


def calculate_sensitivity_matrix(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    cap = Decimal(str(metrics["available_capital"]))
    rev = Decimal(str(metrics["monthly_revenue"]))
    gross_costs = Decimal(str(metrics["total_gross_costs"]))

    shifts = [-25, -10, 0, 10, 25, 50]
    matrix = []

    for shift in shifts:
        mult = Decimal(1) + (Decimal(shift) / Decimal(100))
        shifted_costs = gross_costs * mult
        shifted_net_burn = shifted_costs - rev

        if shifted_net_burn <= 0:
            runway = 99.0
        else:
            runway = float((cap / shifted_net_burn).quantize(Decimal("0.1")))

        matrix.append({
            "cost_shift_pct": shift,
            "monthly_net_burn": float(max(Decimal(0), shifted_net_burn)),
            "runway_months": runway,
        })

    return matrix
