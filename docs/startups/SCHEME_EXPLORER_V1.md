# Direct Scheme Matching Engine & Discovery Explorer V1 — Phase 55

## Purpose

The Direct Scheme Matching Engine & Discovery Explorer workspace (`SchemeExplorerPage.jsx` & `SchemeDetailPage.jsx`) provides founders with a multi-faceted search experience for discovering verified government schemes, grants, working capital loans, tax exemptions, and incubation programmes.

## Key Features

1. **Multi-Facet Discovery Filters**:
   - **Sector**: Filter by BioTech, CleanTech, FinTech, AgriTech, DeepTech, HealthTech, EdTech, AI & Software, Manufacturing.
   - **Stage**: Ideation, Validation, Early Revenue, Scaling.
   - **Location / State**: All India, Karnataka, Maharashtra, Delhi, Tamil Nadu, Telangana, Gujarat, Uttar Pradesh.
   - **Support Type**: Grants, Loans, Tax Exemptions, Incubation.
2. **Catalog Review & Source Transparency**:
   - **Available & Reviewed**: Recommendation-ready verified schemes and reviewed external programmes.
   - **Needs Review**: External records awaiting reviewer validation.
   - **Merged Records**: Source aliases pointing to canonical platform schemes.
   - **Unavailable Records**: Retained historical records for catalog transparency.
3. **Ranked Scheme Match Cards**:
   - Ranked match percentage pills (`95% Match`), rank badges (`Rank #1`), authority tags, support types, maximum amount (₹), and current application status.
4. **Standalone Scheme Detail & Official Portal Launcher**:
   - Structured eligibility rules, required documents & certificates list, scheme benefits, and step-by-step application instructions.
   - Direct **"Launch Official Application Portal ↗"** button linking to verified government portals.

## Verification & Validation

- 525 backend pytest tests passing.
- 165 frontend Vitest tests across 32 test files passing.
- Production bundle build (`npm run build`) passing in 1.84s.
- Ruff linting, Django system checks, and zero migration drift.
