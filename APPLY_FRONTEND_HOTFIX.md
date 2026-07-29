# Apply the frontend white-screen hotfix

Extract this archive over the root of the already extracted
`startup-intelligence-platform` directory, allowing files to be replaced.
Then run:

```bash
chmod +x scripts/frontend_repair.sh scripts/laptop_setup.sh scripts/laptop_doctor.sh
./scripts/frontend_repair.sh
```

For the NVIDIA GPU compose profile:

```bash
./scripts/frontend_repair.sh --gpu
```

The repair removes only the Docker volume containing npm dependencies. It does
not remove PostgreSQL, Redis, MinIO, Neo4j, Qdrant, Ollama models, or uploads.
