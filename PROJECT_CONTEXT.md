# Startup Intelligence Platform — Project Context

Last updated: 24 July 2026

This is the primary orientation document for developers and coding agents
working on this repository. Update it after every major merged product or
architecture milestone.

## 1. Product mission

The Startup Intelligence Platform helps Indian startup founders understand:

- how ready their startup is;
- which verified schemes, loans, registrations, certifications, and benefits
  are relevant;
- why they are eligible, ineligible, or still missing information;
- what evidence must be supplied or reviewed;
- what action should be taken next.

The platform is designed around verified evidence and deterministic decisions.

Language models may retrieve, organize, and explain information, but they must
not become the authority for eligibility, ranking, funding amounts, application
deadlines, verification decisions, or prerequisite sequencing.

## 2. Current maturity

The current product is an advanced MVP and functional internal alpha.

Current repository baseline:

- eligibility engine: `rules-v5`;
- founder explanation contract: `eligibility-explanation-v2`;
- persisted onboarding contract: `founder-onboarding-v1`;
- bounded concierge contract: `founder-concierge-v1`;
- consolidated starting-plan contract: `startup-starting-plan-v1`;
- verified dependency-graph contract: `scheme-prerequisite-graph-v1`;
- dependency-aware funding-plan contract: `startup-funding-plan-v1`;
- ordered founder dashboard with accessible Motion transitions;
- empty-profile and returning-founder onboarding variants;
- resumable, dismissible, and non-repeating onboarding progress;
- shared agent-orchestration persistence foundation;
- owner-scoped and bounded `AgentSession` records;
- append-only agent messages, tool-call logs, and claim references;
- versioned, whitelisted tool registry with one narrowly scoped draft-write
  capability;
- authorization context and canonical output hashes on every tool call;
- initial `get_startup_profile` tool at version `v1`;
- public entry landing page, registration, login, and password recovery;
- protected application shell for unauthenticated vs authenticated access;
- structured My Startup experience across 9 domain sections with profile completeness and verification badges;
- AI startup document intake workspace with pitch deck extraction, confidence scoring, page-level provenance, conflict review, and founder confirmation;
- dynamic 8-step startup assessment wizard with profile prefilling, progress tracking, live step validation, and lock & submit confirmation modal;
- readiness score breakdown & action roadmap workspace with domain score cards, evidence provenance, 3-wave execution roadmap, and direct tool deep links;
- direct scheme matching engine & discovery explorer workspace with multi-facet filters (sector, stage, state, support type), ranked match scoring, and official portal launcher links;
- regulatory compliance & certification engine workspace with authority-wise grouping (DPIIT, FSSAI, CDSCO, ISO/BIS, MCA), requirement cards, and external dataset provenance;
- capital & loan support workspace with financing category filters (grants, debt, working capital), interest & collateral terms, and direct lender links;
- verified startup & reviewer claim governance workspace with status filters (pending, approved, rejected), evidence inspection, and immutable decision audit logs;
- AI startup builder workspace with problem definition, customer persona, interview planning, validation experiments, business model canvas, and pricing strategy;
- AI capital planner workspace with deterministic burn rate, runway months, scenario modeling (conservative, balanced, growth), category capital allocations, sensitivity analysis, and CFO AI tradeoff notes;
- execution & milestones engine workspace across 5 domain categories with dependency graph enforcement, completion evidence submission, and chronological progress update logs;
- universal AI copilot with workspace-aware context injection, per-workspace quick prompts, copilot_context session field, and workspace-specific help for milestones, capital-planner, builder, schemes, startup, and assessment workspaces;
- founder intelligence command-center dashboard aggregating live metrics from all workspaces (readiness, capital runway, milestones, builder progress, scheme matches, recent activity feed) with weakest-workspace focus navigation;
- 543 backend tests passing;
- 203 frontend tests passing;
- frontend production build passing;
- Ruff, Django checks, and migration checks passing.

The main founder workflow is operational:

    First-open founder onboarding
    → startup assessment
    → startup profile
    → deterministic readiness evaluation
    → readiness action plan
    → verified scheme eligibility assessment
    → deterministic recommendation ranking
    → consolidated deterministic starting plan
    → deterministic dependency-aware funding plan
    → manual verification for unresolved gates
    → reviewer decision
    → recommendation regeneration
    → founder-facing verified provenance
    → grounded advisor briefing

The orchestration foundation supports the site-wide chatbot and bounded
founder concierge. It does not provide an autonomous agent runtime.

## 3. Non-negotiable engineering principles

### Deterministic engines are authoritative

Readiness, eligibility, ranking, prerequisite ordering, and deadline handling
must remain deterministic and testable.

The LLM may explain a deterministic result. It must not replace that result.

### Verified data is separated from discovered data

Automatically discovered or extracted scheme information is non-authoritative
until it has passed the review and publication workflow.

Only verified canonical scheme versions and verified executable rules may drive
automatic eligibility and recommendations.

### Founder claims are not verified facts

A founder may submit a claim and supporting evidence.

The claim does not affect authoritative eligibility until an authorized
reviewer creates an effective approval decision.

### Consequential outputs are auditable

Important decisions must retain enough snapshots and provenance to explain:

- which startup profile was evaluated;
- which scheme version and rules were used;
- which source document supported the scheme;
- which reviewer-approved verification was used;
- which engine and explanation versions generated the result.

### Access is capability-based

Frontend visibility is not an authorization boundary.

Backend permissions are authoritative.

Reviewer access is granted by explicit reviewer, administrator, or superuser
capability. Django `is_staff` alone does not grant eligibility-review access.

### Private evidence stays private

Raw object-storage keys, reviewer identities, internal notes, and private
evidence contents must not be exposed to founders unless explicitly intended by
the API contract.

## 4. Current architecture

The system is a modular monolith with asynchronous workers.

### Frontend

- React 19;
- Vite;
- founder dashboard;
- persisted first-open onboarding tour;
- startup assessment wizard;
- scheme explorer and scheme detail views;
- readiness and action-roadmap views;
- consolidated starting-plan and dependency-aware funding-plan workspaces;
- recommendation results;
- founder verification-submission workflow;
- reviewer verification workspace;
- grounded founder-advisor briefing workspace.

### Backend

- Django;
- Django REST Framework;
- JWT and session authentication;
- drf-spectacular OpenAPI schema;
- PostgreSQL-backed domain models;
- persisted shared agent-orchestration foundation;
- append-only tool-call and claim audit records;
- authenticated persistent founder chatbot API;
- Celery workers and scheduled jobs.

### Data and infrastructure

| Component | Responsibility |
| --- | --- |
| PostgreSQL | Authoritative users, profiles, schemes, rules, assessments, decisions, recommendations, jobs, and snapshots |
| MinIO | Raw source documents and private founder eligibility evidence |
| Redis | Celery transport, result backend, caching, and temporary coordination |
| Qdrant | Derived document embeddings and evidence retrieval |
| Neo4j | Derived, rebuildable verified scheme-prerequisite graph projection |
| Ollama | Local embeddings and controlled open-source LLM generation |
| Mailpit | Local email capture |
| Docker Compose | Local development orchestration |

PostgreSQL remains authoritative.

Qdrant and Neo4j are derived stores and must not silently override relational
business records.

## 5. Django domain applications

The current installed domain apps are:

- `core` — health and platform status;
- `accounts` — users, roles, identity, and capabilities;
- `sources` — authoritative sources, source documents, and crawl runs;
- `documents` — extraction, chunking, and document processing;
- `discovery` — discovered URLs, crawl frontier, and quality assessment;
- `knowledge` — extracted candidates, review, and publication workflows;
- `schemes` — canonical schemes, versions, benefits, requirements, rules, verified prerequisites, reviewed unlock relationships, and the derived graph projection;
- `startups` — profiles, assessment drafts, persisted onboarding progress,
  readiness, action plans, consolidated starting plans, dependency-aware
  funding plans, and advisor briefings;
- `recommendations` — eligibility assessments, recommendations, generation
  runs, verification submissions, evidence, and decisions;
- `assistant` — bounded agent sessions, append-only messages, immutable
  tool-call logs, claim references, canonical hashing, and the whitelisted
  tool registry.

## 6. Deterministic readiness

The readiness engine evaluates a stored startup profile at an explicit date.

It returns:

- overall readiness status;
- total and category scores;
- critical blockers;
- recommended improvements;
- ordered findings and actions;
- a deterministic summary.

Persisted readiness assessments and action plans are generated around this pure
evaluation service.

## 7. Eligibility and recommendation system

The current engine version is `rules-v5`.

Every verified rule produces one of:

- `pass`;
- `fail`;
- `unknown`.

Overall assessment precedence is:

1. `application_closed`
2. `verification_required`
3. `ineligible`
4. `insufficient_information`
5. `eligible`

Recommendations are generated only from actionable eligible assessments.

They retain assessment, scheme-version, source, score, rule, explanation, and
verification-provenance snapshots.

The founder explanation schema is `eligibility-explanation-v2`.

## 8. Manual eligibility verification

The manual verification workflow is end to end:

1. A deterministic assessment identifies an unresolved manual gate.
2. The founder creates a structured submission.
3. The founder uploads private supporting evidence.
4. An authorized reviewer accesses the review queue.
5. Evidence is downloaded through an authenticated endpoint.
6. The reviewer creates an immutable approval or rejection.
7. Effective and expiry dates control whether an approval may be used.
8. An effective approval provides the rule-specific value to `rules-v5`.
9. Later rejection, supersession, or expiry prevents stale approval use.
10. Recommendation explanations and snapshots preserve safe provenance.

Concurrent first submissions are serialized by locking the stable
`StartupProfile` parent before reading and replacing the current submission.

Founder-facing provenance may include:

- a safe requirement label;
- the fact that reviewer-approved evidence was used;
- effective and expiry dates.

It must not render internal decision IDs, submission IDs, private evidence
locations, reviewer notes, or reviewer identity.

## 9. Current AI boundary

The existing founder advisor remains a controlled, grounded generation
workflow.

It uses:

- persisted startup, readiness, roadmap, and recommendation snapshots;
- Qdrant retrieval over eligible evidence chunks;
- source-level citations;
- a versioned output schema;
- local Ollama generation;
- persisted briefing and job history.

The shared orchestration foundation now adds:

- owner-scoped `AgentSession` persistence;
- one active session per founder, agent type, and startup scope;
- bounded founder turn counts;
- append-only `AgentMessage` records;
- immutable `AgentToolCallLog` records;
- canonical SHA-256 hashes over tool outputs;
- captured authorization context;
- structured `AgentClaimReference` records;
- a versioned, explicit tool registry;
- the read-only `get_startup_profile` tool;
- one explicitly allowlisted, draft-scoped concierge write capability.

The site-wide founder chatbot is implemented as a bounded deterministic
conversation layer over the shared orchestration foundation.

The bounded founder concierge guides founders through the authoritative
assessment draft and confirmed submission workflow. There is not a general LLM
turn runner or autonomous agent runtime.

The advisor and future agents must preserve deterministic results as
authoritative and must not invent eligibility, funding amounts, legal
conclusions, application deadlines, reviewer decisions, or prerequisite
ordering.

## 9.1 Site-wide founder chatbot

Phase 44 adds:

- a persistent founder-only chatbot launcher and responsive drawer;
- authenticated global and startup-scoped chatbot sessions;
- persisted conversation history;
- bounded founder turns and scoped API request throttling;
- deterministic platform-help and navigation responses;
- startup-profile explanations through `get_startup_profile@v1`;
- page-aware context that is not treated as authorization;
- claim references to successful tool-call logs and canonical output hashes;
- reviewer-workspace exclusion;
- focused backend, frontend, accessibility, and integration tests.

The chatbot remains read-only and does not replace deterministic domain
services or the grounded founder-advisor workflow.

See
[Site-wide founder chatbot](docs/architecture/SITE_WIDE_CHATBOT_V1.md).

## 9.2 Bounded concierge and consolidated starting plan

Phases 46 and 47 add:

- a nine-state `founder-concierge-v1` workflow;
- backend-provided state-specific assessment-field allowlists;
- audited draft updates through the existing serializers;
- explicit founder confirmation before submission;
- transactionally generated readiness, action-plan, eligibility,
  recommendation, and starting-plan records;
- a persisted `startup-starting-plan-v1` snapshot;
- idempotent plan generation, current retrieval, and history;
- source identifiers, snapshots, and engine-version provenance;
- a founder Starting plan workspace.

Starting-plan readiness actions retain readiness priority and scheme
opportunities retain recommendation rank. Dependency status remains
`not_evaluated`; the platform does not claim prerequisite ordering before the
verified graph and funding-plan phases.

See
[Consolidated deterministic starting plan](docs/startups/STARTING_PLAN_V1.md).

## 9.3 Verified scheme-prerequisite graph

Phase 48 adds the versioned `scheme-prerequisite-graph-v1` contract.

PostgreSQL stores the authoritative prerequisite concepts,
scheme-to-prerequisite relationships, unlock relationships, official source
evidence, and reviewer provenance. Extracted and imported relationships remain
non-authoritative until explicitly verified.

Verified unlocks reject self-dependencies and directed cycles during normal
model saves. The schema supports multiple predecessors per scheme.

A deterministic canonical snapshot is projected into Neo4j. Projection rebuilds
use a PostgreSQL advisory lock, retain persisted run audit records, and can be
checked against PostgreSQL by graph version, source hash, identifiers, counts,
and metadata.

Phase 48 does not reorder the consolidated starting plan. Dependency-aware
ordering remains Phase 49 scope.

See
[Verified scheme prerequisite graph](docs/architecture/SCHEME_PREREQUISITE_GRAPH_V1.md).

## 9.4 Deterministic dependency-aware funding plan

Phase 49 adds the versioned `startup-funding-plan-v1` contract.

The pure planner consumes normalized steps and dependency edges, validates
cycles and source values, and produces deterministic Kahn execution waves.
Hard dependencies block successors. Supporting dependencies are preserved but
remain non-blocking.

The source adapter includes only reviewed Phase 48 relationships, verified
scheme versions, persisted Phase 47 starting-plan items, verified application
windows, and strictly sourced processing-time metadata. PostgreSQL remains
authoritative; Neo4j remains derived.

`StartupFundingPlan` persists the canonical source snapshot, SHA-256 source
hash, immutable plan snapshot, exact planning date, counts, next-step
identifiers, history, and one current version per startup.

Founder-owned generate, current, history, and detail APIs reject browser-authored
topology. A dedicated Funding plan workspace displays execution waves,
dependencies, application status, deadlines, timing, and immutable provenance.

The LLM does not choose or alter funding-plan ordering.

See
[Deterministic dependency-aware funding plan](docs/startups/FUNDING_PLAN_V1.md).

## 10. Planned conversational and planning layer

The first-open onboarding, shared orchestration foundation, site chatbot,
bounded concierge, consolidated starting plan, verified prerequisite graph, and
dependency-aware funding plan are implemented.

The remaining agreed implementation order is:

1. founder progress tracking with verification-aware feedback.

Future conversational interfaces must execute only versioned, registered tools.

They must not receive unrestricted database access.

Conversational writes may update assessment drafts only through the registered
and explicitly allowlisted `assessment_draft_update` capability.

Profile submission must continue through the existing validation and
confirmation workflow.

## 11. Agent design rules

Startup-specific agent claims must be traceable to successful tool-call outputs.

The implemented foundation provides:

    get_startup_profile

Additional planned read-only tools include:

    get_readiness_assessment
    get_current_recommendations
    search_schemes
    get_scheme_detail
    get_action_roadmap

Every tool execution must:

- resolve through the explicit registry;
- have a version;
- validate the actor and session owner;
- enforce allowed agent types;
- preserve the session and startup scope;
- record input parameters;
- record authorization context;
- record status and duration;
- snapshot the output or safe failure;
- store a canonical output hash.

Unregistered, unauthorized, closed-session, and non-allowlisted write-capable
tool requests must be denied and logged.

Agent messages, tool-call logs, and claim references are append-only through
the model service boundary.

A draft-scoped field update is allowed only for the concierge, and it must:

- use existing serializers;
- record previous and new values;
- write only to `StartupAssessmentDraft`;
- require explicit confirmation before submission.

Regulatory, government-programme, tax, legal, eligibility, funding, and
deadline claims must come from verified platform data or grounded official
evidence, not unsupported model knowledge.

## 12. Repository map

```text
backend/
  apps/
    assistant/
  config/
  scripts/

frontend/
  src/

docs/
  architecture/
  eligibility/
  frontend/
  review-operations/
  startups/

infrastructure/
docker-compose.yml
Makefile
PROJECT_CONTEXT.md
README.md
```

## 13. Local development

Initial setup:

```bash
cp .env.example .env
docker compose build
docker compose up -d
docker compose exec -T backend python manage.py migrate
docker compose exec backend python manage.py seed_sources
docker compose exec backend python manage.py createsuperuser
```

Optional local model setup:

```bash
docker compose exec ollama ollama pull qwen3.5:9b
docker compose exec ollama ollama pull embeddinggemma
```

## 14. Required validation before a pull request

Backend:

```bash
docker compose exec -T backend pytest -q
docker compose exec -T backend ruff check .
docker compose exec -T backend python manage.py check
docker compose exec -T backend   python manage.py makemigrations --check --dry-run
```

Frontend:

```bash
docker compose exec -T frontend npm test
docker compose exec -T frontend npm run build
```

Repository:

```bash
git diff --check
git status -sb
```

Relevant focused tests should run before full suites.

## 15. Git workflow

Use one focused branch and pull request per milestone.

```text
main
→ focused feature/docs/fix branch
→ focused tests
→ full validation
→ commit
→ push
→ draft pull request
→ CI
→ ready for review
→ merge
→ synchronize main
→ remove feature branch
```

Do not commit directly to `main`.

Do not mix unrelated refactors into a milestone.

## 16. Immediate next milestone

The next milestone is the deterministic dependency-aware funding-plan engine.

Initial Phase 49 scope:

- consume only verified Phase 48 graph relationships;
- support multiple predecessors per plan step;
- order hard prerequisites before dependent opportunities;
- incorporate verified application windows;
- use sourced processing-time ranges;
- account for founder urgency and funding relevance;
- represent steps that may run in parallel;
- persist the generated plan and source snapshots;
- keep ordering algorithmic and testable.

The language model may explain the resulting plan but must not select or modify
its ordering.
