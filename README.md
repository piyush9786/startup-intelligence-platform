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

## System architecture & Domain boundaries

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

### Domain Boundaries
- **Frontend**: React and Vite application implementing multi-language (i18n) support, modern web design paradigms, AI Capital Planner UI, and accessible routing.
- **Startups**: Owns founder profiles, assessment drafts, readiness plans, and advisor snapshots.
- **Schemes**: Owns canonical programmes, immutable versions, eligibility requirements, and executable rules.
- **Recommendations**: Owns deterministic rule evaluation, eligibility assessments, scoring, ranking, and reviewer decisions.
- **Assistant**: Provides persisted agent sessions, tool-call logs, the founder concierge, and site-wide chatbots.

## Project Structure

```text
.
├── backend/                  # Django REST Framework backend
│   ├── apps/                 # Domain applications (startups, schemes, recommendations, assistant, etc.)
│   ├── config/               # Django project configuration
│   └── manage.py             # CLI entrypoint
├── frontend/                 # React + Vite frontend
│   ├── src/                  # React components, contexts (i18n), and styling
│   ├── public/               # Static assets
│   ├── package.json          # Frontend dependencies
│   └── vite.config.js        # Vite build configuration
├── docs/                     # Comprehensive architecture and domain documentation
│   ├── architecture/         # System architecture decisions
│   ├── frontend/             # UI/UX and routing documentation
│   ├── startups/             # Readiness and funding plan logic
│   └── PRODUCT_VISION_V2.md  # Vision and roadmap
├── infrastructure/           # Deployment and operational scripts
├── contracts/                # API and data contracts
├── docker-compose.yml        # Local development orchestration
├── PROJECT_CONTEXT.md        # Technical execution and invariants
└── README.md                 # Project entry point and summary
```

## Final Project Summary

The Startup Intelligence Platform has successfully reached an advanced MVP state aligned with the Product Vision V2. By combining a strictly verified PostgreSQL data core with deterministic logic engines, the platform delivers reliable, hallucination-free guidance for founders. The recent milestone integrated:
1. **Global i18n Localization**: Seamless English, Hindi, and Marathi switching across public and authenticated views.
2. **AI Capital Planner**: Interactive UI for burn-rate and financial scenario modeling.
3. **Modern Web Paradigms**: Enhanced accessibility and premium glassmorphism layouts.
4. **Agentic Workflows**: Bounded concierge and founder assistance using LangGraph and localized embeddings.

See [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) for the complete technical implementation context.

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

## Product Vision V2 roadmap

The platform is currently progressing through the **Product Vision V2** phases, transforming it into an AI Startup Operating System. 

Recent delivery and active milestones include:
- **Phase 50** — Public entry and authentication (landing, registration, responsive public navigation)
- **Phase 51** — Structured My Startup experience
- **Phase 52** — AI startup document intake
- **Phase 53** — Scheme knowledge completeness
- **Phase 54** — AI Startup Builder
- **Phase 55** — AI Capital Planner
- **Phase 56** — Universal AI Copilot
- **Phase 57** — Orchestration and data platform

See [PRODUCT_VISION_V2.md](docs/PRODUCT_VISION_V2.md) for the complete vision, principles, and roadmap.
