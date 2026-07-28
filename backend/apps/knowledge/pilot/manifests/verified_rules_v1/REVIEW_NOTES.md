# Verified executable rules pilot v1

This manifest creates immutable verified scheme versions only for the catalog-pilot schemes that can be partially automated safely with the current startup profile model. It never edits version 1 in place.

## Applied revisions

- **BIG:** executable startup/individual-entrepreneur gate; incubator association remains manual.
- **NIDHI-SSP:** executable startup gate; Indian company registration, incubator association, validated USP, foreign-subsidiary status, and Indian promoter shareholding remain manual.
- DPIIT recognition is not encoded as mandatory for NIDHI-SSP because the verified curated eligibility describes it as preferred, not mandatory.

## Deferred schemes

- **ASPIRE:** remains manual because the applicant is an implementing organisation and the current startup-facing entity model cannot represent its alternatives reliably without risking false exclusions.
- **NIDHI-EIR:** remains manual because eligibility belongs to an individual entrepreneur and depends on citizenship, education or experience, full-time commitment, remuneration, and TBI registration.

## Evaluation behavior

Engine `rules-v4` evaluates conclusive mandatory failures before manual verification gates. This permits safe fail-fast exclusion while preventing unsupported criteria from producing a false eligible result.
