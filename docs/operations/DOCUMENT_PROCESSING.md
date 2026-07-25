# Phase 2: extraction, normalization, and chunking

## Flow

1. A current `SourceDocument` points to immutable raw bytes in MinIO.
2. The processor downloads those bytes from the raw bucket.
3. A MIME-specific extractor handles HTML, PDF, JSON, CSV, or plain text.
4. Unicode and whitespace are normalized deterministically.
5. Normalized text is written to the processed MinIO bucket.
6. Heading-aware or page-aware chunks are created in PostgreSQL.
7. Every extraction is tied to an explicit extractor version.
8. Re-running the same version is idempotent unless `--force` is used.

## Commands

```bash
python manage.py process_documents --all-current --limit 10
python manage.py process_documents --source-domain startupindia.gov.in
python manage.py process_documents --document-id <uuid>
python manage.py process_documents --all-current --enqueue
```

## Current limits

Image-only PDFs are marked failed with an OCR-required message. OCR is kept
out of this phase because it is expensive and should run only on documents
positively identified as scanned or image-only.
