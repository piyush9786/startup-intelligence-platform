# Startup Assessment Wizard v1

Phase 4G.3B.2 connects the founder dashboard to the persisted assessment-draft
workflow.

## User experience

A founder with no startup profile is no longer sent to Django admin as the
primary path. The dashboard presents a **Start startup assessment** action that
opens an eight-step founder workflow.

The same workflow is available from the sidebar for existing profiles so a
founder can update the evidence used by readiness, eligibility,
recommendations, roadmap generation and founder guidance.

## Steps

1. Startup basics
2. Founder
3. Registration
4. Market
5. Business
6. Team
7. Funding
8. Support needs and review

## Persistence

The wizard:

- resumes the current account's open draft;
- creates a draft when none exists;
- saves answers with PATCH requests;
- records the current step;
- supports save-and-exit;
- submits through the transactional assessment endpoint.

Successful submission immediately hydrates the dashboard with the returned
startup profile, readiness assessment, action plan and recommendations.

## Trust boundary

The interface does not invent scheme eligibility, funding values,
certification requirements, mentor appointments or guidance. Those views use
persisted backend results produced after the founder submits their evidence.
