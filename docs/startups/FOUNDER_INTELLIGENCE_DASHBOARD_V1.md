# Founder Intelligence Dashboard — Phase 58

## Overview

The Founder Intelligence Dashboard provides a unified command-center view aggregating live metrics from every Phase 54–57 workspace in one place. All values are computed deterministically from persisted platform records — no LLM calls are made.

**API endpoint**: `GET /api/v1/startups/<profile_id>/intelligence/`

---

## Metric Panels

| Panel | Workspace Source | Key Metrics |
|---|---|---|
| **Readiness Score** | Readiness Engine | Score (0–100), Grade (A–F), Critical gaps |
| **Capital Runway** | Capital Planner | Runway months, Runway status, Net burn |
| **Execution & Milestones** | Milestones Engine | Total / Completed / In-progress / Blocked, completion % |
| **Startup Builder** | Startup Builder | Sections confirmed / drafted / total, completion % |
| **Scheme Matches** | Recommendation Engine | Matched / Eligible / Conditional / Pending |
| **Recent Activity** | Cross-workspace | Last 10 events merged from milestones, capital plans, builder confirmations, readiness |

---

## Readiness Grade Scale

| Score Range | Grade |
|---|---|
| ≥ 90 | A |
| ≥ 70 | B |
| ≥ 55 | C |
| ≥ 40 | D |
| < 40 | F |

---

## Weakest Workspace CTA

The API returns `weakest_workspace` — the slug of the workspace most needing attention. Priority logic:

1. No readiness assessment → `startup`
2. Critical runway (< 6 months) → `capital-planner`
3. No capital plan → `capital-planner`
4. Builder completion < 50% → `builder`
5. No milestones created → `milestones`
6. No scheme recommendations → `schemes`
7. Default → `roadmap`

---

## Recent Activity Feed

An ordered merge of events from:
- Completed milestones (newest `completed_at`)
- Capital plan saves (newest `created_at`)
- Builder sections confirmed (newest `confirmed_at`)
- Readiness assessments (newest `created_at`)

Capped at 10 events, sorted newest-first.

---

## Files

### Backend
- `apps/startups/startup_intelligence_views.py` — Aggregate view (`StartupIntelligenceView`)
- `apps/startups/startup_intelligence_serializers.py` — DRF serializers
- `apps/startups/tests/test_startup_intelligence_api.py` — 7 API tests
- `config/urls.py` — `api/v1/startups/<profile_id>/intelligence/` route

### Frontend
- `intelligenceApi.js` — `getFounderIntelligence(profileId)`
- `intelligenceApi.test.js` — 2 unit tests
- `FounderIntelligencePage.jsx` — Premium dashboard with metric cards, ring progress, bar charts, activity feed, CTA banner
- `FounderIntelligencePage.test.jsx` — 3 component tests
- `App.jsx` — `"intelligence"` sidebar nav entry + view routing
