# Current Recommendation Retrieval API v1

`GET /api/v1/recommendations/current/`

Required query parameter:

```text
startup_profile_id=<profile UUID>
```

Authentication is required. Non-staff users may retrieve only profiles
they own; staff users may retrieve any stored profile.

The endpoint performs no writes. It returns the currently persisted
recommendation rows ordered by stored rank, including generation ID,
ranking version, assessment date, generated timestamp, score breakdowns,
and evidence snapshots.

A valid set must share one generation ID, one ranking version, and one
assessment date, with contiguous ranks beginning at one. An inconsistent
set returns HTTP 409.

A profile with no recommendation rows returns HTTP 200 with
`has_generation=false`, null generation metadata, and an empty list.

In v1, generation metadata lives on recommendation rows. A generation that
produced zero rows is therefore indistinguishable from no generation. A
dedicated generation-run model can separate those states in a later phase.
