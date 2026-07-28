# Infrastructure

## Local development

The complete local stack runs through Docker Compose.

Current services:

- PostgreSQL 17;
- Redis 7.4;
- Qdrant;
- Neo4j Community with APOC;
- MinIO;
- Ollama;
- Mailpit;
- Django web process;
- Celery worker;
- Celery beat;
- React and Vite frontend.

Start the stack with:

```bash
cp .env.example .env
docker compose build
docker compose up -d
docker compose exec -T backend python manage.py migrate
```

Inspect it with:

```bash
docker compose ps
docker compose logs -f backend worker frontend
```

## Data ownership

PostgreSQL is authoritative.

MinIO stores:

- collected raw source objects;
- processed document objects where configured;
- private startup eligibility evidence.

Qdrant stores rebuildable embeddings and chunk metadata.

Neo4j stores rebuildable relationship projections and will later support the
verified scheme-prerequisite graph.

Redis is used for Celery transport, Celery results, caching, and temporary
coordination.

## Local ports

| Service | Address |
| --- | --- |
| Frontend | `http://localhost:5173` |
| Backend | `http://localhost:8000` |
| PostgreSQL | `127.0.0.1:5433` |
| Redis | `127.0.0.1:6379` |
| Qdrant | `127.0.0.1:6333` |
| Neo4j browser | `http://localhost:7474` |
| Neo4j Bolt | `127.0.0.1:7687` |
| MinIO API | `127.0.0.1:9000` |
| MinIO console | `http://localhost:9001` |
| Ollama | `127.0.0.1:11434` |
| Mailpit | `http://localhost:8025` |

## Production-hardening roadmap

Production deployment must add:

- reverse proxy and TLS;
- environment-specific immutable images;
- managed PostgreSQL and Redis where appropriate;
- durable S3-compatible object storage;
- centralized secret management;
- application metrics, logs, traces, and alerts;
- database and object-storage backup automation;
- tested restore and disaster-recovery procedures;
- malware scanning and content validation for uploads;
- retention and deletion policy for private evidence;
- worker autoscaling and queue monitoring;
- API and database load testing;
- network isolation;
- permission and penetration testing;
- controlled schema and data migrations;
- deployment rollback procedures.

Kafka-compatible event transport should only be introduced when measured event
volume or service extraction justifies the additional operational complexity.

See the [project context](../PROJECT_CONTEXT.md) and
[architecture documentation](../docs/architecture/README.md) for the system's
data and trust boundaries.
