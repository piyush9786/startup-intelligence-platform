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
- direct onboarding handoff to the existing startup assessment wizard;
- full backend test suite passing;
- 105 frontend tests passing;
- frontend production build passing;
- Ruff, Django checks, migration checks, and CI validation commands passing.

The main founder workflow is operational:

```text
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
```

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
  runs, verification submissions, evidence, and decisions.

The planned `assistant` application has not been implemented yet.

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

The existing founder advisor is a controlled, grounded generation workflow.

It uses:

- persisted startup, readiness, roadmap, and recommendation snapshots;
- Qdrant retrieval over eligible evidence chunks;
- source-level citations;
- a versioned output schema;
- local Ollama generation;
- persisted briefing and job history.

The system is not yet a general multi-turn agent platform.

The advisor must preserve deterministic results as authoritative and must not
invent eligibility, funding amounts, legal conclusions, or application
deadlines.

## 10. Planned conversational layer

The first-open founder onboarding tour is now implemented as a deterministic,
persisted product workflow. It does not use an autonomous agent and does not
alter readiness, eligibility, recommendation, or verification decisions.

The next product expansion introduces conversation as a controlled interface
over the existing platform.

The remaining agreed implementation order is:

1. shared agent orchestration and whitelisted tool registry;
2. site-wide chatbot;
3. bounded concierge state machine;
4. consolidated deterministic starting plan;
5. verified scheme-prerequisite graph;
6. dependency-aware funding-plan engine and timeline;
7. founder progress tracking with verification-aware feedback.

Agents will use logged, whitelisted tools.

They will not receive unrestricted database access.

Conversational writes must update assessment drafts only.

Profile submission must continue through the existing validation and
confirmation workflow.

## 11. Agent design rules

Future agent responses that make startup-specific claims must be traceable to
tool-call outputs.

The planned tool boundary includes read-mostly operations such as:

```text
get_startup_profile
get_readiness_assessment
get_current_recommendations
search_schemes
get_scheme_detail
get_action_roadmap
```

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

The next milestone is shared agent orchestration and a whitelisted tool
registry.

Initial scope:

- create the `apps/assistant` Django application;
- persist `AgentSession`, `AgentMessage`, and immutable tool-call records;
- establish an authorization context for every tool invocation;
- register versioned, whitelisted tools rather than exposing unrestricted
  database access;
- begin with read-only tools over startup profiles, readiness, recommendations,
  schemes, roadmaps, and persisted evidence;
- retain tool inputs, outputs, status, duration, version, and output hashes;
- provide claim-to-tool-call traceability for startup-specific responses;
- add rate limits and bounded turn execution.

This milestone must not add unrestricted profile writes or allow an LLM to
override deterministic readiness, eligibility, ranking, verification, funding
amount, deadline, or sequencing decisions.
