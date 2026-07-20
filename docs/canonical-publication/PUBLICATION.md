# Deterministic canonical publication

Phase 3D.2 publishes reviewed extraction candidates into the existing
canonical `Scheme` and `SchemeVersion` models.

## Gates

A canonical publication requires:

- an authenticated reviewer, administrator, or superuser;
- candidate review status `approved`;
- a completed `canonical` resolution;
- a resolved authority and canonical title;
- an official URL;
- at least one evidence record;
- every extracted eligibility rule reviewed as `approved` or `rejected`.

A supporting publication requires a previously published primary
candidate and must match its canonical title and authority.

## Idempotency

A normalized JSON payload is hashed with SHA-256. The payload excludes
database identifiers, timestamps, evidence locations, and extraction
confidence. Re-running publication for the same candidate returns the
existing audit record without creating another version.

A changed payload creates the next numbered `SchemeVersion`. A payload
that matches a non-current historical version is blocked for manual
review rather than silently moving the current version backward.

## Audit trail

`CandidatePublication` links the reviewed candidate to the canonical
scheme and version. `PublishedEvidence` snapshots every evidence quote
and retains its protected link to the original `CandidateEvidence`.

## Eligibility rules

Only approved rule candidates become canonical `EligibilityRule`
records. Candidate operators are mapped explicitly to the canonical
operator vocabulary. Canonical rules are marked manually verified.

## Curation gate

Canonical publication requires an approved `CandidateCuration`.
The curated summary, objective, eligibility statement, official URL,
and application URL replace the raw extraction fields in the published
version.

Benefits, required documents, and application steps must each be
explicitly approved or rejected. Draft structured items block canonical
publication, and rejected items are excluded from the version payload.


## Curated structured replacements

Candidate curation may provide reviewed replacements for support
types, categories, benefits, required documents, and application
steps.

A null replacement preserves the approved extracted rows. An empty
list records an explicit reviewed decision that the canonical version
should contain no rows for that field. Non-empty replacements take
precedence over approved extraction rows and participate in the
deterministic publication hash.
