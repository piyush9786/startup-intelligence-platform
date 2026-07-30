# Startup Intelligence Platform — From Project Files to Working Endpoints

## Source package

This guide starts the project files in this archive or checkout. It does not
clone or pin an older repository snapshot. Use the included scripts so the
backend, worker, object-storage buckets, verified scheme catalog, external
support catalogs, and frontend are initialized in the correct order.

## Fastest method

From the project root:

```bash
chmod +x bootstrap_current_project.sh scripts/*.sh
./bootstrap_current_project.sh
```

For an NVIDIA GPU with NVIDIA Container Toolkit installed:

```bash
./bootstrap_current_project.sh --gpu
```

The script performs the complete local startup sequence:

1. Creates `.env` from `.env.example` when needed.
2. Replaces unsafe local placeholder secrets with generated values.
3. Builds and starts PostgreSQL, Redis, Qdrant, Neo4j, MinIO, Ollama,
   Django, Celery, and Vite.
4. Creates all required MinIO buckets.
5. Applies Django migrations.
6. Imports source metadata and the reviewer-verified canonical scheme catalog.
7. Imports and reviews external schemes, capital support, funding, loans, and
   certification requirements.
8. Runs a strict platform catalog-health check.

## Manual equivalent

```bash
cp .env.example .env
# Replace placeholder secrets in .env, then run:
docker compose up -d --build
docker compose exec -T backend python manage.py bootstrap_catalogs
docker compose exec -T backend python manage.py platform_doctor --strict
```

The helper script is preferred because it generates local secrets and waits for
service readiness automatically.

Optional live search can be enabled later in `.env` by setting
`WEB_SEARCH_ENABLED=true` and adding a Tavily or Brave API key. Bundled scheme
and support data does not require a search API key.

## Local entry points

| Component | URL |
|---|---|
| React application | `http://localhost:5173` |
| API health | `http://localhost:8000/api/v1/health/` |
| Swagger API documentation | `http://localhost:8000/api/docs/` |
| OpenAPI schema | `http://localhost:8000/api/schema/` |
| Django admin | `http://localhost:8000/admin/` |
| Qdrant dashboard | `http://localhost:6333/dashboard` |
| Neo4j browser | `http://localhost:7474` |
| MinIO console | `http://localhost:9001` |
| Mailpit | `http://localhost:8025` |

## Main API groups

### Authentication

```text
POST /api/v1/auth/register/
GET  /api/v1/auth/me/
POST /api/v1/auth/token/
POST /api/v1/auth/token/refresh/
POST /api/v1/auth/token/logout/
```

### Founder profile and onboarding

```text
/api/v1/startup-profiles/
/api/v1/startup-onboarding/current/
/api/v1/startup-profiles/autofill-from-document/
/api/v1/startup-assessment-drafts/
/api/v1/startup-assessment-drafts/<draft_id>/submit/
```

### Startup advisor and research handoff

```text
/api/v1/startup-advisor/current/
/api/v1/startup-advisor/snapshots/generate/
/api/v1/startup-advisor/briefings/generate/
/api/v1/startup-advisor/briefings/current/
/api/v1/startup-advisor/briefings/
/api/v1/startup-advisor/briefings/<briefing_id>/
/api/v1/startup-advisor/briefings/jobs/current/
/api/v1/startup-advisor/briefings/jobs/<job_id>/
/api/v1/research/...
```

### Readiness and plans

```text
/api/v1/startup-readiness/evaluate/
/api/v1/startup-readiness/current/
/api/v1/startup-readiness/assessments/
/api/v1/startup-readiness/action-plans/generate/
/api/v1/startup-readiness/action-plans/current/
/api/v1/startup-funding-plans/generate/
/api/v1/startup-funding-plans/current/
/api/v1/startup-starting-plans/generate/
/api/v1/startup-starting-plans/current/
/api/v1/startup-capital-plans/generate/
/api/v1/startup-capital-plans/current/
```

### Startup builder and milestones

```text
/api/v1/startup-builder/generate-master-plan/
/api/v1/startup-builder/generate-resume/
/api/v1/startup-builder/sections/
/api/v1/startup-builder/sections/<section_type>/
/api/v1/startup-builder/sections/<section_type>/draft/
/api/v1/startup-milestones/
/api/v1/startup-milestones/<milestone_id>/
/api/v1/startup-milestones/<milestone_id>/complete/
/api/v1/startup-milestones/<milestone_id>/log-update/
```

### Operations workflows

```text
/api/v1/compliance-records/
/api/v1/consultant-profiles/
/api/v1/consultation-requests/
/api/v1/founder-vault-documents/
/api/v1/application-tasks/
/api/v1/application-stage-events/
/api/v1/application-workflows/
/api/v1/application-workflows/<id>/transition/
```

### Verification and intelligence

```text
/api/v1/startups/verify-instant/
/api/v1/startups/<profile_id>/intelligence/
```

Other route groups are mounted for assistant, companies, discovery, documents, knowledge, recommendations, schemes, and sources. Use the live Swagger documentation at `/api/docs/` for the current authoritative API endpoint list.

## Stack represented by the code

- Frontend: React 19, Vite, React Router, TanStack Query, custom i18n.
- Backend: Django 5.2, Django REST Framework, JWT/cookie authentication.
- Data: PostgreSQL.
- Jobs/cache: Redis, Celery worker, Celery Beat.
- RAG/vector storage: Qdrant.
- Dependency graph: Neo4j.
- Object/document storage: MinIO.
- Local AI: Ollama with `qwen3:4b` and `embeddinggemma`.
- ML: scikit-learn/joblib models.
- Development email: Mailpit.

## Verification commands

```bash
docker compose ps

docker compose exec -T backend pytest -q
docker compose exec -T backend ruff check .
docker compose exec -T backend python manage.py makemigrations --check --dry-run

docker compose exec -T frontend npm test
docker compose exec -T frontend npm run lint
docker compose exec -T frontend npm run build

curl -f http://localhost:8000/api/v1/health/
curl -f http://localhost:5173/
```

## Updating later

The bootstrap is intentionally pinned so you always reproduce the same code. To move to a newer GitHub version later:

```bash
git fetch origin
git switch main
git pull --ff-only origin main
```

Review the new commit before replacing your pinned working snapshot.
