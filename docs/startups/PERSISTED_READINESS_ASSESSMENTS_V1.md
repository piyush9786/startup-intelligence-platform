# Persisted Startup Readiness Assessments v1

## Purpose

A readiness evaluation is now persisted as an immutable historical
assessment. The stored record captures the exact startup profile and
deterministic engine output used at assessment time.

Existing assessments are never replaced when a new assessment is created.

## Model

`StartupReadinessAssessment` stores:

- requesting user;
- startup profile;
- assessment date;
- immutable startup-profile snapshot;
- readiness status;
- overall, critical, and recommended scores;
- all ordered findings;
- blocking findings;
- deterministic summary;
- readiness engine version;
- creation and update timestamps.

The requesting user is nullable so audit records remain available if the
user account is later removed. Assessments are deleted with their startup
profile.

Score fields are constrained to the inclusive range from 0 to 100.

## Evaluation service

`create_startup_readiness_assessment()` calls the Phase 4C.1 deterministic
engine, serializes its exact output, snapshots the stored startup profile,
and creates one historical assessment in a database transaction.

The service does not modify the startup profile or any previous
assessment.

## API

```text
POST /api/v1/startup-readiness/evaluate/
```

Example request:

```json
{
  "startup_profile_id": "<uuid>",
  "assessment_date": "2026-07-21"
}
```

`assessment_date` is optional and defaults to the server's local date.
Raw profile JSON is rejected; the endpoint evaluates only a stored startup
profile.

Successful creation returns HTTP 201 with the complete persisted
assessment.

Non-staff users may assess only startup profiles they own. Staff users may
assess any startup profile. An inaccessible profile returns HTTP 404.

## Version boundary

This phase persists and exposes the existing
`startup-readiness-v1` result. It does not alter readiness rules, provide
current/history retrieval endpoints, or integrate LLM-generated advice.
