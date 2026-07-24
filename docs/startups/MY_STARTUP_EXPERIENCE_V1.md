# Structured My Startup Experience V1 — Phase 51

## Purpose

The Structured My Startup Experience replaces simple profile snapshot panels with a structured founder workspace that organizes all company facts, founder background, market positioning, technology stack, financial traction, capital planning, regulatory compliance, and verified evidence into 9 domain sections.

It provides deterministic completeness scoring, human-readable formatting, purposeful empty states, source provenance badges (`Verified`, `Founder Claim`, `Extracted`), and direct section editing capabilities.

## Domain Sections

The 9 structured domain sections:

1. **Company Overview**: Startup Name, Legal Name, Description, Stage, Entity Type, Incorporation Date, State, District.
2. **Founder Information**: Founder Categories (Woman-led, SC/ST, Student), Primary Founder Gender.
3. **Market & Customers**: Industry Sectors, Target Market, Problem Definition.
4. **Product & Technology**: Core Technologies, Product Stage, IP & Patents.
5. **Traction & Revenue**: Revenue Stage, Annual Turnover, Current Monthly Revenue.
6. **Team & Management**: Headcount, Full-time Founders, Key Positions.
7. **Funding & Capital**: Funding Requirement, Funding Purpose, Prior Capital Raised.
8. **Compliance & Registrations**: DPIIT Recognition, Udyam MSME Registration, GSTIN, PAN / CIN.
9. **Documents & Verified Evidence**: Pitch Deck / PDF uploads, Incorporation Certificate, Reviewer Verification Decisions.

## Completeness & Provenance Policy

- **Completeness Metric**: Calculated deterministically via `calculateProfileCompleteness()` across required and recommended profile fields.
- **Source Badges**:
  - `✓ Verified`: Reviewer-approved eligibility evidence (green badge).
  - `✦ Extracted`: Auto-filled from pitch deck or uploaded document (blue badge).
  - `Founder Claim`: Self-reported founder profile attribute (neutral badge).
- **Section Guidance**: Purposeful empty states explain which government schemes, tax exemptions, or readiness gates are unlocked by filling missing fields.
- **Section Editing**: Direct modal editing updates `StartupProfile` model fields and `profile_data` via DRF `PATCH` endpoints with full ownership validation.

## Verification & Validation

- 2 new backend profile API tests in `apps/startups/tests/test_startup_profile_api.py` (524 total backend tests passing).
- 5 new utility tests in `profileCompleteness.test.js` and 2 new component tests in `MyStartupPage.test.jsx` (151 total frontend tests passing).
- Frontend production bundle build (`npm run build`) passing.
- Ruff linting, Django system checks, and zero migration drift.
