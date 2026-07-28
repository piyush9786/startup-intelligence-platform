# Dynamic Startup Assessment Wizard V1 — Phase 53

## Purpose

The Dynamic Startup Assessment Wizard (`AssessmentWizard.jsx` & `assessment.js`) provides an 8-step structured assessment experience. It supports one-click profile prefilling from the founder's *My Startup* facts, real-time step completeness tracking, live field validation, and an explicit **Lock & Submit Confirmation Modal** that transitions drafts to locked readiness assessment versions.

## Key Features

1. **8-Step Assessment Structure**:
   - Step 1: *Startup basics* (Identity, legal name, 50+ char description)
   - Step 2: *Founder* (Role, headcount, gender, categories, experience, education)
   - Step 3: *Registration* (Incorporation type, date, DPIIT recognition, Udyam MSME, regulatory IDs)
   - Step 4: *Market* (State, district, stage, sectors, technologies)
   - Step 5: *Business* (Business model, customer status, target customer, traction, revenue stage)
   - Step 6: *Team* (Team size, team roles, skills needs, incubator affiliation, mentor access)
   - Step 7: *Funding* (Capital required, preferred type, funding stage, capital raised, runway, funding purpose)
   - Step 8: *Support needs* (Certifications, compliance needs, resources, contact email, website, review summary)
2. **One-Click Profile Prefilling**:
   - `assessmentFormFromProfile(profile)` maps saved facts from `StartupProfile` and `profile_data` into the 8-step form.
3. **Step Completeness & Progress Bar**:
   - Real-time completion percentage score (`assessmentProgress(form)`).
   - Checkmark badges (✓) indicate step validity in the stepper navigation.
4. **Lock & Submit Confirmation Workflow**:
   - Presents a formal **Lock & Submit Confirmation Modal** on Step 8 review.
   - Summarizes key startup attributes across domains.
   - Explains version locking contract (`SUBMITTED`) before generating readiness scores, action roadmaps, and scheme recommendations.

## Verification & Validation

- 525 backend pytest tests passing.
- Unit tests in `assessmentProgress.test.js` and integration tests in `AssessmentWizard.test.jsx` (158 total frontend tests passing).
- Production bundle build (`npm run build`) passing in 1.84s.
- Ruff linting, Django system checks, and zero migration drift.
