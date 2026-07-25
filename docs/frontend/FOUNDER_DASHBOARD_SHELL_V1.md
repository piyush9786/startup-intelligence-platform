# Founder Dashboard Shell & React Router Architecture (v1)

## Overview

The **Founder Dashboard Shell** (`AppShell.jsx`) provides the primary authenticated layout container for the Startup Intelligence Platform. It manages workspace state, multi-tenant startup profile selection, navigation layout, topbar search, and deep-linking via **React Router v7** and **TanStack Query v5**.

---

## 🧭 URL Route Mapping

The dashboard shell replaces legacy inline state machines (`activeView`) with clean, shareable browser URLs:

| Route Path | Component / Page | Purpose |
|---|---|---|
| `/` | `Navigate to=/dashboard` | Root redirect |
| `/dashboard` | `DashboardHome` | Overview & key startup metrics |
| `/startup` | `MyStartupPage` | Comprehensive startup profile & attributes |
| `/builder` | `StartupBuilderPage` | AI Startup Builder & Master Consultant |
| `/capital-planner` | `CapitalPlannerPage` | Capital runway planner & RF forecasting |
| `/tracker` | `ApplicationTrackerPage` | Scheme application tracking & status |
| `/roadmap` | `ActionRoadmapPage` | Actionable readiness roadmap & milestones |
| `/schemes` | `SchemeExplorerPage` | Scheme discovery catalog & filterable search |
| `/schemes/:schemeId` | `SchemeDetailPage` | Full scheme detail, rules, & eligibility breakdown |
| `/requirements` | `RequirementsPage` | External certification & compliance requirements |
| `/funding` | `FundingPage` | External capital support & investor programs |
| `/advisor` | `FounderIntelligencePage` | Grounded open-source LLM advisor briefings |
| `/intelligence` | `FounderConcierge` | Interactive AI concierge & workspace assistant |
| `/reviewer-verifications` | `ReviewerVerificationWorkspace` | Admin/Reviewer evidence review queue |
| `/onboarding` | `AssessmentWizard` | First-time founder onboarding wizard |

---

## 🔒 Shared Data Context

All routes inside `<Workspace />` inherit the shared workspace context via React Router's `<Outlet context={...} />`:
- `currentUser`: Authenticated user model & role.
- `selectedProfile`: Currently selected `StartupProfile`.
- `schemes`: Loaded scheme catalog with verification statuses.
- `currentBriefing`: Active grounded LLM briefing.
- `metrics`: Computed dashboard overview counters.
- `handleRequestError`: Centralized 401 handling & error formatting.

---

## 🧪 Verification

- **Build Check**: `npm run build` generates production bundle into `build/`.
- **Router Test Suite**: `App.test.jsx` & `AppShell.test.jsx` verified with Vitest.
