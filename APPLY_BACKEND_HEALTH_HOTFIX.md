# Backend health and frontend dependency hotfix

This update separates API startup from bundled catalog initialization. The API
can become healthy after checks and migrations, while catalog import runs as a
separate one-off service. A bad imported record can no longer prevent Vite from
starting or produce a blank page.

Apply the archive over the project root, then run:

```bash
chmod +x scripts/backend_repair.sh scripts/frontend_repair.sh scripts/laptop_setup.sh
./scripts/backend_repair.sh
```

Use `./scripts/backend_repair.sh --gpu` when the NVIDIA Compose override is
required.

The repair does not remove any named Docker data volumes.
