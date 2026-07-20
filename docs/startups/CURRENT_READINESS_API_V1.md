# Current Startup Readiness Assessment API v1

## Endpoint

```text
GET /api/v1/startup-readiness/current/?startup_profile_id=<uuid>
```

Authentication is required. Non-staff users may access only startup
profiles they own. Staff users may retrieve the current readiness result
for any startup profile. Inaccessible profiles return HTTP 404.

## Behavior

The endpoint returns the latest persisted
`StartupReadinessAssessment`, ordered by creation time and assessment ID.
It does not run the readiness engine, update the startup profile, create a
new assessment, or modify existing records.

A successful response containing an assessment has this shape:

```json
{
  "startup_profile_id": "<uuid>",
  "has_assessment": true,
  "assessment": {
    "id": "<uuid>",
    "startup_profile_id": "<uuid>",
    "requested_by_id": "<uuid-or-null>",
    "assessment_date": "2026-07-21",
    "profile_snapshot": {},
    "status": "ready",
    "score": 100,
    "critical_score": 100,
    "recommended_score": 100,
    "findings": [],
    "blocking_findings": [],
    "summary": "...",
    "engine_version": "startup-readiness-v1",
    "created_at": "..."
  }
}
```

The assessment payload is serialized directly from persisted data,
including its original profile snapshot and engine output.

## Never-assessed state

A profile with no readiness assessment returns HTTP 200:

```json
{
  "startup_profile_id": "<uuid>",
  "has_assessment": false,
  "assessment": null
}
```

This distinguishes an accessible profile that has never been assessed
from an inaccessible or nonexistent profile.

## Version boundary

This phase adds read-only current-result retrieval. It requires no model
or migration change and does not add assessment-history listing.
