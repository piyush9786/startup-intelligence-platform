# Verified rule revisions

`apply_verified_rule_manifest` creates new verified `SchemeVersion` rows from reviewed JSON manifests. Existing verified versions and candidate publication records remain immutable.

## Safety properties

- Dry-run is the default.
- Every revision is anchored to an exact primary publication, scheme, current version ID, version number, and content hash.
- `executable` rules are limited to field paths supported by the deterministic eligibility engine.
- `manual_verification` rules require the explicit `manual_verification.` namespace and produce a verification gate.
- Applying the same manifest again is count-idempotent.
- A `VerifiedRuleRevision` record preserves the manifest hash, reviewer, base version, and revised version.

## Commands

```bash
python manage.py apply_verified_rule_manifest \
  --reviewer-email reviewer@example.com
```

Apply only after reviewing the dry-run:

```bash
python manage.py apply_verified_rule_manifest \
  --reviewer-email reviewer@example.com \
  --apply
```

## Result precedence

Eligibility engine `rules-v4` uses this order:

1. application closed;
2. conclusive mandatory failure;
3. manual or unsupported verification gate;
4. missing mandatory information;
5. eligible.
