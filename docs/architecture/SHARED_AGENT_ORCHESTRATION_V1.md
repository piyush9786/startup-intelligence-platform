# Shared Agent Orchestration V1

## Purpose

The shared agent-orchestration foundation establishes the persistence,
authorization, bounded-execution, tool-registry, and audit boundary for later
conversational features.

It does not introduce a general autonomous agent.

It does not make readiness, eligibility, recommendation, verification, funding,
deadline, legal, or prerequisite-ordering decisions.

## Application

The foundation is implemented in:

    backend/apps/assistant/

The Django application owns:

- agent sessions;
- agent messages;
- tool definitions and registry behavior;
- tool-call audit logs;
- claim-to-tool-call references;
- canonical output hashing;
- session and message services.

## Persisted models

### AgentSession

An agent session belongs to one authenticated founder.

A session may optionally be scoped to one startup profile owned by that
founder.

The current agent types are:

- `chatbot`;
- `concierge`;
- `funding_plan`.

The current statuses are:

- `active`;
- `completed`;
- `abandoned`.

Only one active session may exist for the same founder, agent type, and startup
scope.

A global session uses the persisted scope key `global`.

A startup-scoped session uses the startup profile UUID as its scope key.

Sessions retain:

- state;
- context;
- user turn count;
- maximum allowed user turns;
- last activity time;
- completion time.

The database constrains the turn count to remain within the configured limit.

### AgentMessage

Agent messages are append-only records.

Roles are:

- `system`;
- `user`;
- `agent`;
- `tool`.

Each message has a session-local sequence number.

User messages increment the bounded session turn count.

Messages cannot be appended after a session is closed.

### AgentToolCallLog

Tool-call logs are append-only records.

Every log retains:

- session;
- optional triggering message;
- actor;
- sequence number;
- tool name;
- tool version;
- status;
- input parameters;
- authorization context;
- output or safe failure snapshot;
- canonical output hash;
- error code and safe error text;
- duration;
- invocation time.

Statuses are:

- `succeeded`;
- `failed`;
- `denied`.

Successful calls cannot contain an error.

Failed and denied calls require an error code.

### AgentClaimReference

A claim reference links one agent-authored message to one successful tool call.

It retains:

- a stable claim key;
- rendered claim text;
- the tool-call log;
- the output path supporting the claim.

The message and tool call must belong to the same session.

Claims cannot reference failed or denied tool calls.

## Append-only policy

`AgentMessage`, `AgentToolCallLog`, and `AgentClaimReference` use an append-only
model boundary.

Existing instances cannot be updated or deleted through model instance
operations.

The Django admin exposes these records as read-only audit data.

Database administrators remain responsible for restricting direct database
mutation in production.

## Canonical output hashes

Tool outputs are normalized before hashing.

Normalization supports:

- dictionaries with stable key order;
- lists and tuples;
- sets with deterministic ordering;
- UUID values;
- dates and datetimes;
- decimals;
- JSON primitive values.

The normalized output is serialized with deterministic separators and key
ordering.

The resulting UTF-8 bytes are hashed with SHA-256.

The stored output hash allows later audit checks to confirm that a tool output
snapshot has not changed.

## Tool registry

Tools must be explicitly registered through `AgentToolRegistry`.

A definition includes:

- tool name;
- version;
- description;
- handler;
- allowed agent types;
- read-only status.

Duplicate names are rejected.

Unregistered tools are denied and logged.

A registered tool may run only when:

- the actor is authenticated;
- the actor is active;
- the actor owns the session;
- the session is active;
- the agent type is allowed;
- the tool is read-only.

Write-capable tools are denied during the Phase 43 foundation.

## Initial tool

The initial registered tool is:

    get_startup_profile@v1

It returns the founder-owned startup profile associated with the session.

For a global session it returns an explicit null startup profile.

It accepts no arbitrary startup-profile identifier, preventing callers from
selecting another founder's profile.

The tool reuses the existing startup-profile serializer.

## Authorization context

Every tool-call log stores the evaluated authorization context, including:

- actor identifier;
- actor role;
- active-account status;
- session identifier;
- founder identifier;
- startup profile identifier;
- agent type;
- session status;
- tool read-only classification;
- authorization result;
- reason.

Frontend visibility is not an authorization boundary.

## Bounded execution

Each session has a configured maximum number of founder turns.

The initial default is 20 turns.

The current hard maximum is 100 turns.

Only user-authored messages increment the turn count.

Once the limit is reached, additional user messages are rejected.

This foundation does not yet execute model turns or implement token,
wall-clock, or request-rate budgets. Those controls belong to the site-wide
chatbot execution milestone.

## Trust boundary

The orchestration layer may retrieve and organize persisted data.

It may not:

- write directly to startup profiles;
- submit an assessment;
- approve or reject evidence;
- change readiness findings;
- change eligibility results;
- change recommendation ranking;
- invent funding amounts;
- invent application deadlines;
- choose prerequisite ordering;
- expose unrestricted database access.

Deterministic domain services remain authoritative.

## Public API status

Phase 43 does not expose a public agent API.

The current surface is an internal service and persistence foundation.

The site-wide chatbot milestone will add authenticated API endpoints and
founder-facing UI on top of these models and services.

## Main implementation files

Models and admin:

    backend/apps/assistant/models.py
    backend/apps/assistant/admin.py
    backend/apps/assistant/migrations/0001_initial.py

Services:

    backend/apps/assistant/services/canonical.py
    backend/apps/assistant/services/sessions.py
    backend/apps/assistant/services/tool_registry.py
    backend/apps/assistant/services/tools.py

Tests:

    backend/apps/assistant/tests/test_agent_orchestration_foundation.py

## Validation coverage

Focused tests cover:

- owner-scoped and idempotent active sessions;
- database uniqueness for global active sessions;
- startup-profile ownership;
- founder-role restrictions;
- closed-session replacement;
- ordered messages;
- bounded user turns;
- closed-session message rejection;
- registry contents;
- duplicate tool rejection;
- successful tool-call audit logs;
- explicit global-profile output;
- non-owner denial logging;
- unregistered-tool denial logging;
- write-tool denial logging;
- failed-tool hashing and logging;
- claim references;
- cross-session claim rejection;
- append-only records.

Required validation:

    docker compose exec -T backend pytest -q
    docker compose exec -T backend ruff check .
    docker compose exec -T backend python manage.py check
    docker compose exec -T backend python manage.py makemigrations --check --dry-run
    git diff --check
