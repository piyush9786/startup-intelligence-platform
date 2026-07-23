# Persisted Eligibility Assessment API

## Endpoint

`POST /api/v1/eligibility/evaluate/`

Authentication is required.

## Request

```json
{
  "scheme_id": "scheme-uuid",
  "startup_profile_id": "profile-uuid",
  "assessment_date": "2026-07-20"
}
```

`assessment_date` is optional and defaults to the current local date.

Raw client-provided `profile` JSON is rejected. The evaluator only receives a
stored `StartupProfile` selected by ID.

## Authorization

Non-staff users may assess only profiles they own. A profile belonging to
another user returns `404`, preventing profile-existence disclosure. Staff
users may assess any stored profile.

## Persistence

A successful request creates one `EligibilityAssessment` and returns HTTP
`201`. The row stores:

- the requesting user;
- the exact current `SchemeVersion`;
- the assessment date;
- an immutable JSON snapshot of the startup profile inputs;
- matched, failed, and unknown rule snapshots;
- the deterministic result, explanation, and engine version.

Editing the startup profile later does not mutate an existing assessment.

## Conflict

A scheme with no current version returns HTTP `409` and creates no assessment.

A verified scheme version with no executable eligibility rules returns
`verification_required`. It is assessed and persisted for auditability but is
excluded from automatic recommendations until verified rules are available.

## Response

```json
{
  "id": "assessment-uuid",
  "startup_profile_id": "profile-uuid",
  "scheme_id": "scheme-uuid",
  "scheme_version_id": "version-uuid",
  "scheme_name": "Startup India Seed Fund Scheme (SISFS)",
  "assessment_date": "2026-07-20",
  "profile_snapshot": {},
  "result": "eligible",
  "matched_rules": [],
  "failed_rules": [],
  "unknown_rules": [],
  "explanation": "All mandatory eligibility rules passed.",
  "engine_version": "rules-v3",
  "created_at": "2026-07-20T12:00:00Z"
}
```
