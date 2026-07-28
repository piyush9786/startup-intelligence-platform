# Consolidated Deterministic Starting Plan v1

## Purpose

Phase 47 gives a founder one persisted view of the actions and verified
opportunities produced by the existing deterministic platform services.

The starting plan does not introduce a new decision engine. It composes:

- one persisted startup-readiness assessment;
- the readiness action plan derived from that assessment;
- one persisted recommendation generation run;
- the immutable snapshots and engine versions carried by those records.

The contract version is `startup-starting-plan-v1`.

## Authority boundary

The starting plan may preserve and present existing ordering:

- readiness actions retain the deterministic order from
  `startup-readiness-action-plan-v1`;
- scheme opportunities retain rank from the selected recommendation run.

Phase 47 does not claim that a readiness action is a prerequisite for a scheme.
Every item therefore exposes:

```json
{
  "dependency_status": "not_evaluated"
}
```

Verified prerequisite edges and dependency-aware ordering remain the
responsibility of Phases 48 and 49.

No language model creates, removes, ranks, or reorders starting-plan items.

## Persistence

`StartupStartingPlan` is an owner-scoped, versioned snapshot with protected
references to:

- `StartupReadinessAssessment`;
- `StartupReadinessActionPlan`;
- `RecommendationGenerationRun`.

It stores:

- the submitted profile snapshot;
- readiness and action-plan snapshots;
- recommendation-generation metadata;
- the recommendation snapshot;
- normalized plan items;
- item counts and the first item;
- the plan version;
- current/history state.

There is at most one current starting plan per startup profile.

The combination of action-plan source and recommendation-generation source is
unique. Repeating generation with the same persisted sources is idempotent and
returns the existing plan.

## Item contract

Readiness items use `item_type=readiness_action` and retain:

- readiness priority;
- action and reason;
- field path and finding code;
- source assessment and action-plan identifiers;
- readiness and action-planner versions.

Scheme items use `item_type=scheme_opportunity` and retain:

- recommendation rank and score;
- scheme and scheme-version identifiers;
- eligibility assessment identifier;
- recommendation-run identifier;
- ranking and eligibility engine versions.

All new items begin with `status=not_started`. Phase 47 does not yet provide
progress mutation; Phase 50 will introduce verification-aware progress states.

## Generation

Confirmed assessment submission creates the starting plan in the same database
transaction as:

1. the startup profile update;
2. the readiness assessment;
3. the readiness action plan;
4. eligibility and recommendation generation;
5. concierge completion.

If any step fails, the transaction rolls back.

Existing profiles may generate or refresh a plan from their latest persisted
action plan and current recommendation run.

Raw profile, readiness, action-plan, or recommendation payloads are rejected by
the generation API.

## API

Generate or idempotently retrieve from current persisted sources:

```text
POST /api/v1/startup-starting-plans/generate/
```

Request:

```json
{
  "startup_profile_id": "uuid"
}
```

Retrieve the current plan:

```text
GET /api/v1/startup-starting-plans/current/?startup_profile_id=uuid
```

Retrieve history:

```text
GET /api/v1/startup-starting-plans/?startup_profile_id=uuid
```

Retrieve one historical plan:

```text
GET /api/v1/startup-starting-plans/{starting_plan_id}/
```

All endpoints require authentication and apply the existing startup-profile
visibility boundary. Founders receive `404` for another founder's profile or
plan.

## Frontend

The founder workspace includes a dedicated **Starting plan** view.

It:

- loads only persisted API data;
- groups critical readiness work, strengthening actions, and scheme
  opportunities;
- links readiness items to the action roadmap;
- links scheme opportunities to the verified scheme explorer;
- displays source identifiers and the plan version;
- states that dependency ordering has not yet been evaluated;
- supports idempotent refresh from current persisted records.

The concierge terminal state links to this view for an existing selected
startup profile.

## Validation

Coverage includes:

- deterministic composition and ordering;
- source and version provenance;
- source mismatch rejection;
- idempotent generation;
- current, history, and detail retrieval;
- owner isolation and authentication;
- raw-payload rejection;
- assessment-submission integration;
- concierge regression behavior;
- founder rendering, navigation, empty state, and ordering-boundary text.
