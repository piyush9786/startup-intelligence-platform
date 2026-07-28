# Persisted Startup Readiness Action Plans v1

## Purpose

This phase persists deterministic remediation plans generated only from
previously stored `StartupReadinessAssessment` records.

The live startup profile is never evaluated. The service reconstructs a
readiness evaluation from the persisted assessment status, scores,
findings, summary, and engine version, then passes that reconstruction to
the deterministic action-plan builder.

## Endpoint

```text
POST /api/v1/startup-readiness/action-plans/generate/
```

Request:

```json
{
  "readiness_assessment_id": "<uuid>"
}
```

Raw profile, assessment, and findings payloads are rejected.

Authentication is required. A non-staff user may generate a plan only from
an assessment belonging to a startup profile they own. Staff users may use
any assessment. Inaccessible or nonexistent assessments return HTTP 404.

## Persisted record

Each `StartupReadinessActionPlan` stores the requester, startup profile,
protected source-assessment reference, immutable source snapshot, readiness
status, action-presence flag, summary counts, next action, ordered action
items, source engine version, planner version, and timestamps.

Repeated generation creates additional historical plans. Existing plans
are never replaced.

## Integrity

Database constraints require action presence to agree with the total count
and next action, and require blocker plus recommendation counts to equal the
total action count.

## Boundaries

This phase adds generation and persistence only. It does not add action-plan
current/history retrieval, does not recalculate readiness, and uses no LLM.
