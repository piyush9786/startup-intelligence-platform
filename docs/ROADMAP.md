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
- persisted first-open founder onboarding;
- shared agent-orchestration persistence and audit foundation;
- persistent site-wide founder chatbot.
- bounded founder concierge state machine;
- persisted consolidated deterministic starting plan.

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

## Completed Phase 44: site-wide founder chatbot

Purpose: provide persistent product navigation, workspace definitions, and
startup-profile-aware explanations without weakening the deterministic trust
boundary.

Implemented scope:

- founder-only persistent launcher and responsive drawer;
- authenticated global and startup-scoped chatbot sessions;
- complete persisted conversation history;
- page-aware context treated only as convenience context;
- deterministic platform-help and navigation responses;
- startup-profile explanations through the registered
  `get_startup_profile@v1` tool;
- claim references to successful tool calls and canonical output hashes;
- bounded 20-turn founder sessions;
- scoped request throttling through `assistant_chat_turn`;
- ownership enforcement and non-disclosure of other founders' profiles;
- reviewer-workspace exclusion;
- focused API, frontend, accessibility, and integration tests;
- successful full backend and frontend validation.

The chatbot remains read-only.

It does not modify startup profiles, assessment drafts, readiness findings,
eligibility results, recommendations, verification decisions, deadlines,
funding amounts, or prerequisite ordering.

See
[Site-wide founder chatbot](architecture/SITE_WIDE_CHATBOT_V1.md).

## Completed conversational foundation

## Completed Phase 43: shared agent orchestration

Purpose: establish the safety, ownership, persistence, and audit boundary once
for future conversational features.

Implemented scope:

- new `apps/assistant` Django application;
- owner-scoped `AgentSession`;
- one active session per founder, agent type, and startup scope;
- bounded founder turn counts;
- append-only `AgentMessage`;
- immutable `AgentToolCallLog`;
- structured `AgentClaimReference`;
- canonical JSON normalization and SHA-256 output hashing;
- captured authorization context;
- versioned whitelisted tool registry;
- explicit denial and logging of unregistered tools;
- explicit denial and logging of unauthorized actors;
- explicit denial of write-capable tools during Phase 43;
- initial read-only `get_startup_profile` tool;
- focused service, ownership, integrity, and audit tests.

The foundation does not yet add an LLM turn runner, public chatbot API, or
frontend chatbot.

See
[Shared agent orchestration](architecture/SHARED_AGENT_ORCHESTRATION_V1.md).

## Remaining implementation order

### 1. Scheme dependency graph — Phase 48

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

### 2. Funding plan engine — Phase 49

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

### 3. Progress feedback — Phase 50

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

<!-- phase-46-roadmap:start -->
## Phase 46 — Bounded founder concierge state machine

**Status: Completed**

- Added the versioned `founder-concierge-v1` nine-state workflow.
- Added authenticated founder-only current-state, bounded-update, and expected-state transition APIs.
- Added one narrowly allowlisted and audited assessment-draft write capability; unrelated write tools remain disabled.
- Required explicit founder confirmation before deterministic assessment submission.
- Added the internal successful-submission bridge from `generating_plan` to `plan_ready`.
- Added the responsive founder concierge frontend while keeping the site-wide chatbot separate and read-only.
- Preserved deterministic readiness, eligibility, recommendation, amount, deadline, ordering, and verification authority outside the browser.
- Added focused backend and frontend regression coverage.
- Validated 124 frontend tests, the 465-test backend suite, the frontend production build, Ruff, Django checks, and zero migration drift.
<!-- phase-46-roadmap:end -->

## Phase 47 — Consolidated deterministic starting plan

**Status: Completed**

- Added the persisted, versioned `startup-starting-plan-v1` contract.
- Composed exact readiness, action-plan, and recommendation-run sources without
  introducing a second decision engine.
- Preserved profile, source, result, engine-version, and recommendation
  snapshots.
- Added idempotent generation, one current plan per startup, and immutable
  historical source references.
- Added authenticated current, history, detail, and generate APIs with owner
  isolation and raw-payload rejection.
- Integrated plan creation into confirmed assessment submission and concierge
  completion in the existing transaction.
- Added a dedicated founder Starting plan workspace with provenance and
  responsive grouped actions.
- Explicitly left prerequisite dependency status as `not_evaluated` until
  Phases 48 and 49.
- Added focused backend, frontend, authorization, integration, and regression
  coverage.
- Validated 473 backend tests, 127 frontend tests, the frontend production
  build, Ruff, Django checks, and zero migration drift.

See
[Consolidated deterministic starting plan](startups/STARTING_PLAN_V1.md).
