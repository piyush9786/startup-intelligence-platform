# Phase 1: source registry and immutable raw ingestion

## Flow

1. A source is approved in `backend/catalog/source_registry/sources.csv`.
2. `import_sources` performs an idempotent database upsert.
3. `collect_sources` downloads one registered source URL.
4. The collector validates protocol, domain, DNS destination, redirects,
   robots policy, response size, status, and content type.
5. SHA-256 identifies duplicate and changed content.
6. Raw bytes are stored in MinIO using a content-addressed key.
7. PostgreSQL stores provenance, headers, version sequence, and crawl results.
8. An unchanged page does not create another document version.

## Commands

```bash
python manage.py import_sources
python manage.py collect_sources --domain startupindia.gov.in
python manage.py collect_sources --all --limit 2
```

`--ignore-robots` exists only for explicit manual diagnostics. Do not use it as
the normal collection mode.

## Security boundary

Collection URLs must use HTTP(S), match the registered domain allow-list,
use standard ports, and resolve only to public IP addresses. Redirects are
validated again before they are followed.
