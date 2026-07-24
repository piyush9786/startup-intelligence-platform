# Documentation

Start with the repository-level
[Project Context](../PROJECT_CONTEXT.md).

It describes the current product state, architecture, invariants, validation
workflow, and immediate next milestone.

## Product direction

- [Roadmap](ROADMAP.md)
- [Infrastructure roadmap](../infrastructure/README.md)

## Architecture

- [System architecture](architecture/README.md)
- [Shared agent orchestration](architecture/SHARED_AGENT_ORCHESTRATION_V1.md)
- [Site-wide founder chatbot](architecture/SITE_WIDE_CHATBOT_V1.md)
- [Verified scheme prerequisite graph](architecture/SCHEME_PREREQUISITE_GRAPH_V1.md)

## Eligibility and recommendations

- [Deterministic eligibility engine](eligibility/ENGINE_V1.md)
- [Eligibility assessment API](eligibility/ASSESSMENT_API.md)
- [Verified rule revisions](review-operations/VERIFIED_RULE_REVISIONS.md)

## Startup readiness and advisor

- [Readiness engine](startups/READINESS_ENGINE_V1.md)
- [Consolidated deterministic starting plan](startups/STARTING_PLAN_V1.md)
- [Grounded open-source LLM advisor briefings](startups/GROUNDED_OPEN_SOURCE_LLM_ADVISOR_BRIEFINGS_V1.md)
- [Advisor briefing retrieval API](startups/STARTUP_ADVISOR_BRIEFING_RETRIEVAL_API_V1.md)

## Founder frontend

- [Founder dashboard shell](frontend/FOUNDER_DASHBOARD_SHELL_V1.md)
- [Founder dashboard motion and hierarchy](frontend/FOUNDER_DASHBOARD_MOTION_V1.md)
- [First-open onboarding tour](frontend/FIRST_OPEN_ONBOARDING_TOUR_V1.md)
- [Startup assessment wizard](frontend/STARTUP_ASSESSMENT_WIZARD_V1.md)
- [Founder advisor briefing workspace](frontend/FOUNDER_ADVISOR_BRIEFING_WORKSPACE_V1.md)
- [Founder advisor workspace hardening](frontend/FOUNDER_ADVISOR_WORKSPACE_HARDENING_V1.md)

## Documentation maintenance

After each major milestone:

1. update `PROJECT_CONTEXT.md`;
2. update the affected domain document;
3. update `docs/ROADMAP.md`;
4. update the root README when setup, architecture, or headline capabilities
   change;
5. verify all relative Markdown links.
