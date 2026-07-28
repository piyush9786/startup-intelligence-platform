# Pilot review manifest

The pilot manifest is a version-controlled review decision record for
selected extraction candidates. The command validates every candidate,
source-document hash, eligibility-rule ID, structured-item ID, authority,
resolution, and curation payload before any database mutation.

## Dry run

Dry run is the default and performs no database writes:

```bash
python manage.py apply_pilot_manifest \
  --reviewer-email reviewer@example.com
```

## Apply

Applying requires the explicit `--apply` flag:

```bash
python manage.py apply_pilot_manifest \
  --reviewer-email reviewer@example.com \
  --apply
```

A different manifest may be supplied with `--manifest`.

The apply operation is atomic. It creates or reuses the reviewed authority,
registers verified aliases, records eligibility and structured-item review
decisions, creates the canonical candidate resolution, and stores the
approved curation payload.

The command never creates a `Scheme`, `SchemeVersion`, or
`CandidatePublication`. Publication remains a separate explicit operation.
