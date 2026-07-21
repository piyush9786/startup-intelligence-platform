# Founder Advisor Briefing Workspace v1

## Purpose

Phase 4G.1 replaces the foundation status screen with a founder-facing
workspace for persisted, grounded startup advisor briefings.

## Workflow

1. Authenticate through the existing JWT token endpoint.
2. Load startup profiles visible to the authenticated user.
3. Retrieve the current persisted briefing and complete briefing history.
4. Generate a new immutable advisor snapshot.
5. Generate a grounded LLM briefing from that snapshot.
6. Reload the persisted briefing history.

## Security

Access and refresh tokens are stored in browser `sessionStorage`, not
`localStorage`. They are removed when the founder signs out or the browser
tab session ends.

The frontend never accepts raw profile, readiness, recommendation, prompt,
model, provider, or briefing payload overrides. Generation sends only:

```json
{
  "startup_profile_id": "<uuid>"
}
```

followed by:

```json
{
  "advisor_snapshot_id": "<uuid>"
}
```

## Grounding display

The workspace displays source references attached to:

- top priorities;
- scheme guidance;
- risks.

Each reference identifies the persisted source type and JSON Pointer field
path. The source UUID remains available as the reference tooltip.

## Tests

The frontend test command uses Node's built-in test runner and validates:

- paginated API collection normalization;
- DRF error extraction;
- timeout and network error messages;
- citation-label rendering;
- briefing section counts;
- safe date formatting.

## API endpoints

- `POST /api/v1/auth/token/`
- `POST /api/v1/auth/token/refresh/`
- `GET /api/v1/startup-profiles/`
- `POST /api/v1/startup-advisor/snapshots/generate/`
- `POST /api/v1/startup-advisor/briefings/generate/`
- `GET /api/v1/startup-advisor/briefings/current/`
- `GET /api/v1/startup-advisor/briefings/`
- `GET /api/v1/startup-advisor/briefings/<briefing_id>/`
