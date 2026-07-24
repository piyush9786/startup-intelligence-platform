# Regulatory Compliance & Certification Engine V1 — Phase 56

## Purpose

The Regulatory Compliance & Certification Engine (`complianceEngine.js` & `RequirementsPage.jsx`) provides founders with a regulatory intelligence workspace for discovering, tracking, and verifying explicit certification requirements across government authorities.

## Key Features

1. **Authority-Wise Compliance Grouping**:
   - **DPIIT & Startup India**: Recognition certificates, tax exemption eligibility (80-IAC), and angel tax provisions.
   - **FSSAI & Food Safety**: Food business operator licenses, hygiene ratings, and agricultural compliance.
   - **CDSCO & Health**: Medical device registrations, clinical trial clearances, and pharma licensing.
   - **ISO & BIS Standards**: Quality management systems (ISO 9001, ISO 27001) and Bureau of Indian Standards product marks.
   - **MCA & Corporate Governance**: Incorporation certificates, MoA/AoA filings, and RoC annual returns.
2. **Authority Filter Bar**:
   - Filter requirements and certification references by issuing authority (*All Authorities*, *DPIIT*, *FSSAI*, *CDSCO*, *ISO / BIS*, *MCA*).
3. **Verified Scheme Requirements Display**:
   - Itemized required documents list, certification evidence requirements, and mandatory/optional eligibility rules.
   - Direct link to open scheme detail page (`Open scheme →`).
4. **External Certification Dataset Provenance**:
   - Discovery records for additional regulatory certificates, applicability rules ("Who may need it"), validity and renewal periods, and official source links.

## Verification & Validation

- 525 backend pytest tests passing.
- 170 frontend Vitest tests across 34 test files passing.
- Production bundle build (`npm run build`) passing in 1.95s.
- Ruff linting, Django system checks, and zero migration drift.
