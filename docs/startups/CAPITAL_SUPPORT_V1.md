# Capital & Loan Support Workspace V1 — Phase 57

## Purpose

The Capital & Loan Support Workspace (`capitalSupportEngine.js` & `FundingPage.jsx`) provides founders with a structured financial intelligence platform for discovering, evaluating, and comparing grant funding, working capital loans, debt credit facilities, and equity instruments.

## Key Features

1. **Capital Type Filter Tabs**:
   - **All funding**: Complete overview of verified schemes and external capital support references.
   - **Loans & credit**: Debt facilities, collateral-free credit schemes (CGTMSE), working capital lines.
   - **Grants and other support**: Equity-free seed grants, prototyping subsidies, and R&D grants.
2. **Verified Platform Funding Cards**:
   - Published grant/loan support amount range (₹).
   - Interest rate range indicators (e.g. 7.5% - 9.5% per annum for loan facilities).
   - Equity requirement indicators (`Yes` / `No` / `Not published`).
   - Direct eligibility inspection trigger (`Review eligibility and apply`).
3. **External Capital Support Discovery Dataset**:
   - External discovery records with provenance badges (`External dataset`, `Needs review`).
   - Published reference amounts, collateral & repayment terms, and official lender portal links (e.g. SIDBI, NCGTC, MUDRA).

## Verification & Validation

- 525 backend pytest tests passing.
- 175 frontend Vitest tests across 36 test files passing.
- Production bundle build (`npm run build`) passing in 1.86s.
- Ruff linting, Django system checks, and zero migration drift.
