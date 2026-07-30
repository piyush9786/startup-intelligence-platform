# Laptop Setup Guide

This package is designed to run as a complete local stack with Docker Compose.
You do not need to install PostgreSQL, Redis, Node.js, Python packages, Qdrant,
Neo4j, MinIO, or Ollama directly on the laptop.

## 1. Prerequisites

For Ubuntu or another Linux distribution, install:

- Git (optional when using the ZIP archive)
- Docker Engine
- Docker Compose v2
- Python 3 and `curl` for the setup helper
- At least 16 GB RAM and 20 GB free disk space

For NVIDIA GPU mode, also install:

- A working NVIDIA driver (`nvidia-smi` must succeed)
- NVIDIA Container Toolkit

The CPU stack works without an NVIDIA GPU. A 4 GB NVIDIA GPU can run the
configured quantized `qwen3:4b` model, but closing other GPU-heavy programs is
recommended.

## 2. First launch

From the project root:

```bash
chmod +x bootstrap_current_project.sh scripts/*.sh
./bootstrap_current_project.sh
```

For NVIDIA GPU acceleration:

```bash
./bootstrap_current_project.sh --gpu
```

The setup script performs all required actions:

1. Creates `.env` from `.env.example`.
2. Generates local random secrets instead of retaining placeholder passwords.
3. Builds every container.
4. Starts PostgreSQL, Redis, Qdrant, Neo4j, MinIO, Ollama, Celery, Django, and Vite.
5. Applies Django migrations.
6. Imports the source registry.
7. Creates the reviewer-verified canonical scheme catalog.
8. Imports and reviews the bundled external scheme catalog.
9. Imports funding, loan, and certification datasets.
10. Runs a strict catalog-health check.

Open the application at <http://localhost:5173>.

## 3. Create a local administrator

```bash
./scripts/create_local_admin.sh
```

The command generates a password when one is not supplied. To choose the
credentials explicitly:

```bash
ADMIN_USERNAME=admin \
ADMIN_EMAIL=admin@example.local \
ADMIN_PASSWORD='replace-with-a-strong-local-password' \
./scripts/create_local_admin.sh
```

A normal founder account can also be created from the public registration page.

## 4. Common commands

```bash
./scripts/laptop_up.sh              # Start CPU mode
./scripts/laptop_up.sh --gpu        # Start GPU mode
./scripts/laptop_doctor.sh          # Check services and catalogs
./scripts/laptop_doctor.sh --gpu    # Include GPU/Ollama checks
./scripts/laptop_logs.sh            # Follow application logs
./scripts/laptop_down.sh            # Stop CPU mode
./scripts/laptop_down.sh --gpu      # Stop GPU mode
```

Equivalent `make` commands are available:

```bash
make laptop-setup
make laptop-setup-gpu
make doctor
make catalogs
make create-admin
make test
```

## 5. Catalog and dashboard recovery

When the dashboard shows zero verified schemes or scheme endpoints fail, run:

```bash
docker compose exec backend python manage.py bootstrap_catalogs
docker compose exec backend python manage.py platform_doctor --strict
```

Then sign out, sign in again, and refresh the browser. The frontend clears all
account-scoped cached data during authentication changes.

The dashboard deliberately does not display invented match percentages. Before
a founder assessment has generated recommendations, it shows the verified
canonical catalog. After recommendation generation, it switches to actual
eligibility and ranking output.

## 6. Optional live web research

Bundled catalogs work without an API key. Live web search is disabled by
default so a fresh laptop does not fail because of an empty provider key.

To enable Tavily, edit `.env`:

```dotenv
WEB_SEARCH_ENABLED=true
WEB_SEARCH_PROVIDER=tavily
TAVILY_API_KEY=your_key_here
```

Or use Brave Search:

```dotenv
WEB_SEARCH_ENABLED=true
WEB_SEARCH_PROVIDER=brave
BRAVE_API_KEY=your_key_here
```

Restart the backend and worker after changing `.env`:

```bash
docker compose restart backend worker
```

## 7. Local service addresses

| Service | Address |
|---|---|
| Web application | <http://localhost:5173> |
| Django API | <http://localhost:8000/api/v1/> |
| API documentation | <http://localhost:8000/api/docs/> |
| Django admin | <http://localhost:8000/admin/> |
| Mailpit | <http://localhost:8025> |
| Qdrant | <http://localhost:6333/dashboard> |
| Neo4j | <http://localhost:7474> |
| MinIO | <http://localhost:9001> |
| Ollama | <http://localhost:11434> |

## 8. Full local reset

This permanently removes the local PostgreSQL database, uploaded files, model
volumes, queues, and generated `.env`:

```bash
./scripts/laptop_reset.sh --yes
```

Run the first-launch command again after a reset.

## 9. Troubleshooting

### Backend remains unhealthy

```bash
docker compose ps
docker compose logs --tail=250 backend postgres minio_init
```

### Advisor model is unavailable

```bash
docker compose logs --tail=200 ollama ollama_init worker
docker compose exec ollama ollama list
```

For GPU mode:

```bash
nvidia-smi
docker compose -f docker-compose.yml -f docker-compose.gpu.yml \
  exec ollama ollama ps
```

### Frontend shows old account data

Sign out through the application instead of only closing the browser tab. The
project now serializes logout and token refresh operations and clears the query
cache whenever the authenticated account changes.
