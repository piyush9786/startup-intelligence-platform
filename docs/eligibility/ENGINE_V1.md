# Deterministic Eligibility Engine v1

## Purpose

The v1 engine evaluates a startup profile against one verified canonical
`SchemeVersion` without an LLM and without writing to the database.

Each canonical rule produces one outcome:

- `pass`
- `fail`
- `unknown`

## Assessment precedence

1. `application_closed`
2. `verification_required`
3. `ineligible`
4. `insufficient_information`
5. `eligible`

A failed mandatory rule makes the assessment ineligible. Missing data for a
mandatory rule produces insufficient information only when no mandatory rule
fails. Unsupported fields, operators, rule groups, malformed comparisons, or
rules that are not manually verified require manual verification.

## Rule groups

Engine v1 supports only blank rule groups and `all`. Both are interpreted as
logical AND. Any other group is deliberately not guessed and produces
`verification_required`.

## Pilot profile mappings

| Rule field | StartupProfile source |
| --- | --- |
| `dpiit_recognized` | `StartupProfile.dpiit_recognized` |
| `startup_age_months` | Complete calendar months derived from `incorporation_date` |
| `eligible_entity_type` | `profile_data.entity_types`, then `profile_data.entity_type`, otherwise `["startup"]` |
| `regulatory_registration` | `profile_data.regulatory_registrations`, then `profile_data.regulatory_registration` |

`StartupProfile` is a startup-facing model, so its default entity type is
`startup`. This makes startup-only schemes deterministic and makes the
AIF-facing Fund of Funds scheme fail for an ordinary startup profile. An AIF
assessment must explicitly provide:

```json
{
  "entity_types": ["alternative_investment_fund"],
  "regulatory_registrations": ["SEBI"]
}
```

## Time semantics

`startup_age_months` uses anniversary-based calendar months, rounded up when
the assessment date is past the monthly anniversary. Therefore, one day past
the 24-month anniversary evaluates as 25 months. The date is required in tests and should be explicitly
supplied by callers that need reproducible historical assessments.

## Persistence

This slice is pure evaluation. Persisting an `EligibilityAssessment`, exposing
an API endpoint, and ranking recommendations are separate follow-up slices.
