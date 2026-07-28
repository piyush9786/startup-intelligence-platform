# Laptop-Ready Repair Summary

This package repairs the merged project snapshot so a fresh laptop database
starts with the data and service order expected by the frontend.

## Functional corrections

- Added an idempotent canonical scheme bootstrap from the bundled
  reviewer-curated manifests.
- Ensured the 89 external scheme records can be reviewed against seven exact
  canonical scheme names.
- Unified source, verified scheme, external scheme, capital support, loan, and
  certification imports under `python manage.py bootstrap_catalogs`.
- Added `python manage.py platform_doctor --strict` to detect missing database
  or catalog state immediately.
- Corrected first-start ordering for PostgreSQL, Redis, MinIO buckets, Ollama
  model download, Django, Celery, and Vite.
- Added safe laptop environment generation and disabled API-key-dependent web
  search by default.
- Added CPU and NVIDIA GPU startup, shutdown, reset, logs, diagnostics, and
  local administrator scripts.

## Dashboard and account corrections

- The dashboard now shows the verified catalog before a founder has generated
  personalized recommendations.
- It no longer invents recommendation percentages for a new account.
- After an assessment, the same card switches to real eligibility and ranking
  results.
- Dashboard state is cleared when the selected startup changes, preventing a
  previous profile's data from remaining visible while the next profile loads.
- Account-scoped query/session protections already present in the source are
  retained.

## Validation completed in this build environment

- All backend Python source files compile.
- All frontend JavaScript/JSX source files pass TypeScript parser syntax checks.
- All shell scripts pass `bash -n`.
- All bundled JSON files parse.
- All Docker Compose YAML files parse.
- `git diff --check` passes.

Full Docker execution, Django tests, frontend tests, lint, and production builds
could not be run in this build environment because Docker is unavailable and
the internal npm/Python package mirrors returned availability errors. The
included `make test` command runs those checks on a laptop after Docker images
are built.
