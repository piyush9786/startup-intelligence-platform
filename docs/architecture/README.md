# Architecture

The initial deployment is a modular monolith with asynchronous workers.

- PostgreSQL is authoritative for structured business data and rule results.
- MinIO stores immutable raw HTML/PDF/JSON objects.
- Qdrant stores embeddings and chunk metadata.
- Neo4j stores stable ecosystem relationships.
- Redis provides caching, Celery transport, and temporary state.
- Celery runs collection, extraction, embedding, verification, and alerts.

Domain modules communicate through service functions and versioned event contracts.
High-load modules can later be extracted without changing public API contracts.
