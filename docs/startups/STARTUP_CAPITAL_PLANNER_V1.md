# AI Capital Planner Workspace — Phase 55

## Overview

The AI Capital Planner Workspace (`CapitalPlannerPage.jsx`) provides founders with a deterministic financial engine for modeling net monthly burn rate, runway months, and runway health status (*Healthy > 18m*, *Caution 6–18m*, *Critical < 6m*), along with multi-scenario projections (*Conservative*, *Balanced*, *Growth*), stage-based category capital allocations, burn sensitivity matrices, and CFO-grade AI tradeoff explanations.

Supported by a dedicated Django persistence model (`StartupCapitalPlan`), capital plans preserve complete snapshot provenance under schema version `startup-capital-plan-v1`.

---

## Key Capabilities

1. **Deterministic Financial Core**:
   - **Net Burn Calculation**: Gross monthly costs minus recurring revenues.
   - **Runway Months Projection**: Liquid capital divided by net monthly burn.
   - **Runway Health Status**: Automatically categorized as *Healthy* (> 18m), *Caution* (6–18m), or *Critical* (< 6m).
2. **Scenario Modeling**:
   - **Conservative**: 15% variable cost reduction to extend runway.
   - **Balanced Baseline**: Current operational trajectory.
   - **Growth Acceleration**: 25% cost expansion for 30% projected revenue growth.
3. **Category Capital Allocations**:
   - Recommended percentage and rupee allocations across Hiring (40%), Marketing (20%), Cloud & Software (15%), Legal & Compliance (10%), and Contingency Reserves (15%).
4. **Burn Sensitivity Matrix**:
   - Evaluates runway impact under cost shifts of -25%, -10%, 0%, +10%, +25%, and +50%.
5. **AI Tradeoff Analysis**:
   - Grounded natural language explanations generated via `OllamaStartupAdvisorProvider` highlighting executive summaries, key risk factors, and scenario tradeoffs.

---

## Technical Architecture

- **Backend Persistence**:
  - `StartupCapitalPlan` model in `apps.startups.models`.
  - Migration `0013_startup_capital_plan.py`.
  - Service: `capital_planner_engine.py` (calculation engine) & `capital_planner_service.py` (AI orchestration).
  - Endpoints: `GET /api/v1/startup-capital-plans/current/` & `POST /api/v1/startup-capital-plans/generate/`.
- **Frontend Workspace**:
  - `CapitalPlannerPage.jsx` with input controls, metric summary cards, scenario tabs, allocation progress bars, and CFO insights card.

---

## Verification & Validation

- 530 backend pytest tests passing.
- 188 frontend Vitest tests across 41 test files passing.
- Frontend production bundle build (`npm run build`) passing in 4.57s.
- Ruff linting, Django system checks, and zero migration drift.
