# Startup Intelligence Platform — Project Context

Last updated: 23 July 2026

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
- empty-profile and returning-founder onboarding variants;
- resumable, dismissible, and non-repeating onboarding progress;
- shared agent-orchestration persistence foundation;
- owner-scoped and bounded `AgentSession` records;
- append-only agent messages, tool-call logs, and claim references;
- versioned, whitelisted, read-only tool registry;
- authorization context and canonical output hashes on every tool call;
- initial `get_startup_profile` tool at version `v1`;
- full backend test suite passing;
- 105 frontend tests passing;
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
    → manual verification for unresolved gates
    → reviewer decision
    → recommendation regeneration
    → founder-facing verified provenance
    → grounded advisor briefing

The orchestration foundation is infrastructure for later conversational
interfaces. It does not yet provide a site-wide chatbot or autonomous agent
runtime.

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
| Neo4j | Ecosystem relationships and future scheme-prerequisite graph |
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
- `schemes` — canonical schemes, versions, benefits, requirements, and rules;
- `startups` — profiles, assessment drafts, persisted onboarding progress,
  readiness, action plans, and advisor briefings;
- `recommendations` — eligibility assessments, recommendations, generation
  runs, verification submissions, evidence, and decisions;
- `assistant` — bounded agent sessions, append-only messages, immutable
  tool-call logs, claim references, canonical hashing, and the whitelisted
  read-only tool registry.

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
- a Phase 43 prohibition on write-capable tools;
- the read-only `get_startup_profile` tool.

The site-wide founder chatbot is implemented as a bounded deterministic
conversation layer over the shared orchestration foundation.

There is not yet a general LLM turn runner or concierge workflow.

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

## 10. Planned conversational layer

The first-open founder onboarding tour and shared orchestration foundation are
implemented.

The remaining agreed implementation order is:

1. bounded concierge state machine;
2. consolidated deterministic starting plan;
3. verified scheme-prerequisite graph;
4. dependency-aware funding-plan engine and timeline;
5. founder progress tracking with verification-aware feedback.

Future conversational interfaces must execute only versioned, registered tools.

They must not receive unrestricted database access.

Conversational writes must update assessment drafts only and remain disabled
until a separately reviewed write-tool milestone.

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

Unregistered, unauthorized, closed-session, and write-capable tool requests
must be denied and logged.

Agent messages, tool-call logs, and claim references are append-only through
the model service boundary.

A draft-scoped field update may be allowed later, but it must:

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

The next milestone is the bounded concierge state machine.

Initial scope:

- guide a founder from an empty or incomplete profile to a useful starting
  plan;
- reuse the existing `StartupAssessmentDraft` representation;
- use explicit bounded conversation states;
- allow language-model phrasing and structured answer interpretation only;
- keep draft-field updates behind separately reviewed write tools;
- require confirmation and correction before assessment submission;
- submit through existing serializers and validation services;
- run deterministic readiness, roadmap, eligibility, and recommendation
  services after confirmed submission;
- preserve complete session, tool-call, and field-change audit records.

The concierge must not create a second authoritative startup-profile
representation, bypass assessment validation, directly modify submitted
profiles, or allow language models to choose eligibility, ranking,
recommendation, funding, deadline, or prerequisite decisions.
