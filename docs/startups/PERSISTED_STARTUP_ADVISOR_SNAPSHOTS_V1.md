# Persisted Startup Advisor Snapshots v1

## Endpoint

```text
POST /api/v1/startup-advisor/snapshots/generate/
```

Request:

```json
{
  "startup_profile_id": "<uuid>"
}
```

Raw profile, readiness, action-plan, recommendation, or generation
payloads are rejected. The server assembles the snapshot only from
persisted records.

## Persisted record

Each `StartupAdvisorSnapshot` stores:

- the requesting user;
- the startup profile;
- an immutable startup-profile snapshot;
- the newest persisted readiness assessment, when available;
- the newest persisted readiness action plan, when available;
- the current persisted recommendation generation, when available;
- the persisted recommendation rows for that generation;
- availability flags and source-record relationships;
- the recommendation count;
- `startup-advisor-snapshot-v1` as the snapshot version.

The readiness assessment and action plan are selected independently. An
action plan may therefore reference an older assessment than the newest
readiness assessment.

## Empty guidance

A startup profile does not need existing guidance before a snapshot is
created. Missing sections are persisted explicitly:

- the source relationship is null;
- the availability flag is false;
- the section snapshot is an empty object or list;
- the recommendation count is zero when no generation exists.

A completed recommendation generation that produced zero recommendations
remains available: its generation flag is true, its generation snapshot
is present, and its recommendation list is empty.

## Integrity and concurrency

Snapshot creation locks the startup profile while selecting current
sources. This serializes advisor and recommendation generation operations
that use the same profile lock.

Current recommendation rows are validated against their generation run.
An inconsistent current set returns HTTP 409 and no advisor snapshot is
written.

## History and immutability

Snapshot generation always creates a new row. Older snapshots are retained
and their JSON payloads are not rebuilt when source records later change.

Source relationships use protected deletion so identifiers remain
available for persisted snapshots.

## Authorization

Authentication is required.

Non-staff users may generate snapshots only for startup profiles they own.
Staff users may generate snapshots for any startup profile. Unknown or
inaccessible profiles return HTTP 404.

## Boundaries

The operation writes only the `StartupAdvisorSnapshot` row. It does not:

- evaluate startup readiness;
- generate a readiness action plan;
- generate recommendations;
- update source guidance records;
- invoke an LLM.
