# First-Open Founder Onboarding Tour V1

## Purpose

The first-open onboarding tour gives founders a short orientation before they
use the startup-support workspace.

It is a deterministic product workflow. It is not an autonomous agent and does
not make readiness, eligibility, ranking, verification, funding, deadline, or
sequencing decisions.

Contract version:

```text
founder-onboarding-v1
```

## User variants

The initial variant is selected when the owner-scoped progress record is first
created.

### `empty_profile`

Used when the founder has no startup profile.

The final action completes the tour and opens the existing startup assessment
wizard with an onboarding assessment draft.

### `returning_founder`

Used when the founder already owns at least one startup profile.

The tour introduces the existing startup, recommendations, requirements,
roadmap, and founder-advisor surfaces.

The selected variant remains persisted. It is not silently changed on later
loads.

## Persisted model

`OnboardingProgress` is stored in PostgreSQL and has a one-to-one relationship
with the authenticated user.

Important fields:

| Field | Meaning |
| --- | --- |
| `owner` | Authenticated owner of the progress record |
| `tour_version` | Versioned onboarding contract |
| `variant` | Empty-profile or returning-founder experience |
| `status` | Active, dismissed, or completed |
| `current_step` | Persisted step from 1 through 4 |
| `started_at` | Initial creation time |
| `dismissed_at` | Most recent dismissal time |
| `completed_at` | Immutable completion time for the current contract |

The database constrains `current_step` to the supported range.

Only one onboarding progress record may exist per user.

## Status lifecycle

```text
first authenticated founder load
          │
          ▼
        active
       /      \
      ▼        ▼
 dismissed   completed
      │
      ▼
    active
```

Rules:

- `set_step` keeps the tour active and persists the selected step;
- `dismiss` hides the modal but preserves the current step;
- `resume` returns dismissed progress to active;
- `complete` sets step 4 and records completion;
- completed progress does not show again;
- completed progress cannot be reopened through the v1 API.

## API

Endpoint:

```text
GET   /api/v1/startup-onboarding/current/
PATCH /api/v1/startup-onboarding/current/
```

Authentication is required.

### GET current progress

The first GET creates the owner-scoped progress record when it does not exist.

Example response:

```json
{
  "id": "uuid",
  "owner_id": "uuid",
  "tour_version": "founder-onboarding-v1",
  "variant": "empty_profile",
  "status": "active",
  "current_step": 1,
  "total_steps": 4,
  "should_show": true,
  "started_at": "2026-07-23T10:00:00Z",
  "dismissed_at": null,
  "completed_at": null,
  "created_at": "2026-07-23T10:00:00Z",
  "updated_at": "2026-07-23T10:00:00Z"
}
```

### Persist a step

```json
{
  "action": "set_step",
  "current_step": 2
}
```

### Dismiss

```json
{
  "action": "dismiss"
}
```

### Resume

```json
{
  "action": "resume"
}
```

### Complete

```json
{
  "action": "complete"
}
```

Attempting to reopen completed progress returns HTTP `409 Conflict`.

## Frontend behavior

The founder workspace loads onboarding progress only after the authenticated
identity has been resolved as a founder.

Reviewer users do not request or render founder onboarding.

Active progress renders a four-step modal.

Dismissed progress renders a resume banner containing the persisted step.

Completed progress renders neither the modal nor the resume banner.

For an empty-profile founder, completing the final step routes directly to the
existing `AssessmentWizard`.

The onboarding feature does not write startup-profile answers and does not
create an alternative profile representation.

## Accessibility

The v1 modal provides:

- `role="dialog"`;
- `aria-modal="true"`;
- labelled title and description;
- a semantic progress bar with current and total step values;
- keyboard focus movement into the dialog;
- Tab and Shift+Tab focus containment;
- Escape-key dismissal;
- visible focus treatment;
- disabled actions while persistence is in progress;
- responsive small-screen action layout;
- reduced-motion compatibility through the existing global stylesheet rule.

## Authorization and trust boundary

The API is authenticated and owner scoped.

The frontend is not treated as an authorization boundary.

Onboarding progress is product-navigation state only. It cannot:

- modify eligibility facts;
- approve founder evidence;
- change reviewer decisions;
- produce recommendation results;
- alter readiness scores;
- submit an assessment;
- bypass existing serializer validation.

## Main implementation files

Backend:

```text
backend/apps/startups/models.py
backend/apps/startups/onboarding_serializers.py
backend/apps/startups/onboarding_views.py
backend/apps/startups/services/onboarding.py
backend/apps/startups/migrations/0009_onboardingprogress.py
backend/apps/startups/tests/test_onboarding_progress_api.py
```

Frontend:

```text
frontend/src/OnboardingTour.jsx
frontend/src/App.jsx
frontend/src/api.js
frontend/src/styles.css
frontend/src/App.test.jsx
```

## Validation

Focused backend tests cover:

- authentication;
- empty-profile variant selection;
- returning-founder variant selection;
- persisted step resumption;
- dismissal and resume;
- permanent completion;
- step validation;
- owner isolation.

Frontend integration tests cover:

- persisted step changes;
- dismissal and resume;
- empty-profile completion and assessment handoff;
- reviewer exclusion.

Milestone validation:

```bash
docker compose exec -T backend pytest -q
docker compose exec -T backend ruff check .
docker compose exec -T backend python manage.py check
docker compose exec -T backend \
  python manage.py makemigrations --check --dry-run

docker compose exec -T frontend npm test
docker compose exec -T frontend npm run build

git diff --check
```

At milestone completion:

- the full backend suite passes;
- 105 frontend tests pass;
- the frontend production build passes;
- Ruff passes;
- Django system checks pass;
- no migration drift is present.
