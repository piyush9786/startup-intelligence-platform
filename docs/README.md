# Documentation

Start with the repository-level [README](../README.md).

It describes the current product state, system architecture, 9-model ML ensemble, data engineering pipelines, validation workflow, and completed milestones.

## Product direction

- [Roadmap](ROADMAP.md)
- [Product Vision v2](PRODUCT_VISION_V2.md)
- [Infrastructure roadmap](../infrastructure/README.md)

## Architecture & Machine Learning

- [System architecture](architecture/README.md)
- [Shared agent orchestration](architecture/SHARED_AGENT_ORCHESTRATION_V1.md)
- [Site-wide founder chatbot](architecture/SITE_WIDE_CHATBOT_V1.md)
- [Verified scheme prerequisite graph](architecture/SCHEME_PREREQUISITE_GRAPH_V1.md)

## Eligibility, Machine Learning & Recommendations

- [Deterministic eligibility engine](eligibility/ENGINE_V1.md)
- [Eligibility assessment API](eligibility/ASSESSMENT_API.md)
- [Verified rule revisions](review-operations/VERIFIED_RULE_REVISIONS.md)

## Startup readiness and advisor

- [Readiness engine](startups/READINESS_ENGINE_V1.md)
- [Consolidated deterministic starting plan](startups/STARTING_PLAN_V1.md)
- [Deterministic dependency-aware funding plan](startups/FUNDING_PLAN_V1.md)
- [Grounded open-source LLM advisor briefings](startups/GROUNDED_OPEN_SOURCE_LLM_ADVISOR_BRIEFINGS_V1.md)
- [Advisor briefing retrieval API](startups/STARTUP_ADVISOR_BRIEFING_RETRIEVAL_API_V1.md)

## Founder frontend

- [Founder dashboard shell](frontend/FOUNDER_DASHBOARD_SHELL_V1.md)
- [Founder dashboard motion and hierarchy](frontend/FOUNDER_DASHBOARD_MOTION_V1.md)
- [First-open onboarding tour](frontend/FIRST_OPEN_ONBOARDING_TOUR_V1.md)
- [Startup assessment wizard](frontend/STARTUP_ASSESSMENT_WIZARD_V1.md)
- [Founder advisor briefing workspace](frontend/FOUNDER_ADVISOR_BRIEFING_WORKSPACE_V1.md)
- [Founder advisor workspace hardening](frontend/FOUNDER_ADVISOR_WORKSPACE_HARDENING_V1.md)
- [Multi-Language Support (i18n)](frontend/I18N_V1.md)

## Documentation maintenance

After each major milestone:

1. update affected domain documents;
2. update `docs/ROADMAP.md`;
3. update the root `README.md` when setup, architecture, ML models, or headline capabilities change;
4. verify all relative Markdown links.
