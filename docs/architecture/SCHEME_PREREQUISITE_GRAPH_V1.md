# Verified Scheme Prerequisite Graph v1

## Status

Phase 48 is implemented.

The `scheme-prerequisite-graph-v1` contract represents reviewed prerequisite
concepts, scheme requirements, and scheme unlock relationships without changing
the ordering of the Phase 47 starting plan.

PostgreSQL remains authoritative. Neo4j is a rebuildable derived projection.

## Purpose

The graph provides verified dependency data for the future deterministic
funding-plan engine.

It supports:

- canonical prerequisite concepts;
- multiple prerequisites per scheme version;
- multiple predecessor schemes for one unlocked scheme;
- hard and supporting prerequisite classifications;
- official-source evidence for concepts and relationships;
- explicit reviewer provenance;
- automatically extracted candidate relationships that remain
  non-authoritative until reviewed;
- cycle rejection for authoritative unlock relationships;
- deterministic PostgreSQL snapshots;
- canonical SHA-256 projection hashes;
- rebuildable Neo4j projection;
- PostgreSQL-to-Neo4j consistency checks.

Phase 48 does not reorder founder plans. Dependency-aware ordering belongs to
Phase 49.

## Authoritative PostgreSQL records

### `PrerequisiteConcept`

A prerequisite concept represents a reusable verified requirement such as a
registration, certification, compliance condition, financial-readiness
condition, operational condition, or scheme-access requirement.

Verified concepts require:

- an official `SourceDocument`;
- source evidence text;
- a reviewer;
- a review timestamp.

### `SchemePrerequisite`

A scheme-prerequisite relationship connects a specific verified
`SchemeVersion` to a verified `PrerequisiteConcept`.

Relationship types are:

- `hard`;
- `supporting`.

Every authoritative relationship retains:

- origin;
- review status;
- official source document;
- evidence text and optional page;
- review notes;
- reviewer and review timestamp;
- structured metadata.

### `SchemeUnlock`

A scheme-unlock relationship connects a predecessor scheme version to an
unlocked scheme version.

The schema supports multiple predecessors for one scheme. It does not use a
single nullable `depends_on` field.

Verified unlocks require verified scheme versions and complete source and review
provenance.

Self-dependencies and directed cycles are rejected before an authoritative edge
can be saved.

### Candidate relationships

Origins include:

- `manual`;
- `extracted`;
- `imported`.

Extracted or imported relationships may be stored with `review_required`
status, but only `verified` records are included in the authoritative graph
snapshot and Neo4j projection.

## Save-time integrity

Verified prerequisite concepts and reviewed relationships run model validation
during normal saves.

Verified unlock saves also evaluate the complete authoritative unlock graph.
This prevents ordinary Django admin and application writes from bypassing cycle
validation.

Database uniqueness constraints prevent duplicate:

- scheme-version/prerequisite pairs;
- predecessor-version/unlocked-version pairs.

## Deterministic snapshot

`build_scheme_graph_snapshot()` produces a canonical representation containing:

- verified scheme-version nodes;
- verified prerequisite nodes;
- verified scheme-prerequisite edges;
- verified scheme-unlock edges;
- source and reviewer provenance.

Records are ordered deterministically, serialized as canonical JSON, and hashed
with SHA-256.

Any change to authoritative nodes, relationships, or evidence changes the source
hash.

## Neo4j projection

Neo4j contains only derived records for the versioned graph:

- `SIPSchemeVersion` nodes;
- `SIPPrerequisite` nodes;
- `SIP_REQUIRES_PREREQUISITE` relationships;
- `SIP_UNLOCKS_SCHEME` relationships;
- one `SIPGraphProjection` metadata node.

Every projected node and relationship includes:

- `graph_version`;
- projection source hash;
- canonical PostgreSQL identifier;
- relevant source and review provenance.

A rebuild replaces only records belonging to
`scheme-prerequisite-graph-v1`. PostgreSQL records are never changed by the
projection operation.

## Rebuild concurrency

The rebuild service uses a PostgreSQL advisory lock.

Only one Phase 48 graph rebuild may execute at a time. A concurrent command
fails explicitly instead of interleaving Neo4j replacement operations.

## Projection run audit

Each rebuild creates a `SchemeGraphProjectionRun` record containing:

- graph version;
- status;
- source hash;
- expected node and edge counts;
- start and finish timestamps;
- failure information when applicable.

## Operations

Apply database migrations:

```bash
docker compose exec -T backend \
  python manage.py migrate schemes
Rebuild Neo4j from authoritative PostgreSQL records:
docker compose exec -T backend \
  python manage.py rebuild_scheme_graph
Check consistency without changing Neo4j:
docker compose exec -T backend \
  python manage.py rebuild_scheme_graph --check
The consistency check compares:

graph version;
canonical source hash;
scheme-version node count and identifiers;
prerequisite node count and identifiers;
prerequisite-edge count and identifiers;
unlock-edge count and identifiers;
projection metadata cardinality.

Any mismatch causes the command to fail.

Current pilot projection

At Phase 48 completion, the local verified catalog projects:

9 verified scheme-version nodes;
0 verified prerequisite nodes;
0 verified scheme-prerequisite edges;
0 verified unlock edges.

The empty relationship sets are valid. They show that the graph infrastructure
is operational while authoritative prerequisite review coverage is still to be
added.

Trust boundary

PostgreSQL is authoritative.

Neo4j must not:

create authoritative relationships;
promote extracted candidates;
override review status;
change scheme versions;
reorder founder plans;
become the source for eligibility or recommendation decisions.

Language models may help extract candidate relationships or explain a
deterministically generated plan, but they may not approve graph edges or choose
dependency ordering.

Validation

Phase 48 was validated with:

10 focused graph tests;
the complete 489-test backend suite;
130 frontend tests across 21 files;
the frontend production build;
Ruff;
Django system checks;
zero migration drift;
Docker Compose configuration validation;
warning-free live Neo4j rebuild and consistency checks;
git diff --check.
Next phase

Phase 49 will consume verified graph data in a deterministic funding-plan
engine.

Ordering must consider hard dependencies, application windows, sourced
processing times, founder urgency, funding relevance, and steps that can run in
parallel. The language model may narrate the resulting plan but may not choose
its ordering.
