# Product and Engineering Roadmap

This roadmap records the agreed implementation order after verified eligibility
provenance v1 and the persisted first-open onboarding milestone.

It is directional rather than a promise of dates.

Each phase should be shipped as a focused and tested pull request.

## Completed foundation

The following major capabilities are operational:

- modular Django and React platform foundation;
- source collection, document extraction, and knowledge review;
- verified canonical scheme versions;
- deterministic startup-readiness assessment;
- deterministic eligibility and recommendation generation;
- persisted assessments, generation runs, and evidence snapshots;
- startup document autofill;
- Qdrant RAG and official evidence citations;
- grounded Ollama founder-advisor briefings;
- founder manual eligibility-verification workflow;
- reviewer verification workspace;
- concurrency-safe verification submissions;
- verified eligibility provenance in backend snapshots and founder UI;
- persisted first-open founder onboarding.

## Completed Phase 45: first-open onboarding tour

Purpose: improve the first founder experience without adding agent risk.

Implemented scope:

- owner-scoped `OnboardingProgress` persistence;
- `founder-onboarding-v1` versioning;
- empty-profile and returning-founder variants;
- active, dismissed, and completed states;
- resumable current-step persistence;
- no repeat or reopening after completion;
- direct handoff to the existing assessment wizard;
- founder-only frontend loading;
- reviewer-workspace exclusion;
- accessible modal semantics, progress reporting, keyboard focus containment,
  Escape dismissal, and responsive layout;
- focused backend API tests;
- frontend integration tests and production build validation.

See
[First-open onboarding tour](frontend/FIRST_OPEN_ONBOARDING_TOUR_V1.md).

## Remaining implementation order

### 1. Shared agent orchestration — Phase 43

Purpose: establish the safety and audit boundary once for every conversational
feature.

Scope:

- new `apps/assistant` Django application;
- `AgentSession`, `AgentMessage`, and immutable `AgentToolCallLog`;
- one active session per founder, startup profile, and agent type;
- whitelisted tool registry;
- authorization context on every tool call;
- tool version, status, duration, output snapshot, and output hash;
- structured claim-to-tool-call references;
- rate limits and bounded turn execution.

Start with read-only tools.

### 2. Site-wide chatbot — Phase 44

Purpose: provide product navigation, definitions, and profile-specific
explanations.

Scope:

- persistent dashboard widget;
- page-aware context;
- platform-help answers;
- startup-specific answers through deterministic tools;
- verified or grounded sourcing for regulatory and scheme facts;
- escalation to the existing advisor briefing for deep synthesis.

The chatbot must not directly modify authoritative profile data.

### 3. Concierge state machine — Phases 46 and 47

Purpose: guide a founder from an empty profile to a useful starting plan.

Scope:

- bounded explicit conversation states;
- LLM phrasing and structured answer interpretation only;
- draft-scoped assessment-field updates;
- confirmation and correction stage;
- existing serializers and submission services;
- deterministic readiness, roadmap, eligibility, and recommendation generation;
- consolidated ordered starting plan.

The Concierge must reuse `StartupAssessmentDraft`.

It must not create a second authoritative profile representation.

### 4. Scheme dependency graph — Phase 48

Purpose: represent prerequisites and unlock relationships with provenance.

Scope:

- verified prerequisite concepts;
- scheme-to-prerequisite edges;
- unlock relationships;
- source and review provenance for every graph edge;
- PostgreSQL canonical records with Neo4j projection;
- cycle validation;
- graph rebuild and consistency checks.

LLM-extracted edges must not become authoritative without review.

### 5. Funding plan engine — Phase 49

Purpose: produce an ordered, dependency-aware funding and readiness plan.

Ordering must be algorithmic and consider:

- hard prerequisite dependencies;
- verified application windows;
- sourced processing-time ranges;
- founder urgency;
- funding relevance;
- steps that may run in parallel.

Use a dependency table that supports multiple predecessors per step instead of a
single nullable `depends_on` field.

The LLM may narrate the generated plan but must not choose its ordering.

### 6. Progress feedback — Phase 50

Purpose: connect plan execution back to readiness and recommendations.

Use explicit states such as:

- `not_started`;
- `in_progress`;
- `founder_reported_complete`;
- `evidence_submitted`;
- `verified`.

Founder-reported completion must not automatically become a verified
eligibility fact.

## Parallel production-hardening track

Before public production use, complete:

- deployment environment and TLS;
- managed secrets;
- backup and restore drills;
- object-storage retention policy;
- malware scanning and stronger upload validation;
- observability, metrics, logs, and alerting;
- queue and API load testing;
- permission and penetration testing;
- disaster-recovery documentation;
- broader verified scheme coverage;
- end-to-end browser tests;
- operational reviewer audit history;
- user notifications.

## Phase completion rule

A phase is complete only when:

- its authorization boundary is defined;
- deterministic and LLM responsibilities are separated;
- persisted data has an ownership and mutability policy;
- focused and full tests pass;
- migrations are reviewed;
- API and founder-facing behavior are documented;
- CI passes;
- the project context and roadmap are updated.
