# Deterministic Startup Readiness Action Plan v1

## Purpose

The action-plan service converts a deterministic readiness evaluation into
an ordered remediation plan. It consumes the structured findings produced
by `evaluate_startup_readiness` and does not inspect or modify the startup
profile directly.

## Public API

```python
from apps.startups.services import (
    build_startup_readiness_action_plan,
)

plan = build_startup_readiness_action_plan(
    evaluation=evaluation,
)
payload = plan.to_dict()
```

## Ordering

Findings whose outcome is `present` are excluded.

Remaining findings are ordered deterministically by:

1. critical priority before recommended priority;
2. invalid before missing before incomplete;
3. original readiness-engine order as the final tie-breaker.

Each action item receives a one-based `position`.

## Output

The plan exposes:

- the source readiness status;
- whether any action is required;
- critical blocker count;
- recommended-improvement count;
- total action count;
- the first ordered action as `next_action`;
- complete ordered action items;
- source readiness-engine version;
- action-plan version.

Each item retains the finding code, field path, priority, outcome, reason,
action, and JSON-ready actual value.

## Determinism and boundaries

The same readiness evaluation always produces the same action plan. The
service performs no database reads or writes, calls no external service,
uses no LLM, exposes no API endpoint, and requires no migration.

Version identifier:

```text
startup-readiness-action-plan-v1
```
