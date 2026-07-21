# Current Startup Readiness Action Plan API v1

## Endpoint

```text
GET /api/v1/startup-readiness/action-plans/current/?startup_profile_id=<uuid>
```

## Behavior

The endpoint returns the newest persisted
`StartupReadinessActionPlan` for the requested startup profile.

It never regenerates an action plan, never evaluates startup readiness,
and never updates stored data. The response is built entirely from the
persisted action-plan record, including its ordered items and immutable
source-assessment snapshot.

When a visible startup profile has no action plan, the endpoint returns
HTTP 200:

```json
{
  "startup_profile_id": "<uuid>",
  "has_action_plan": false,
  "action_plan": null
}
```

When a plan exists, `has_action_plan` is true and `action_plan` contains
the complete read-only action-plan serializer payload.

## Authorization

Authentication is required.

Non-staff users may retrieve plans only for startup profiles they own.
Staff users may retrieve plans for any startup profile. Unknown or
inaccessible profile identifiers return HTTP 404.

## Ordering

Current selection is deterministic:

1. newest `created_at`;
2. highest UUID identifier as the final tie-breaker.

## Boundaries

This phase adds current-plan retrieval only. It introduces no model
changes, migration, generation behavior, historical list endpoint, or LLM.
