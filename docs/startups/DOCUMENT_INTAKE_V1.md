# AI Startup Document Intake V1 — Phase 52

## Purpose

The AI Startup Document Intake workspace (`DocumentIntakeWorkspace.jsx`) allows founders to upload pitch decks, executive summaries, incorporation certificates, and Udyam MSME registration PDFs or text documents. It extracts structured startup facts, computes confidence scores, preserves page-level evidence provenance, detects profile conflicts, and allows founders to review and confirm facts before updating their profile.

## Key Features

1. **Document Parsing & Classification**:
   - Accepts PDF and TXT documents up to 10MB.
   - Supports auto-detection or founder hint selection for document types:
     - `incorporation_certificate`
     - `udyam_registration`
     - `pitch_deck`
2. **Fact Extraction Scope**:
   - `startup_name`, `legal_name`, `incorporation_type`, `incorporation_date`
   - `udyam_registered`, `regulatory_registrations` (CIN, LLPIN, Udyam)
   - `state`, `district`
   - `sectors`, `technologies`
   - `funding_required`, `team_size`
3. **Confidence Scoring & Provenance**:
   - Assigns confidence percentages (e.g. 96% High, 85% Medium).
   - Preserves exact page numbers, section headings, and text excerpts for evidence provenance.
4. **Conflict Flagging & Confirmation Workflow**:
   - Compares extracted values against existing saved profile values, highlighting conflicts.
   - Provides "Select High Confidence (85%+)" bulk shortcut and individual checkbox toggles.
   - Saves only founder-confirmed suggestions to `StartupProfile` with fields tagged under `autofilled_fields`.

## Verification & Validation

- Backend API tests in `apps/startups/tests/test_startup_document_autofill_api.py` (525 total backend tests passing).
- Frontend Vitest suite in `DocumentIntakeWorkspace.test.jsx` (153 total frontend tests passing).
- Production bundle build (`npm run build`) passing.
- Ruff linting, Django system checks, and zero migration drift.
