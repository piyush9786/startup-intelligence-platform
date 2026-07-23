# Site-Wide Founder Chatbot V1

## Purpose

The site-wide founder chatbot provides persistent product navigation,
workspace definitions, and startup-profile-aware explanations.

It is a bounded conversational interface over the existing deterministic and
verified platform core.

It does not replace readiness, eligibility, recommendation, verification,
funding, deadline, legal, or prerequisite-ordering services.

## User surface

The chatbot is available as a persistent founder-only launcher and responsive
drawer throughout the authenticated founder workspace.

The drawer provides:

- persisted conversation history;
- global or startup-profile session scope;
- current page context;
- bounded remaining-turn visibility;
- platform-navigation actions;
- grounded claim details;
- safe request-error handling;
- keyboard Escape dismissal;
- responsive mobile presentation.

Reviewer and administrative workspaces do not expose the founder chatbot.

Frontend visibility is not an authorization boundary.

## Authenticated API

The chatbot exposes two authenticated endpoints:

    GET /api/v1/assistant/chatbot/current/
    POST /api/v1/assistant/chatbot/current/messages/

The current-session endpoint creates or returns the one active chatbot session
for the authenticated founder and selected startup scope.

The message endpoint:

1. validates the founder request;
2. resolves an optional founder-owned startup profile;
3. creates or retrieves the active chatbot session;
4. appends the founder message;
5. produces a deterministic chatbot response;
6. appends the agent response;
7. returns the complete persisted conversation.

A startup profile owned by another user is not disclosed.

Non-founder users cannot create founder chatbot sessions.

## Persistence

The chatbot reuses the shared orchestration models:

- `AgentSession`;
- `AgentMessage`;
- `AgentToolCallLog`;
- `AgentClaimReference`.

Only one active chatbot session exists for the same founder and startup scope.

A global workspace conversation uses the persisted global scope.

A startup-profile conversation uses that profile's persisted scope key.

Founder messages increment the bounded session turn count.

The initial session limit is 20 founder turns.

## Deterministic response layer

Version 1 uses the deterministic chatbot contract:

    site-chatbot-v1

The response layer recognizes bounded platform-help intents such as:

- general workspace help;
- startup-profile context;
- startup assessment;
- readiness;
- action roadmap;
- schemes;
- requirements;
- funding and loans;
- founder-advisor guidance.

Navigation responses may identify an existing workspace destination.

They do not execute the navigation themselves.

The frontend treats returned navigation metadata as a user-facing action, not
as authorization.

## Tool use and claims

Startup-specific factual claims execute only through the versioned,
whitelisted read-only tool registry.

The initial chatbot tool is:

    get_startup_profile@v1

For a startup-scoped session, it returns the founder-owned serialized startup
profile.

For a global session, it returns an explicit null startup profile.

A successful startup-specific claim records:

- claim key;
- rendered claim text;
- supporting tool-call log;
- output path;
- tool name and version;
- canonical output hash.

The claim cannot reference a failed, denied, or cross-session tool call.

Additional domain tools remain separate milestones.

## Rate and turn limits

The message endpoint uses the scoped throttle:

    assistant_chat_turn

Its environment configuration is:

    ASSISTANT_CHATBOT_TURN_RATE=20/hour

The throttle is resolved dynamically from Django REST Framework settings so
runtime configuration and test overrides remain authoritative.

The request-rate limit is separate from the persisted founder-turn limit.

When the founder-turn limit is reached, the API returns a conflict response
with the code:

    turn_limit_reached

## Page context

The frontend sends bounded page context with each message.

The current payload includes the active workspace view.

Page context is convenience context only.

It cannot select another founder's startup, expand permissions, bypass
ownership checks, change deterministic records, or authorize a tool call.

The backend validates that page context is a bounded JSON object.

## Trust boundary

The chatbot may:

- explain the platform;
- identify the selected startup profile;
- navigate to existing founder workspace pages;
- organize persisted read-only information;
- expose claim-to-tool-call provenance.

The chatbot may not:

- modify a startup profile;
- update an assessment draft;
- submit an assessment;
- upload or approve verification evidence;
- change readiness findings;
- change eligibility results;
- change recommendation ranking;
- invent funding amounts;
- invent deadlines;
- make legal or regulatory conclusions;
- choose prerequisite ordering;
- perform deep synthesis in place of the grounded founder-advisor workflow.

Deterministic domain services and verified evidence remain authoritative.

## Main implementation files

Backend:

    backend/apps/assistant/chatbot_serializers.py
    backend/apps/assistant/services/chatbot.py
    backend/apps/assistant/views.py
    backend/apps/assistant/tests/test_chatbot_api.py
    backend/config/settings.py
    backend/config/urls.py

Frontend:

    frontend/src/ChatbotDrawer.jsx
    frontend/src/ChatbotDrawer.test.jsx
    frontend/src/chatbotApi.test.js
    frontend/src/api.js
    frontend/src/App.jsx
    frontend/src/App.test.jsx
    frontend/src/styles.css

## Validation coverage

Backend chatbot tests cover:

- anonymous access denial;
- persistent global sessions;
- persistent startup-scoped sessions;
- startup ownership and non-disclosure;
- founder-role enforcement;
- persisted user and agent messages;
- registered profile-tool execution;
- claim references and output hashes;
- explicit global null-profile claims;
- non-invention by navigation responses;
- bounded page context;
- founder-turn limits;
- scoped request throttling;
- existing conversation history.

Frontend tests cover:

- startup-scoped session loading;
- page-context message submission;
- persisted transcript rendering;
- grounded claim details;
- navigation actions;
- keyboard dismissal;
- safe error display;
- founder-only workspace integration;
- reviewer-workspace exclusion.

Required validation:

    docker compose exec -T backend pytest -q
    docker compose exec -T backend ruff check .
    docker compose exec -T backend python manage.py check
    docker compose exec -T backend python manage.py makemigrations --check --dry-run
    docker compose exec -T frontend npm test -- --run
    docker compose exec -T frontend npm run build
    git diff --check
