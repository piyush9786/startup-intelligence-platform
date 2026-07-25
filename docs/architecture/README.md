# Architecture

## Architectural style

The Startup Intelligence Platform is a modular Django monolith with a React
frontend and asynchronous Celery workers.

The modular monolith keeps transactions, permissions, and audit trails simple
while preserving service boundaries that may later be extracted if scale
requires it.

## System overview

```text
Founder / Reviewer / Administrator
                │
                ▼
          React + Vite
                │
                ▼
      Django REST Framework
                │
   ┌────────────┼─────────────┐
   ▼            ▼             ▼
PostgreSQL   Celery/Redis   Object and graph services
                               │
                 ┌─────────────┼──────────────┐
                 ▼             ▼              ▼
               MinIO         Qdrant         Neo4j

                         Ollama
                 embeddings + generation
```

## Source of truth

PostgreSQL is authoritative for:

- users and permissions;
- sources and source documents;
- canonical schemes and scheme versions;
- verified executable rules;
- startup profiles and assessment drafts;
- readiness assessments and action plans;
- eligibility assessments;
- recommendation runs and snapshots;
- verification submissions, evidence metadata, and immutable decisions;
- advisor jobs and briefing snapshots.

MinIO stores object bytes.

PostgreSQL stores their metadata and access relationships.

Qdrant and Neo4j are derived stores.

They must be rebuildable from authoritative records and must not silently become
the source of truth for eligibility or permissions.

## Domain boundaries

### Frontend

The frontend domain is built on React and Vite and implements:

- global multi-language (i18n) support across public and authenticated views;
- responsive user interfaces adopting modern web design paradigms (glassmorphism, vibrant palettes, modern typography, semantic layouts);
- deterministic AI Capital Planner UI for burn-rate and scenario modeling;
- accessible routing, page transitions, and authenticated dashboard layouts.

### Sources, documents, discovery, and knowledge

This path collects external material and creates reviewable knowledge
candidates.

```text
Source
→ SourceDocument
→ extraction and chunks
→ discovery and quality assessment
→ knowledge candidate
→ human review
→ canonical publication
```

Extracted content remains non-authoritative until reviewed and published.

### Schemes

The schemes domain owns canonical programmes, immutable versions, benefits,
requirements, application information, and executable rules.

Eligibility is always evaluated against a specific `SchemeVersion`.

### Startups

The startups domain owns:

- founder startup profiles;
- assessment drafts;
- submitted profile updates;
- readiness evaluation and persistence;
- readiness action plans;
- founder-advisor source snapshots, jobs, and briefings.

### Recommendations

The recommendations domain owns:

- deterministic rule evaluation;
- persisted eligibility assessments;
- recommendation scoring and ranking;
- recommendation generation history;
- evidence snapshots;
- manual verification submissions;
- evidence metadata;
- immutable reviewer decisions;
- verified-decision provenance.

## Deterministic decision flow

```text
StartupProfile
      │
      ├── readiness engine
      │       └── readiness assessment and action plan
      │
      └── eligibility engine + verified SchemeVersion
              │
              ├── profile values
              ├── effective reviewer-approved values
              └── verified executable rules
                      │
                      ▼
              EligibilityAssessment
                      │
                      ▼
              deterministic ranking
                      │
                      ▼
              RecommendationGenerationRun
```

## Verification boundary

Founder submissions and uploaded evidence are claims, not authoritative facts.

Only a current and effective reviewer approval may provide a manual rule value
to the eligibility engine.

Reviewer decisions are immutable.

New decisions supersede old effective state without rewriting history.

Concurrent first submissions are serialized by locking the stable startup
profile before current-submission replacement.

## AI and retrieval boundary

The current LLM path is controlled rather than autonomous.

```text
Persisted deterministic snapshots
        +
Qdrant evidence retrieval
        +
versioned prompt and output schema
        ▼
local Ollama generation
        ▼
validated and persisted advisor briefing
```

The LLM explains and synthesizes.

It does not determine eligibility, reviewer approval, ranking, verified
deadlines, or funding-plan ordering.

Qdrant retrieval should fail open for optional guidance without breaking the
authoritative founder workspace.

## Assistant layer

The `apps/assistant` application provides:

- persisted agent sessions and messages;
- immutable tool-call logs;
- a whitelisted read-mostly tool registry;
- a site chatbot;
- a bounded concierge state machine;
- narration for deterministic funding plans.

The assistant layer must call existing domain services.

It must not receive unrestricted ORM or database access.

## Security model

- Backend permissions are authoritative.
- Startup resources are owner-scoped.
- Reviewer APIs require explicit eligibility-review capability.
- Private evidence is downloaded through authenticated endpoints.
- Storage keys are not public API fields.
- Internal verification identifiers may be retained in snapshots but are not
  rendered as founder-facing content.
- Generated regulatory and scheme claims require verified or grounded sources.

## Concurrency and immutability

Use database transactions and stable-parent locks for workflows where the
absence of a child row would otherwise create a first-write race.

Historical assessments, recommendation runs, reviewer decisions, source
snapshots, and briefing outputs should remain immutable.

New state should supersede or reference historical state instead of overwriting
it.

## Evolution strategy

Keep the modular monolith until observed load or team boundaries justify
extraction.

Likely future extraction candidates are:

- collection and document processing;
- embedding and retrieval;
- notifications;
- conversational orchestration.

Public APIs and versioned contracts should remain stable if an internal module
is extracted.

- [Site-wide founder chatbot](SITE_WIDE_CHATBOT_V1.md)
