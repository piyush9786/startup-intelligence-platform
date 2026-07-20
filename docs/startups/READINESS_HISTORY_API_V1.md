# Startup Readiness Assessment History API v1

## Endpoints

List all persisted assessments for one startup profile:

```text
GET /api/v1/startup-readiness/assessments/?startup_profile_id=<uuid>
```

Retrieve one persisted assessment:

```text
GET /api/v1/startup-readiness/assessments/<assessment_id>/
```

Authentication is required. Non-staff users may access only assessments
belonging to startup profiles they own. Staff users may access any
assessment. Inaccessible profiles and assessments return HTTP 404.

## List response

Assessments are ordered newest first using creation time and assessment ID
as deterministic tie-breakers.

```json
{
  "startup_profile_id": "<uuid>",
  "count": 2,
  "assessments": [
    {
      "id": "<uuid>",
      "startup_profile_id": "<uuid>",
      "requested_by_id": "<uuid-or-null>",
      "assessment_date": "2026-07-21",
      "profile_snapshot": {},
      "status": "ready_with_recommendations",
      "score": 97,
      "critical_score": 100,
      "recommended_score": 88,
      "findings": [],
      "blocking_findings": [],
      "summary": "...",
      "engine_version": "startup-readiness-v1",
      "created_at": "..."
    }
  ]
}
```

An accessible profile with no assessments returns HTTP 200 with
`count: 0` and an empty `assessments` list.

## Detail response

The detail endpoint returns the complete persisted assessment serializer
payload, including its immutable profile snapshot, ordered findings,
blocking findings, scores, requester, assessment date, and engine
version.

## Read-only behavior

Both endpoints perform database reads only. They do not run the readiness
engine, create assessments, update startup profiles, or modify historical
records.

## Version boundary

This phase adds readiness-assessment history retrieval. It requires no
model or migration change and does not add pagination or generated advice.
