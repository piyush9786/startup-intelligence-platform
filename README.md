# Startup Intelligence Platform

A verified startup-support intelligence platform for readiness assessment,
scheme eligibility, recommendations, evidence verification, grounded guidance,
and deterministic dependency-aware funding planning.

The platform is currently an advanced MVP and functional internal alpha.

## Core principle

Deterministic engines decide. Verified evidence supports those decisions.

Language models retrieve and explain. They do not invent eligibility, funding
amounts, deadlines, reviewer decisions, or prerequisite ordering.

## Implemented capabilities

- persisted first-open founder onboarding with empty-profile and
  returning-founder variants;
- resumable, dismissible onboarding with no repeat after completion;
- interactive react-joyride website tour;
- shared agent-orchestration persistence foundation;
- bounded owner-scoped agent sessions;
- append-only messages, immutable tool-call logs, and claim references;
- versioned whitelisted read-only tool registry with authorization snapshots
  and canonical output hashes;
- persistent founder-only site-wide chatbot integrated with local Qwen 3:4b LLM
  via Ollama, featuring page-aware context and deterministic navigation;
- startup profile and assessment-draft workflow;
- document-assisted profile autofill;
- deterministic startup-readiness assessment;
- persisted readiness action plans;
- persisted, versioned consolidated starting plans with source provenance;
- persisted dependency-aware funding plans with verified prerequisites,
  deterministic execution waves, exact-source idempotency, and immutable
  history;
- verified canonical scheme catalog and versioning;
- verified prerequisite concepts and reviewed scheme dependency relationships;
- deterministic cycle validation and rebuildable Neo4j graph projection;
- executable deterministic eligibility engine (`rules-v5`);
- immutable eligibility assessments and recommendation runs;
- deterministic recommendation ranking;
- founder manual-verification submissions and private evidence uploads;
- reviewer queue, protected evidence access, and immutable decisions;
- effective and expiring reviewer approvals;
- founder-facing reviewer-approved evidence provenance;
- Qdrant-backed evidence retrieval;
- grounded Ollama founder-advisor briefings with robust validation handling
  for LLM hallucination and fallback citations;
- global multi-language (i18n) support across public and product views (English, Hindi, Marathi);
- founder and reviewer React workspaces;
- readiness-first responsive founder dashboard with accessible Motion
  transitions and premium modern UI/UX (glassmorphism, vibrant palettes);
- interactive user journey routing dialogue for new founders vs existing startups;
- AI Capital Planner UI with runway, burn, and deterministic scenario modeling.

## System architecture

```text
React / Vite (with i18n context)
      │
      ▼
Django REST Framework
      │
      ├── PostgreSQL — authoritative business data
      ├── Redis / Celery — asynchronous work
      ├── MinIO — raw documents and private evidence
      ├── Qdrant — derived embeddings and retrieval
      ├── Neo4j — derived verified dependency-graph projection
      └── Ollama — local embeddings and controlled generation
```

See [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) for the complete product,
architecture, safety, and implementation context.

## Documentation

- [Documentation index](docs/README.md)
- [Shared agent orchestration](docs/architecture/SHARED_AGENT_ORCHESTRATION_V1.md)
- [Site-wide founder chatbot](docs/architecture/SITE_WIDE_CHATBOT_V1.md)
- [Multi-Language Support (i18n)](docs/frontend/I18N_V1.md)
- [First-open onboarding tour](docs/frontend/FIRST_OPEN_ONBOARDING_TOUR_V1.md)
- [Consolidated starting plan](docs/startups/STARTING_PLAN_V1.md)
- [Dependency-aware funding plan](docs/startups/FUNDING_PLAN_V1.md)
- [Verified scheme prerequisite graph](docs/architecture/SCHEME_PREREQUISITE_GRAPH_V1.md)
- [Project roadmap](docs/ROADMAP.md)
- [Architecture](docs/architecture/README.md)
- [Eligibility engine](docs/eligibility/ENGINE_V1.md)
- [Infrastructure](infrastructure/README.md)

## Local setup

```bash
cp .env.example .env
docker compose build
docker compose up -d
docker compose exec -T backend python manage.py migrate
docker compose exec backend python manage.py seed_sources
docker compose exec backend python manage.py createsuperuser
```

Optional local Ollama models:

```bash
docker compose exec ollama ollama pull qwen3.5:9b
docker compose exec ollama ollama pull embeddinggemma
```

## Local URLs

- Web: <http://localhost:5173>
- API health: <http://localhost:8000/api/v1/health/>
- API status: <http://localhost:8000/api/v1/status/>
- API docs: <http://localhost:8000/api/docs/>
- Django admin: <http://localhost:8000/admin/>
- Qdrant: <http://localhost:6333/dashboard>
- Neo4j: <http://localhost:7474>
- MinIO: <http://localhost:9001>
- Mailpit: <http://localhost:8025>

## Validation

```bash
docker compose exec -T backend pytest -q
docker compose exec -T backend ruff check .
docker compose exec -T backend python manage.py check
docker compose exec -T backend   python manage.py makemigrations --check --dry-run

docker compose exec -T frontend npm test
docker compose exec -T frontend npm run build

git diff --check
```

## Next product phase

The next milestone is verification-aware founder progress feedback.

Phase 50 will connect execution of the persisted funding plan back to readiness
and recommendations through explicit states such as `not_started`,
`in_progress`, `founder_reported_complete`, `evidence_submitted`, and
`verified`.

Founder-reported completion will remain separate from reviewer-approved or
otherwise authoritative verification facts.
<!-- phase-46-founder-concierge:start -->
## Phase 46: Bounded founder concierge

Phase 46 adds the authenticated founder-only `founder-concierge-v1` workflow while preserving the startup assessment as the authoritative source of founder and startup inputs.

The concierge follows nine bounded states: `greeting`, `basic_info`, `location_legal`, `founder_details`, `funding_need`, `documents_check`, `confirm_profile`, `generating_plan`, and `plan_ready`.

The frontend reads the authoritative current state and renders only the backend-provided `allowed_fields`. Draft changes use the narrowly allowlisted and audited assessment-draft update capability. Every public transition includes `expected_state`, and browser clients never send `system_transition`.

At `confirm_profile`, the founder must explicitly confirm submission. The existing deterministic assessment submission service remains authoritative for readiness, roadmap, eligibility, and recommendation generation. Successful submission performs the internal `generating_plan` to `plan_ready` transition.

The founder concierge remains separate from the site-wide read-only founder chatbot. It does not calculate or invent readiness, eligibility, recommendations, amounts, deadlines, ordering, or verification results in the browser.

API endpoints:

- `GET /api/v1/assistant/concierge/current/`
- `POST /api/v1/assistant/concierge/current/updates/`
- `POST /api/v1/assistant/concierge/current/transitions/`

Validation completed with 20 frontend test files and 124 frontend tests, the 465-test backend suite, the production frontend build, Ruff, Django system checks, and migration drift checks. No database migration was required.
<!-- phase-46-founder-concierge:end -->

## Phase 47: Consolidated deterministic starting plan

Phase 47 adds the persisted `startup-starting-plan-v1` contract.

It transactionally composes the exact readiness assessment, readiness action
plan, and recommendation generation created by confirmed assessment
submission. Each plan retains source snapshots, identifiers, engine versions,
counts, normalized items, history, and one current version per startup.

Readiness actions preserve readiness priority and scheme opportunities preserve
recommendation rank. Every item explicitly reports that dependency ordering has
not been evaluated; verified prerequisite ordering remains reserved for Phases
48 and 49.

Founder APIs support idempotent generation, current retrieval, history, and
detail. The founder workspace adds a dedicated Starting plan view with source
provenance and direct roadmap and scheme-explorer actions.

See
[Consolidated deterministic starting plan](docs/startups/STARTING_PLAN_V1.md).

## Phase 49: Deterministic dependency-aware funding plan

Phase 49 adds the persisted `startup-funding-plan-v1` contract.

It converts the Phase 47 starting plan and reviewed Phase 48 prerequisite graph
into deterministic ordered steps and parallel execution waves. Hard
dependencies block successors; supporting relationships remain non-blocking
provenance.

Only verified graph relationships, verified scheme versions, verified
application windows, and strictly sourced processing-time metadata influence
the plan. PostgreSQL remains authoritative, while Neo4j remains a derived
projection.

Founder APIs support idempotent generation, current retrieval, immutable
history, and detail. The founder dashboard includes a dedicated Funding plan
workspace with dependency, deadline, timing, execution-wave, and provenance
information.

Language models may narrate a persisted plan but do not select its ordering.

See
[Deterministic dependency-aware funding plan](docs/startups/FUNDING_PLAN_V1.md).
