# Deterministic Startup Readiness Engine v1

## Scope

The readiness engine is a pure evaluation service for a stored
`StartupProfile`. It performs no database writes, exposes no API endpoint,
creates no model, and makes no LLM calls.

The caller provides an explicit assessment date so the same profile and
date always produce the same result.

## Outcomes

Every check returns exactly one outcome:

- `present`: usable data is available;
- `missing`: no usable value was supplied;
- `incomplete`: partial data is available but needs completion;
- `invalid`: the supplied value cannot be safely used.

Checks are classified as `critical` or `recommended`.

## Status

- `blocked`: one or more critical checks are not present;
- `ready_with_recommendations`: all critical checks are present, but one
  or more recommended checks need attention;
- `ready`: every critical and recommended check is present.

## Critical checks

v1 evaluates:

- startup name;
- startup stage;
- incorporation date;
- explicit DPIIT-recognition status;
- eligibility entity context.

A normal startup profile may omit an entity override because the existing
eligibility engine defaults it to `startup`. An AIF override must include
usable regulatory registration data and a SEBI registration to be ready
for the current AIF-only pilot rule.

## Recommended checks

v1 evaluates:

- legal name;
- startup description;
- incorporation type;
- state and district;
- sectors;
- explicit Udyam-registration status;
- turnover, revenue stage, and team size;
- funding amount and purpose.

## Score

Outcome factors are deterministic:

- present: 1.0;
- incomplete: 0.5;
- missing or invalid: 0.0.

Critical checks contribute 70 percent of the final score. Recommended
checks contribute 30 percent. Category and final scores use decimal
round-half-up behavior and are returned as integers from 0 to 100.

A high score does not override a critical blocker. Status is determined
from critical outcomes first.

## Output

`evaluate_startup_readiness()` returns an immutable evaluation containing:

- overall status and score;
- critical and recommended category scores;
- ordered findings with reasons and actions;
- blocking findings;
- deterministic summary;
- engine version `startup-readiness-v1`.
