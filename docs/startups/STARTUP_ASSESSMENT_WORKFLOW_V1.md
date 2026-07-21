# Startup Assessment Workflow v1

## Scope

Phase 4G.3B.1 adds the persisted backend workflow used by the founder
assessment wizard.

The workflow supports:

- authenticated assessment drafts;
- optional linkage to an existing startup profile;
- profile prefill when a draft is linked;
- incremental draft updates with step tracking;
- owner-scoped retrieval;
- transactional submission;
- startup-profile creation or update;
- readiness-assessment generation;
- readiness action-plan generation;
- recommendation generation;
- immutable submission profile snapshots.

## Draft endpoints

```text
GET    /api/v1/startup-assessment-drafts/
POST   /api/v1/startup-assessment-drafts/
GET    /api/v1/startup-assessment-drafts/{draft_id}/
PATCH  /api/v1/startup-assessment-drafts/{draft_id}/
POST   /api/v1/startup-assessment-drafts/{draft_id}/submit/
```

Draft list requests can filter by `status` and `startup_profile`.

## Ownership

Non-staff users can access only drafts they own and can link drafts only to
startup profiles they own. Cross-user access returns `404` or validation
errors without exposing another founder's data.

## Submission

Submission validates the draft, creates or updates the linked startup profile,
then creates the readiness assessment, action plan, and recommendation
generation in one database transaction.

A failed downstream operation rolls back the profile and draft state.

A submitted draft cannot be submitted again.

## Assessment data

Direct startup-profile fields are stored on `StartupProfile`. Additional
founder, business, team, funding, and resource fields are stored in
`StartupProfile.profile_data` so they remain available to eligibility and
future guidance workflows without creating duplicate profile models.

## Frontend follow-up

Phase 4G.3B.2 will add the eight-step React wizard, autosave behavior,
save-and-exit controls, review screen, submission progress, and dashboard
redirect.
