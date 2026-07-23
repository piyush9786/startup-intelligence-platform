# Startup Intelligence Platform

A verified startup-support intelligence platform for readiness assessment,
scheme eligibility, recommendations, evidence verification, grounded guidance,
and future dependency-aware funding planning.

The platform is currently an advanced MVP and functional internal alpha.

## Core principle

Deterministic engines decide. Verified evidence supports those decisions.

Language models retrieve and explain. They do not invent eligibility, funding
amounts, deadlines, reviewer decisions, or prerequisite ordering.

## Implemented capabilities

- persisted first-open founder onboarding with empty-profile and
  returning-founder variants;
- resumable, dismissible onboarding with no repeat after completion;
- shared agent-orchestration persistence foundation;
- bounded owner-scoped agent sessions;
- append-only messages, immutable tool-call logs, and claim references;
- versioned whitelisted read-only tool registry with authorization snapshots
  and canonical output hashes;
- persistent founder-only site-wide chatbot with bounded sessions, page-aware
  context, deterministic navigation, and grounded claim provenance;
- startup profile and assessment-draft workflow;
- document-assisted profile autofill;
- deterministic startup-readiness assessment;
- persisted readiness action plans;
- verified canonical scheme catalog and versioning;
- executable deterministic eligibility engine (`rules-v5`);
- immutable eligibility assessments and recommendation runs;
- deterministic recommendation ranking;
- founder manual-verification submissions and private evidence uploads;
- reviewer queue, protected evidence access, and immutable decisions;
- effective and expiring reviewer approvals;
- founder-facing reviewer-approved evidence provenance;
- Qdrant-backed evidence retrieval;
- grounded Ollama founder-advisor briefings with citations;
- founder and reviewer React workspaces.

## System architecture

```text
React / Vite
      │
      ▼
Django REST Framework
      │
      ├── PostgreSQL — authoritative business data
      ├── Redis / Celery — asynchronous work
      ├── MinIO — raw documents and private evidence
      ├── Qdrant — derived embeddings and retrieval
      ├── Neo4j — relationships and future dependency graph
      └── Ollama — local embeddings and controlled generation
```

See [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) for the complete product,
architecture, safety, and implementation context.

## Documentation

- [Documentation index](docs/README.md)
- [Shared agent orchestration](docs/architecture/SHARED_AGENT_ORCHESTRATION_V1.md)
- [Site-wide founder chatbot](docs/architecture/SITE_WIDE_CHATBOT_V1.md)
- [First-open onboarding tour](docs/frontend/FIRST_OPEN_ONBOARDING_TOUR_V1.md)
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

The next milestone is the bounded concierge state machine.

It will guide founders through the existing assessment-draft workflow using
explicit conversation states, confirmation, existing serializers, and complete
audit records.

Language models may phrase questions and interpret structured answers, but
deterministic services remain authoritative and profile submission must
continue through the existing validation workflow.

It will be followed by the consolidated deterministic starting plan, verified
scheme-dependency graph, and dependency-aware funding planning.
