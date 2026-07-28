# Startup Advisor Snapshot API v1

## Endpoint

```text
GET /api/v1/startup-advisor/current/?startup_profile_id=<uuid>
```

## Purpose

This endpoint returns the latest persisted startup guidance in one
read-only response. It combines independently persisted records rather
than generating new guidance.

## Response sections

```json
{
  "startup_profile": {
    "id": "<uuid>",
    "startup_name": "Example Startup",
    "legal_name": "Example Startup Private Limited",
    "stage": "mvp",
    "state": "Karnataka",
    "district": "Bengaluru Urban"
  },
  "readiness": {
    "has_assessment": true,
    "assessment": {}
  },
  "action_plan": {
    "has_action_plan": true,
    "action_plan": {}
  },
  "recommendations": {
    "has_generation": true,
    "generation": {},
    "recommendation_count": 1,
    "recommendations": []
  }
}
```

Each section has an explicit availability flag. Missing persisted records
return `null` or an empty list with HTTP 200.

A completed recommendation generation that produced zero recommendations
is represented as `has_generation: true`, with a non-null `generation`
object and an empty recommendation list.

## Current-record selection

- Readiness uses the newest assessment by `created_at` and UUID.
- Action planning uses the newest plan by `created_at` and UUID.
- Recommendations use the run marked `is_current` and its persisted,
  ranked recommendation rows.

These records are selected independently. A current action plan may
therefore reference an assessment older than the newest readiness
assessment.

## Authorization

Authentication is required.

Non-staff users may retrieve snapshots only for startup profiles they own.
Staff users may retrieve snapshots for any startup profile. Unknown or
inaccessible profiles return HTTP 404.

## Integrity behavior

Persisted current recommendation rows are validated against their
generation run. An inconsistent recommendation set returns HTTP 409 rather
than presenting a misleading snapshot.

## Read-only boundary

This endpoint does not:

- evaluate startup readiness;
- generate a readiness action plan;
- generate recommendations;
- update or create database records;
- invoke an LLM.

No model change or migration is introduced.
