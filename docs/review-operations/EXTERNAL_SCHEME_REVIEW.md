# External scheme review

The spreadsheet-derived scheme dataset is review staging, not a canonical
eligibility source. Importing it never verifies records automatically.

The versioned manifest at
`backend/apps/knowledge/pilot/manifests/external_scheme_review_v1.json`
contains one decision for every imported record. Each decision records an
official HTTPS source, a rationale, optional corrected fields, and an optional
match to an already-published canonical scheme.

Run the workflow in this order:

```bash
python manage.py import_external_schemes
python manage.py review_external_schemes --check
python manage.py review_external_schemes
```

The review command fails unless the manifest covers the imported dataset
exactly. It is idempotent and does not create or publish canonical schemes.

- `verified` means the external programme or support service was confirmed
  against the cited official source. It remains discovery-only.
- `rejected` quarantines ended, unsupported, misleading, or out-of-scope rows.
- `matched_scheme_name` links a duplicate staging row to an existing canonical
  scheme, causing the external duplicate to be excluded from the public list.

Official-source review does not imply that a call is currently open. Users must
confirm live dates and terms on the linked authority page before applying.
