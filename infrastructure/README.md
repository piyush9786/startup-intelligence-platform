# Infrastructure roadmap

Local development uses Docker Compose. Production overlays will later add:

- reverse proxy and TLS
- managed PostgreSQL and Redis
- S3-compatible object storage
- secret management
- metrics, logs and traces
- container orchestration
- backup and restore automation
- Kafka-compatible event transport when volume requires it
