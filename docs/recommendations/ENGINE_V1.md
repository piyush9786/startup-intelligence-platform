# Deterministic Recommendations v1

## Scope

The recommendation generator evaluates every active scheme whose current
version is verified. Each evaluation is persisted as an
`EligibilityAssessment`.

Only assessments with the `eligible` result are candidates. The current
application status must be one of:

- `open`
- `rolling`
- `unknown`

`unknown` remains recommendable because it does not prove closure, but it
receives a lower application-status component. `upcoming` and `closed`
versions are not included in the current actionable recommendation set.

## Score

Scores are deterministic decimals with six places:

```text
eligibility_component
+ rule_match_component
+ application_status_component
```

Components:

- eligible result: `0.700000`
- matched-rule ratio: up to `0.200000`
- application status:
  - open: `0.100000`
  - rolling: `0.090000`
  - unknown: `0.050000`

An eligible scheme with all rules matched and unknown application status
therefore scores `0.950000`.

## Ranking

Recommendations are ordered by:

1. score descending;
2. canonical scheme name, case-insensitive;
3. scheme-version UUID.

Ranks start at one and are unique inside a generation.

## Replacement and audit behavior

Generation locks the selected startup profile and runs inside one database
transaction. Assessments are created for all in-scope schemes. The existing
current recommendation rows for that profile are then replaced atomically.

Historical assessments remain stored. Recommendation rows carry a shared
`generation_id`, `ranking_version`, score breakdown, and evidence snapshot.

## API

`POST /api/v1/recommendations/generate/`

Authentication is required.

```json
{
  "startup_profile_id": "profile-uuid",
  "assessment_date": "2026-07-20"
}
```

`assessment_date` is optional. Raw client-provided `profile` JSON is
rejected. Non-staff users may generate recommendations only for profiles
they own; staff users may generate for any stored profile.
