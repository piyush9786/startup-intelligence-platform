# Persisted Recommendation Generation Runs v1

## Purpose

A recommendation generation is now stored independently of its current
recommendation rows. This distinguishes:

- a profile that has never generated recommendations;
- a completed generation with zero recommendations;
- a completed generation with one or more recommendations.

## Run metadata

Each run stores:

- startup profile and requesting user;
- assessment date and ranking version;
- immutable startup-profile snapshot;
- assessed-scheme and recommendation counts;
- excluded-scheme details;
- a recommendation output snapshot;
- completion time;
- whether the run is the current run for the profile.

Only one run may be current for a startup profile.

## Assessments and recommendations

Eligibility assessments created during generation link to the run.
Standalone eligibility assessments may have no generation run.

Current recommendation rows also link to the run. The existing
`generation_id` and `ranking_version` columns remain as compatibility
snapshots and are validated against the authoritative run.

When a new generation succeeds, the previous run remains available for
audit, including its recommendation snapshot. Current recommendation rows
continue to be replaced atomically.

## Retrieval behavior

The current-recommendations endpoint now reads the current run first.

A completed zero-result run returns:

```json
{
  "has_generation": true,
  "assessed_scheme_count": 1,
  "recommendation_count": 0,
  "recommendations": []
}
```

A profile with no run returns `has_generation: false`.

The endpoint returns HTTP 409 when current recommendation rows disagree
with their authoritative run metadata.
