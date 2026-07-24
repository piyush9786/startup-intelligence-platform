# Product and Engineering Roadmap

This roadmap records the agreed implementation order after verified eligibility
provenance v1 and the persisted first-open onboarding milestone.

It is directional rather than a promise of dates.

Each phase should be shipped as a focused and tested pull request.

## Completed foundation

The following major capabilities are operational:

- modular Django and React platform foundation;
- source collection, document extraction, and knowledge review;
- verified canonical scheme versions;
- deterministic startup-readiness assessment;
- deterministic eligibility and recommendation generation;
- persisted assessments, generation runs, and evidence snapshots;
- startup document autofill;
- Qdrant RAG and official evidence citations;
- grounded Ollama founder-advisor briefings;
- founder manual eligibility-verification workflow;
- reviewer verification workspace;
- concurrency-safe verification submissions;
- verified eligibility provenance in backend snapshots and founder UI;
- persisted first-open founder onboarding;
- shared agent-orchestration persistence and audit foundation;
- persistent site-wide founder chatbot.
- bounded founder concierge state machine;
- persisted consolidated deterministic starting plan.
- verified scheme-prerequisite graph with a rebuildable Neo4j projection.
- persisted deterministic dependency-aware funding plan with execution waves.
- ordered, responsive founder dashboard with accessible Motion transitions.

## Completed frontend polish: founder dashboard motion and hierarchy

Purpose: make the founder workspace easier to scan and act on without changing
the deterministic source of any displayed decision.

Implemented scope:

- reordered workspace navigation around the founder journey;
- next-best-action command center sourced from the persisted action plan;
- readiness-first progress metrics;
- separated decision and supporting-tool sections;
- responsive desktop, tablet, and mobile composition;
- Motion-powered navigation, progress, card, page, and notice transitions;
- operating-system reduced-motion support;
- `LazyMotion` bundle optimization;
- focused dashboard hierarchy coverage and full frontend validation.

See
[Founder dashboard motion and hierarchy](frontend/FOUNDER_DASHBOARD_MOTION_V1.md).

## Completed Phase 45: first-open onboarding tour

Purpose: improve the first founder experience without adding agent risk.

Implemented scope:

- owner-scoped `OnboardingProgress` persistence;
- `founder-onboarding-v1` versioning;
- empty-profile and returning-founder variants;
- active, dismissed, and completed states;
- resumable current-step persistence;
- no repeat or reopening after completion;
- direct handoff to the existing assessment wizard;
- founder-only frontend loading;
- reviewer-workspace exclusion;
- accessible modal semantics, progress reporting, keyboard focus containment,
  Escape dismissal, and responsive layout;
- focused backend API tests;
- frontend integration tests and production build validation.

See
[First-open onboarding tour](frontend/FIRST_OPEN_ONBOARDING_TOUR_V1.md).

## Completed Phase 44: site-wide founder chatbot

Purpose: provide persistent product navigation, workspace definitions, and
startup-profile-aware explanations without weakening the deterministic trust
boundary.

Implemented scope:

- founder-only persistent launcher and responsive drawer;
- authenticated global and startup-scoped chatbot sessions;
- complete persisted conversation history;
- page-aware context treated only as convenience context;
- deterministic platform-help and navigation responses;
- startup-profile explanations through the registered
  `get_startup_profile@v1` tool;
- claim references to successful tool calls and canonical output hashes;
- bounded 20-turn founder sessions;
- scoped request throttling through `assistant_chat_turn`;
- ownership enforcement and non-disclosure of other founders' profiles;
- reviewer-workspace exclusion;
- focused API, frontend, accessibility, and integration tests;
- successful full backend and frontend validation.

The chatbot remains read-only.

It does not modify startup profiles, assessment drafts, readiness findings,
eligibility results, recommendations, verification decisions, deadlines,
funding amounts, or prerequisite ordering.

See
[Site-wide founder chatbot](architecture/SITE_WIDE_CHATBOT_V1.md).

## Completed conversational foundation

## Completed Phase 43: shared agent orchestration

Purpose: establish the safety, ownership, persistence, and audit boundary once
for future conversational features.

Implemented scope:

- new `apps/assistant` Django application;
- owner-scoped `AgentSession`;
- one active session per founder, agent type, and startup scope;
- bounded founder turn counts;
- append-only `AgentMessage`;
- immutable `AgentToolCallLog`;
- structured `AgentClaimReference`;
- canonical JSON normalization and SHA-256 output hashing;
- captured authorization context;
- versioned whitelisted tool registry;
- explicit denial and logging of unregistered tools;
- explicit denial and logging of unauthorized actors;
- explicit denial of write-capable tools during Phase 43;
- initial read-only `get_startup_profile` tool;
- focused service, ownership, integrity, and audit tests.

The foundation does not yet add an LLM turn runner, public chatbot API, or
frontend chatbot.

See
[Shared agent orchestration](architecture/SHARED_AGENT_ORCHESTRATION_V1.md).

## Completed Phase 48: verified scheme-prerequisite graph

Purpose: represent prerequisites and unlock relationships with reviewed
provenance while preserving PostgreSQL as the authoritative store.

Implemented scope:

canonical prerequisite concepts;
reviewed scheme-to-prerequisite relationships;
reviewed scheme-unlock relationships;
multiple predecessors per scheme;
hard and supporting prerequisite classifications;
official-source and reviewer provenance;
non-authoritative extracted and imported candidate states;
save-time self-dependency and cycle validation;
deterministic canonical graph snapshots and SHA-256 hashes;
versioned, rebuildable Neo4j projection;
PostgreSQL advisory locking for rebuild concurrency;
persisted projection-run audit records;
PostgreSQL-to-Neo4j identifier, count, metadata, and hash consistency checks;
no Phase 47 starting-plan reordering.

See
Verified scheme prerequisite graph.

## Completed Phase 49: deterministic dependency-aware funding plan

Purpose: produce an ordered, dependency-aware funding and readiness plan without
giving an LLM authority over ordering.

Implemented scope:

- pure versioned `startup-funding-plan-v1` engine;
- validated hard and supporting dependency edges;
- multiple predecessors per step;
- cycle rejection and deterministic Kahn execution waves;
- verified application-window ordering;
- strictly sourced processing-time ranges;
- founder urgency and funding relevance ordering;
- explicit parallel-work grouping;
- Phase 47 starting-plan source adapter;
- verified Phase 48 prerequisite and unlock closure;
- exclusion of unreviewed graph candidates;
- immutable exact-source persistence with SHA-256 hashing;
- one current plan per startup and complete historical retention;
- founder-owned generate, current, history, and detail APIs;
- rejection of browser-authored topology and ordering;
- dedicated founder Funding plan workspace;
- full backend and frontend validation.

See
[Deterministic dependency-aware funding plan](startups/FUNDING_PLAN_V1.md).

## Remaining implementation order

1. Progress feedback — Phase 50

Purpose: connect plan execution back to readiness and recommendations.

Use explicit states such as:

not_started;
in_progress;
founder_reported_complete;
evidence_submitted;
verified.

Founder-reported completion must not automatically become a verified
eligibility fact.

## Parallel production-hardening track

Before public production use, complete:

- deployment environment and TLS;
- managed secrets;
- backup and restore drills;
- object-storage retention policy;
- malware scanning and stronger upload validation;
- observability, metrics, logs, and alerting;
- queue and API load testing;
- permission and penetration testing;
- disaster-recovery documentation;
- broader verified scheme coverage;
- end-to-end browser tests;
- operational reviewer audit history;
- user notifications.

## Phase completion rule

A phase is complete only when:

- its authorization boundary is defined;
- deterministic and LLM responsibilities are separated;
- persisted data has an ownership and mutability policy;
- focused and full tests pass;
- migrations are reviewed;
- API and founder-facing behavior are documented;
- CI passes;
- the project context and roadmap are updated.

<!-- phase-46-roadmap:start -->
## Phase 46 — Bounded founder concierge state machine

**Status: Completed**

- Added the versioned `founder-concierge-v1` nine-state workflow.
- Added authenticated founder-only current-state, bounded-update, and expected-state transition APIs.
- Added one narrowly allowlisted and audited assessment-draft write capability; unrelated write tools remain disabled.
- Required explicit founder confirmation before deterministic assessment submission.
- Added the internal successful-submission bridge from `generating_plan` to `plan_ready`.
- Added the responsive founder concierge frontend while keeping the site-wide chatbot separate and read-only.
- Preserved deterministic readiness, eligibility, recommendation, amount, deadline, ordering, and verification authority outside the browser.
- Added focused backend and frontend regression coverage.
- Validated 124 frontend tests, the 465-test backend suite, the frontend production build, Ruff, Django checks, and zero migration drift.
<!-- phase-46-roadmap:end -->

## Phase 47 — Consolidated deterministic starting plan

**Status: Completed**

- Added the persisted, versioned `startup-starting-plan-v1` contract.
- Composed exact readiness, action-plan, and recommendation-run sources without
  introducing a second decision engine.
- Preserved profile, source, result, engine-version, and recommendation
  snapshots.
- Added idempotent generation, one current plan per startup, and immutable
  historical source references.
- Added authenticated current, history, detail, and generate APIs with owner
  isolation and raw-payload rejection.
- Integrated plan creation into confirmed assessment submission and concierge
  completion in the existing transaction.
- Added a dedicated founder Starting plan workspace with provenance and
  responsive grouped actions.
- Explicitly left prerequisite dependency status as `not_evaluated` until
  Phases 48 and 49.
- Added focused backend, frontend, authorization, integration, and regression
  coverage.
- Validated 473 backend tests, 127 frontend tests, the frontend production
  build, Ruff, Django checks, and zero migration drift.

See
[Consolidated deterministic starting plan](startups/STARTING_PLAN_V1.md).

## Phase 50 — Public entry and authentication

**Status: Completed**

- Added public landing page (`LandingPage`) with hero workspace preview, how-it-works workflow, capability breakdown, and responsible AI trust principles.
- Added public navigation with header actions for sign in and founder registration.
- Added public founder registration API (`POST /api/v1/auth/register/`) with Django password validation, email normalization, and strict `FOUNDER` role assignment.
- Added founder sign in page (`LoginPage`) with simpleJWT token authentication (`POST /api/v1/auth/token/`).
- Added password recovery page (`PasswordRecoveryPage`) with recovery guidance and support instructions.
- Protected application shell (`App.jsx`) ensuring unauthenticated users see public entry while authenticated users access the private workspace.
- Added 4 backend API tests and frontend Vitest coverage.
- Validated 522 backend tests, 144 frontend tests, frontend production build, Ruff, Django checks, and zero migration drift.

See
[Public entry and authentication](frontend/PUBLIC_ENTRY_V1.md).

## Phase 51 — Structured My Startup experience

**Status: Completed**

- Added structured My Startup workspace (`MyStartupPage.jsx`) organizing company facts into 9 domain sections.
- Added deterministic profile completeness calculation (`profileCompleteness.js`) with section progress bars and overall percentage scoring.
- Added source and verification badges (`Verified`, `Founder Claim`, `Extracted`) for transparent fact provenance.
- Added purposeful empty states providing clear guidance on which schemes or tax exemptions are unlocked by filling missing fields.
- Added direct section editing modal (`SectionEditModal`) with owner-validated `PATCH` updates to `StartupProfile` and `profile_data`.
- Added 2 backend API tests and 7 frontend unit/component tests.
- Validated 524 backend tests, 151 frontend tests, frontend production build, Ruff, Django checks, and zero migration drift.

See
[Structured My Startup experience](startups/MY_STARTUP_EXPERIENCE_V1.md).

## Phase 52 — AI startup document intake

**Status: Completed**

- Added AI Startup Document Intake workspace (`DocumentIntakeWorkspace.jsx`) enabling founders to upload pitch decks, certificates, and MSME PDFs.
- Expanded extraction service (`document_autofill.py`) supporting pitch decks, sectors, technologies, team size, funding required, and regulatory registration IDs.
- Added confidence scoring (High 90%+, Medium 70%+) and page-level evidence provenance snippets.
- Added profile conflict detection comparing extracted values against current saved profile attributes.
- Added founder confirmation workflow requiring explicit acceptance of suggestions before updating `StartupProfile` with `autofilled_fields` tagging.
- Added 1 backend test and 2 frontend component tests.
- Validated 525 backend tests, 153 frontend tests, frontend production build, Ruff, Django checks, and zero migration drift.

See
[AI startup document intake](startups/DOCUMENT_INTAKE_V1.md).

## Phase 53 — Dynamic startup assessment wizard

**Status: Completed**

- Enhanced 8-step assessment wizard (`AssessmentWizard.jsx`) with dynamic wizard progress gauge and step completion checkmark badges (✓).
- Added one-click profile prefilling (`assessmentFormFromProfile`) populating known facts from *My Startup* profile.
- Added step-by-step progress calculator (`assessmentProgress`) and live validation feedback per step.
- Added Lock & Submit Confirmation Modal presenting key attribute summaries and version locking contract (`SUBMITTED`) before generating readiness scores, action roadmaps, and scheme recommendations.
- Added 3 frontend unit tests (`assessmentProgress.test.js`) and updated integration tests (`AssessmentWizard.test.jsx`).
- Validated 525 backend tests, 158 frontend tests, frontend production build, Ruff, Django checks, and zero migration drift.

See
[Dynamic startup assessment wizard](startups/ASSESSMENT_WIZARD_V1.md).

## Phase 54 — Readiness score breakdown & action roadmap

**Status: Completed**

- Built dedicated Readiness Score Breakdown & Action Roadmap workspace (`ActionRoadmapPage.jsx`).
- Added domain breakdown calculator (`readinessBreakdown.js`) categorizing findings across 5 core readiness domains (*Legal*, *Compliance*, *Market*, *Financial*, *Team*).
- Added evidence provenance displays with outcome pills (`PRESENT ✓`, `MISSING ✗`, `INCOMPLETE ⚠`), field paths, actual values, and reason explanations.
- Organized roadmap items into 3 prioritized execution waves (*Wave 1: Immediate Blockers*, *Wave 2: Capability Boosters*, *Wave 3: Scale & Governance*).
- Added direct deep-link navigation buttons linking action items to `Schemes`, `Document Intake`, `My Startup`, and `Requirements`.
- Added 2 unit tests (`readinessBreakdown.test.js`) and 2 component tests (`ActionRoadmapPage.test.jsx`).
- Validated 525 backend tests, 162 frontend tests, frontend production build, Ruff, Django checks, and zero migration drift.

See
[Readiness score breakdown & action roadmap](startups/READINESS_ROADMAP_V1.md).

## Phase 55 — Direct scheme matching engine & discovery explorer

**Status: Completed**

- Extracted and modularized `SchemeExplorerPage.jsx` & `SchemeDetailPage.jsx` components.
- Added multi-facet filter controls for Sector (*BioTech*, *CleanTech*, *FinTech*, etc.), Stage (*Ideation*, *Validation*, *Scaling*), Location/State (*Karnataka*, *Maharashtra*, etc.), and Support Type (*Grants*, *Loans*, *Tax Exemptions*).
- Added ranked scheme match score pills (`95% Match`), rank badges (`Rank #1`), support type tags, and maximum support amount formatting.
- Integrated direct official application portal launching (`Launch Official Application Portal ↗`) and manual verification claim workflows.
- Added unit tests in `SchemeExplorerPage.test.jsx` and `SchemeDetailPage.test.jsx` (165 total frontend tests passing across 32 test files).
- Validated 525 backend tests, 165 frontend tests, frontend production build, Ruff, Django checks, and zero migration drift.

See
[Direct scheme matching engine & discovery explorer](startups/SCHEME_EXPLORER_V1.md).

## Phase 56 — Regulatory compliance & certification engine

**Status: Completed**

- Built regulatory compliance calculator (`complianceEngine.js`) categorizing requirements into 6 authority groups (*DPIIT*, *FSSAI*, *CDSCO*, *ISO / BIS*, *MCA*, *Financial / Tax*).
- Extracted standalone `RequirementsPage.jsx` workspace featuring authority-wise filter tabs (*All Authorities*, *DPIIT*, *FSSAI*, *CDSCO*, *ISO / BIS*, *MCA*).
- Integrated verified scheme document & certification requirements display with direct scheme detail triggers (`Open scheme →`).
- Formatted external discovery certification dataset cards with applicability ("Who may need it"), validity and renewal periods, and official source links.
- Added unit tests in `complianceEngine.test.js` and `RequirementsPage.test.jsx` (170 total frontend tests passing across 34 test files).
- Validated 525 backend tests, 170 frontend tests, frontend production build, Ruff, Django checks, and zero migration drift.

See
[Regulatory compliance & certification engine](startups/COMPLIANCE_ENGINE_V1.md).

## Phase 57 — Capital & loan support workspace

**Status: Completed**

- Built capital support calculator (`capitalSupportEngine.js`) categorizing options into grants, debt facilities, working capital lines, and credit guarantees.
- Extracted standalone `FundingPage.jsx` workspace with financing category tabs (*All funding*, *Loans & credit*, *Grants and non-debt support*).
- Displayed published support amounts (₹), interest rate ranges, equity requirement flags, and eligibility inspection triggers.
- Rendered external capital support discovery dataset cards with collateral terms, repayment structures, and official lender portal links.
- Added unit tests in `capitalSupportEngine.test.js` and `FundingPage.test.jsx` (175 total frontend tests passing across 36 test files).
- Validated 525 backend tests, 175 frontend tests, frontend production build, Ruff, Django checks, and zero migration drift.

See
[Capital & loan support workspace](startups/CAPITAL_SUPPORT_V1.md).

## Phase 58 — Verified startup & reviewer claim governance

**Status: Completed**

- Modularized standalone `ReviewerVerificationWorkspace.jsx` workspace for server-authorized reviewer claim audits.
- Implemented queue filter controls by submission lifecycle state (*Pending review*, *Approved*, *Rejected*, *Expired*).
- Added secure protected evidence inspection file download triggers.
- Built `ReviewerDecisionForm` for creating immutable reviewer decisions with verified values, valid-from dates, and justification notes.
- Added unit tests in `ReviewerVerificationWorkspace.test.jsx` (177 total frontend tests passing across 37 test files).
- Validated 525 backend tests, 177 frontend tests, frontend production build, Ruff, Django checks, and zero migration drift.

See
[Verified startup & reviewer claim governance](startups/CLAIM_GOVERNANCE_V1.md).

## Phase 54 — AI Startup Builder

**Status: Completed**

- Built `StartupBuilderSection` model (`startup-builder-v1` schema) supporting problem, customer, interview, validation, business model, and pricing sections.
- Created `builder_draft_service.py` for grounded AI draft generation via structured JSON schemas and Ollama LLM provider.
- Developed `StartupBuilderPage.jsx` workspace with interactive tabbed navigation, field forms, AI draft triggers, and confirmation workflow.
- Added backend API tests (`test_startup_builder_api.py`) and frontend component tests (`StartupBuilderPage.test.jsx`).
- Validated 530 backend tests, 184 frontend tests, frontend production build, Ruff, Django checks, and zero migration drift.

See
[AI Startup Builder workspace](startups/STARTUP_BUILDER_V1.md).

## Phase 55 — AI Capital Planner

**Status: Completed**

- Built `StartupCapitalPlan` model (`startup-capital-plan-v1` schema) for deterministic burn rate, runway months, health status, scenarios, capital allocations, sensitivity matrix, and AI tradeoff notes.
- Developed `capital_planner_engine.py` calculation engine and `capital_planner_service.py` CFO AI tradeoff service.
- Developed `CapitalPlannerPage.jsx` workspace with input controls, runway metric cards, scenario tabs, allocation progress bars, and AI insight notes.
- Added backend API tests (`test_capital_planner_api.py`) and frontend component tests (`CapitalPlannerPage.test.jsx`).
- Validated 530 backend tests, 188 frontend tests, frontend production build, Ruff, Django checks, and zero migration drift.

See
[AI Capital Planner workspace](startups/STARTUP_CAPITAL_PLANNER_V1.md).

## Phase 56 — Execution & Milestones Engine

**Status: Completed**

- Built `StartupMilestone` model (`startup-milestone-v1` schema) supporting 5 domain categories, dependency enforcement, completion evidence, and founder updates log.
- Created `milestone_service.py` for cycle detection, prerequisite checks, completion with evidence, and progress logging.
- Developed `ExecutionMilestonesPage.jsx` workspace with category filters, status tabs, Create/Edit modal, Complete Milestone modal, and Progress Log modal.
- Added backend API tests (`test_milestone_api.py`) and frontend component tests (`ExecutionMilestonesPage.test.jsx`).
- Validated 530 backend tests, 195 frontend tests, frontend production build, Ruff, Django checks, and zero migration drift.

See
[Execution & Milestones Engine workspace](startups/EXECUTION_MILESTONES_V1.md).
