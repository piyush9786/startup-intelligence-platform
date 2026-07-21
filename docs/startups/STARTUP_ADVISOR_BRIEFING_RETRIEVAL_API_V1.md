# Startup Advisor Briefing Retrieval API v1

## Purpose

This API exposes only previously persisted and validated
`StartupAdvisorBriefing` records.

Retrieval never calls Ollama, creates a briefing, recalculates readiness,
generates an action plan or recommendations, refreshes an advisor snapshot,
or writes to the database.

## Endpoints

```text
GET /api/v1/startup-advisor/briefings/current/?startup_profile_id=<uuid>
GET /api/v1/startup-advisor/briefings/?startup_profile_id=<uuid>
GET /api/v1/startup-advisor/briefings/<briefing_id>/
```

The current endpoint returns an explicit empty state when no briefing exists:

```json
{
  "startup_profile_id": "<uuid>",
  "has_briefing": false,
  "briefing": null
}
```

History is ordered by `completed_at`, `created_at`, and UUID, all descending.
Responses include complete stored prompt, schema, model, usage, response
metadata, citations, and briefing payloads.

Startup owners may retrieve their own records. Staff users may retrieve all
records. Unknown and inaccessible resources return HTTP 404.

This phase requires no migration.
