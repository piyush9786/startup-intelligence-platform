# Recommendation Generation History API v1

## Endpoints

List a startup profile's persisted generation runs:

```text
GET /api/v1/recommendations/runs/?startup_profile_id=<uuid>
```

Retrieve one generation run:

```text
GET /api/v1/recommendations/runs/<run_id>/
```

Authentication is required. Non-staff users may access only runs belonging to
startup profiles they own. Staff users may access any run. Unauthorized
ownership is represented as HTTP 404 to avoid exposing private resources.

## List response

Runs are ordered newest first using completion time, creation time, and run ID
as deterministic tie-breakers. Each list item includes:

- generation ID;
- startup-profile and requesting-user IDs;
- assessment date and ranking version;
- assessed, recommended, and excluded counts;
- current-run status;
- completion and creation timestamps.

A profile with no generation history returns HTTP 200 with `count: 0`.

## Detail response

The detail endpoint includes all list metadata plus the persisted:

- startup-profile snapshot;
- excluded-scheme records;
- recommendation output snapshot.

Historical output is returned from the generation run's immutable snapshots
rather than reconstructed from current recommendation rows.

## Read-only behavior

Both endpoints perform database reads only. They do not generate assessments,
recalculate rankings, modify the current run, or require a migration.
