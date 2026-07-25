# Deterministic Eligibility Engine

The historical filename is retained for compatibility.

The current runtime engine version is `rules-v5`.

## Purpose

The engine evaluates one startup profile against one verified canonical
`SchemeVersion`.

The evaluator is deterministic and makes no LLM calls.

Higher-level services persist assessments, generate recommendations, and retain
immutable evidence snapshots around the pure evaluation result.

## Authoritative inputs

An evaluation uses:

- a stored `StartupProfile`;
- an explicit assessment date;
- one verified `SchemeVersion`;
- its verified executable `EligibilityRule` records;
- current effective reviewer-approved values, when available.

Automatically extracted but unreviewed rules must not be executed as
authoritative eligibility requirements.

## Rule outcomes

Each rule produces exactly one outcome:

- `pass`;
- `fail`;
- `unknown`.

A rule evaluation retains:

- rule ID;
- field path;
- operator;
- expected and actual value;
- mandatory flag;
- rule group;
- reason;
- source evidence text and page;
- whether verification is required;
- reviewer-verification provenance when an approved value was used.

## Assessment precedence

Overall result precedence is:

1. `application_closed`
2. `verification_required`
3. `ineligible`
4. `insufficient_information`
5. `eligible`

A failed mandatory rule makes the assessment ineligible.

Missing data for a mandatory rule produces insufficient information only when
no mandatory rule fails.

Unsupported fields, operators, malformed comparisons, unsupported rule groups,
or unverified canonical rules require verification instead of guessed
evaluation.

## Supported rule groups

Blank rule groups and `all` are supported.

Both are interpreted as logical AND.

Other groups deliberately return `verification_required`.

More complex Boolean rule graphs must be introduced as an explicit and
versioned engine capability instead of being inferred from free-form text.

## Supported operators

The current deterministic operator set is:

- `exists`;
- `not_exists`;
- `equals`;
- `not_equals`;
- `in`;
- `not_in`;
- `contains_any`;
- `contains_all`;
- `greater_than`;
- `greater_or_equal`;
- `less_than`;
- `less_or_equal`;
- `between`.

String comparisons are normalized.

Numeric comparisons use decimal conversion and reject unsafe Boolean or
malformed values.

## Profile field mappings

| Rule field | StartupProfile source |
| --- | --- |
| `dpiit_recognized` | `StartupProfile.dpiit_recognized` |
| `startup_age_months` | Calendar months derived from `incorporation_date` |
| `eligible_entity_type` | `profile_data.entity_types`, then `profile_data.entity_type`, otherwise `["startup"]` |
| `regulatory_registration` | `profile_data.regulatory_registrations`, then `profile_data.regulatory_registration` |

`StartupProfile` is startup-facing, so a blank entity type defaults to
`startup`.

Explicit non-startup entity types remain authoritative.

For example, an AIF context must be explicitly supplied:

```json
{
  "entity_types": ["alternative_investment_fund"],
  "regulatory_registrations": ["SEBI"]
}
```

Rule-specific manual fields may be resolved from an effective
reviewer-approved verification value.

## Manual verification

The verification workflow is:

```text
unresolved rule
→ founder submission
→ private evidence upload
→ reviewer queue
→ immutable approval or rejection
→ effective-value lookup
→ deterministic re-evaluation
```

Founder claims are non-authoritative.

An approval may affect eligibility only when it is:

- current for the submission chain;
- effective on the assessment date;
- not expired;
- linked to the same startup, scheme version, and rule.

Later rejection, supersession, or expiry prevents stale approval use.

## Verification provenance

When an approved value is used, the rule evaluation retains:

- decision ID;
- submission ID;
- valid-from date;
- expiry date.

Those internal references are persisted in assessment and recommendation
snapshots for auditability.

Founder explanations use the `eligibility-explanation-v2` contract and expose
only safe content such as:

- the relevant requirement;
- the fact that reviewer-approved evidence was used;
- effective and expiry dates.

The UI must not render internal decision IDs, submission IDs, reviewer identity,
private notes, or storage locations.

## Time semantics

`startup_age_months` uses anniversary-based calendar months and rounds up when
the assessment date is past the monthly anniversary.

One day past the 24-month anniversary therefore evaluates as 25 months.

Callers should supply an explicit date for reproducible historical assessments.

Future incorporation dates are rejected by startup input validation and are
also treated as unusable by evaluation.

## Persistence

The assessment service persists an immutable `EligibilityAssessment`
containing:

- result;
- engine version;
- matched rules;
- failed rules;
- unknown rules;
- source and scheme-version context;
- assessment date.

Recommendation generation persists:

- ranked recommendations;
- excluded scheme outcomes;
- evidence snapshots;
- eligibility explanations;
- verification provenance;
- a generation-run snapshot.

Re-running eligibility creates new historical output instead of rewriting an
old assessment.

## Recommendation boundary

Only eligible and actionable schemes may enter the ranked recommendation list.

Schemes with no executable verified rules, unresolved verification, missing
mandatory information, failed mandatory rules, or closed applications remain
auditable but are excluded from actionable ranked matches.

## Concurrency

Verification-submission creation locks the stable `StartupProfile` parent
before checking for and replacing the current submission.

This serializes the first-submission case where no child row exists and prevents
database uniqueness races from surfacing to founders.

## Testing expectations

Changes to eligibility must cover:

- direct rule behavior;
- overall result precedence;
- profile field resolution;
- time boundaries;
- persistence;
- recommendation inclusion or exclusion;
- effective approval use;
- rejection, supersession, and expiry;
- provenance snapshots;
- founder-safe rendering;
- concurrent submission behavior when relevant.
