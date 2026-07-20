# Startup Intelligence Platform

Upgradeable foundation for verified startup schemes, loans, registrations,
certificates, benefits, eligibility, recommendations, RAG, data ingestion,
notifications, and administrative verification.

## Local URLs

- Web: http://localhost:5173
- API health: http://localhost:8000/api/v1/health/
- API docs: http://localhost:8000/api/docs/
- Django admin: http://localhost:8000/admin/
- Qdrant: http://localhost:6333/dashboard
- Neo4j: http://localhost:7474
- MinIO: http://localhost:9001
- Mailpit: http://localhost:8025

## First run

```bash
docker compose build
docker compose run --rm backend python manage.py makemigrations
docker compose run --rm backend python manage.py migrate
docker compose up -d
docker compose exec backend python manage.py seed_sources
docker compose exec backend python manage.py createsuperuser
```
