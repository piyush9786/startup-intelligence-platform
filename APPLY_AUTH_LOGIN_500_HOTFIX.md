# Authentication 500 repair

From the active project directory:

```bash
cd /home/ps/Project/startup-intelligence-platform
unzip -o ~/Downloads/auth-login-500-hotfix.zip -d .
chmod +x scripts/auth_login_repair.sh
./scripts/auth_login_repair.sh
```

The repair:

- backs up `.env`;
- sets Docker-internal Redis and Celery service URLs;
- clears only Redis database 0 used for Django cache/rate limits;
- reapplies Django and JWT blacklist migrations;
- recreates backend/worker/beat/frontend;
- tests `/api/v1/auth/token/` with intentionally invalid credentials.

It does not delete users, passwords, PostgreSQL data, documents, MinIO data,
Qdrant vectors, Neo4j data, Ollama models, schemes, or startup profiles.
