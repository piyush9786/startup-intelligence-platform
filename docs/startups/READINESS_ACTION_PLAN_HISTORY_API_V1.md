# Startup Readiness Action Plan History API v1

## Endpoints

```text
GET /api/v1/startup-readiness/action-plans/?startup_profile_id=<uuid>
GET /api/v1/startup-readiness/action-plans/<action_plan_id>/
```

## List behavior

The list endpoint returns all persisted readiness action plans for a visible
startup profile, ordered newest first.

```json
{
  "startup_profile_id": "<uuid>",
  "count": 2,
  "action_plans": []
}
```

A profile with no plans returns HTTP 200 with a zero count and an empty
`action_plans` list.

## Detail behavior

The detail endpoint returns one complete persisted action-plan payload,
including its ordered items, immutable source-assessment snapshot, counts,
next action, source engine version, and planner version.

Unknown or inaccessible action-plan identifiers return HTTP 404.

## Authorization

Authentication is required.

Non-staff users may list or retrieve plans only for startup profiles they
own. Staff users may access plans for any startup profile.

## Immutability

Both endpoints are read-only. They do not:

- regenerate an action plan;
- evaluate startup readiness;
- read current profile fields to rebuild a response;
- update or create database records;
- invoke an LLM.

Responses are serialized directly from stored
`StartupReadinessActionPlan` records.

## Ordering

Historical list ordering is deterministic:

1. newest `created_at`;
2. highest UUID identifier as the final tie-breaker.

## Boundaries

This phase adds historical list and detail retrieval only. It introduces no
model changes, migration, or generation behavior.
