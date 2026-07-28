# Phase 3A: Structured Knowledge Extraction

This phase converts quality-approved document chunks into reviewable
startup-support candidates. It does not publish unreviewed records into
the canonical scheme tables.

## Pipeline

1. Read a successful, quality-approved `DocumentExtraction`.
2. Detect individual scheme/program/fund boundaries.
3. Classify section text into eligibility, benefits, application steps,
   required documents, objectives, and authority information.
4. Parse common monetary amounts and deterministic eligibility rules.
5. Attach exact source chunks and page numbers as evidence.
6. Store every result as a `SchemeCandidate` with `needs_review` status.
7. Review candidates in Django admin before canonical publication.

## Safety rule

Candidate extraction is not publication. Human review remains mandatory.
A later Phase 3B publisher will map approved candidates into canonical
`Authority`, `Scheme`, `SchemeVersion`, and `EligibilityRule` records.

## Commands

```bash
python manage.py extract_knowledge --all-approved --limit 10
python manage.py extract_knowledge --document-id UUID --force
python manage.py extract_knowledge --all-approved --enqueue
```
