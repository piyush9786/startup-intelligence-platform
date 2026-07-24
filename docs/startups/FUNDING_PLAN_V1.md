# Deterministic Dependency-Aware Funding Plan v1

## Status

Phase 49 is implemented.

The versioned contract is:

```text
startup-funding-plan-v1
```

The funding plan produces an immutable, founder-owned sequence of readiness,
prerequisite, dependency-review, and verified scheme steps.

The plan is algorithmic. A language model may explain a persisted result but
does not select, modify, or override the ordering.

## Purpose

The Phase 47 starting plan intentionally preserved readiness priority and
recommendation rank without claiming prerequisite ordering.

Phase 49 consumes that persisted starting plan together with reviewed Phase 48
graph relationships and produces a dependency-aware execution plan.

The engine considers:

- hard prerequisite dependencies;
- supporting relationships;
- verified application windows;
- sourced processing-time ranges;
- founder urgency;
- funding relevance;
- steps that may execute in parallel;
- multiple predecessors for one step.

## Authoritative sources

PostgreSQL remains authoritative.

The source adapter reads:

- one persisted `StartupStartingPlan`;
- verified canonical `SchemeVersion` records;
- verified `SchemeUnlock` relationships;
- verified `SchemePrerequisite` relationships;
- verified prerequisite concepts;
- official source-document provenance.

Neo4j is not used as an authoritative planning input. Its Phase 48 projection is
derived and rebuildable.

Extracted, imported, pending, or otherwise unreviewed graph relationships do not
affect the funding plan.

## Source adapter

The adapter converts authoritative records into pure engine inputs.

It includes:

- readiness items from the persisted starting plan;
- recommended schemes only when their current source version is verified;
- backward closure over verified scheme-unlock relationships;
- verified prerequisite steps;
- review-only dependency-scheme steps where an unlock predecessor is outside
  the starting plan;
- hard and supporting relationship classifications;
- processing-time ranges only when strict verified metadata contains a matching
  source-document identifier.

The adapter does not infer missing processing times, application dates, graph
relationships, or prerequisite classifications.

## Deterministic ordering

The pure engine validates:

- unique step identifiers;
- valid dependency endpoints;
- supported dependency types;
- non-negative urgency and relevance values;
- valid application dates;
- valid processing-time ranges;
- absence of directed cycles.

Hard dependencies block successor steps.

Supporting dependencies are retained as provenance but do not block execution.

Ready work is ordered deterministically using persisted status and verified
fields, including:

1. actionable application-window status;
2. verified deadline;
3. founder urgency;
4. funding relevance;
5. verified opening date;
6. source position;
7. stable step identifier.

The engine uses deterministic Kahn execution waves.

Independent work may appear in the same execution wave. Urgent work marked as
non-parallel is isolated into its own execution group.

The output includes:

- normalized ordered steps;
- normalized dependencies;
- execution waves;
- current next-step identifiers;
- total step and dependency counts;
- the engine version.

## Persistence

`StartupFundingPlan` stores:

- founder and startup ownership;
- the exact source starting plan;
- explicit `as_of_date`;
- canonical source snapshot;
- SHA-256 source hash;
- immutable plan snapshot;
- step, dependency, and execution-wave counts;
- current next-step identifiers;
- planner version;
- current and historical state;
- creation provenance.

The exact-source identity is:

```text
source_starting_plan
+ as_of_date
+ source_hash
+ plan_version
```

Generating from the same exact source identity is idempotent.

A changed verified graph, changed verified source data, or changed planning date
creates a new immutable plan and supersedes the previous current plan.

Unreviewed graph changes do not change the authoritative source hash.

Only one funding plan may be current for a startup.

Historical plan snapshots and source references are immutable.

## Founder API

Authenticated founder-owned endpoints:

```text
POST /api/v1/startup-funding-plans/generate/
GET  /api/v1/startup-funding-plans/current/
GET  /api/v1/startup-funding-plans/
GET  /api/v1/startup-funding-plans/<funding_plan_id>/
```

Generation accepts:

```json
{
  "startup_profile_id": "uuid",
  "as_of_date": "YYYY-MM-DD"
}
```

`as_of_date` is optional.

The API rejects browser-supplied steps, dependencies, graph data, ordering, and
starting-plan snapshots. These inputs are resolved by the backend from
authoritative records.

Founder ownership is enforced by backend query scope. Cross-founder current,
history, and detail access is not disclosed.

Generation returns:

- `201 Created` for a newly persisted source identity;
- `200 OK` for an idempotent existing plan.

## Founder workspace

The founder dashboard includes a dedicated Funding plan workspace.

It displays:

- total steps;
- verified dependency count;
- execution-wave count;
- plan version;
- ordered execution waves;
- parallel-work guidance;
- hard and supporting predecessors;
- verified application status and deadlines;
- sourced processing-time ranges;
- immutable starting-plan and source-hash provenance;
- saved plan-version count.

The original Phase 47 Starting plan workspace remains unchanged and continues
to represent its historical contract.

The site-wide founder assistant receives `funding-plan` as page context when the
workspace is open, but that context is not an authorization or ordering input.

## Trust boundary

The funding planner does not:

- use an LLM to choose ordering;
- treat founder-reported completion as verified;
- infer missing official deadlines;
- infer missing processing times;
- use unreviewed graph candidates;
- accept client-authored plan topology;
- treat Neo4j as authoritative;
- mutate previous plan snapshots;
- change eligibility or recommendation outcomes.

## Validation

Phase 49 validation completed with:

- 518 backend tests;
- 141 frontend tests across 23 files;
- Ruff passing;
- Django system checks passing;
- zero migration drift;
- migration `0011_startup_funding_plan` applied;
- frontend production build passing;
- Docker Compose configuration validation passing;
- repository whitespace checks passing.

## Next phase

Phase 50 adds founder progress feedback with explicit states such as:

```text
not_started
in_progress
founder_reported_complete
evidence_submitted
verified
```

Founder-reported completion must not automatically become an authoritative
eligibility or prerequisite fact.
