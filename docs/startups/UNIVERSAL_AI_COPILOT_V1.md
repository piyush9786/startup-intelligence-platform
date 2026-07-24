# Universal AI Copilot — Phase 57

## Overview

The Universal AI Copilot upgrades the existing `ChatbotDrawer` + `AgentSession` chatbot into a workspace-contextually-aware AI assistant. When a founder opens the copilot on any page, the active workspace is automatically injected into the session so every response is grounded in the founder's current context.

---

## Key Capabilities

1. **Workspace Context Injection**:
   - `POST /api/v1/assistant/chatbot/current/copilot-context/` accepts `{ workspace, context }` and writes it to the active session's `copilot_context` field.
   - Called automatically by `ChatbotDrawer` whenever the drawer opens or the active workspace changes.
   - Validated against an explicit whitelist of 17 known platform workspace slugs.

2. **Workspace-Aware AI Responses**:
   - The chatbot reads `session.copilot_context.workspace` when building platform help replies.
   - Workspace-specific guidance messages are returned for: *milestones*, *capital-planner*, *builder*, *schemes*, *startup*, *assessment*.
   - Three new intent classifiers: `milestones` (runway, burn, net burn), `capital_planner` (runway/burn terms), `builder` (problem statement, persona terms).
   - Three new navigation replies routing to: `milestones`, `capital-planner`, `builder`.

3. **Workspace-Aware Quick Prompts**:
   - The `ChatbotDrawer` surfaces contextual pre-built prompts per active view:
     - **Milestones**: *"Which milestones should I prioritize?"*, *"Which milestones block my funding round?"*
     - **Capital Planner**: *"Is my runway healthy?"*, *"What does the Conservative scenario mean?"*
     - **Builder**: *"How do I define my customer persona?"*
     - **Schemes**: *"How do I apply to DPIIT Startup India?"*
     - Default: *"What can you help with?"*, *"What should I do next?"*

---

## Technical Architecture

- **Backend Session Field**: `copilot_context` JSONField on `AgentSession` (migration `0002_copilot_context.py`).
- **Context Injection Endpoint**: `apps/assistant/copilot_context_views.py` — `CopilotContextView`.
- **Enhanced Chatbot Service**: `apps/assistant/services/chatbot.py` — workspace-aware `_platform_help_reply`, extended `_classify_intent`, and extended `_navigation_reply`.
- **Frontend API Client**: `copilotApi.js` — `injectCopilotContext(workspace, context)`.
- **Updated ChatbotDrawer**: `WORKSPACE_QUICK_PROMPTS` map, `getWorkspacePrompts(view)`, and automatic context injection effect.

---

## Verification & Validation

- 536 backend pytest tests passing.
- 198 frontend Vitest tests across 44 test files passing.
- Frontend production bundle build (`npm run build`) passing in 2.00s.
- Ruff linting, Django system checks, migration check, and `git diff --check` all passing with 0 errors.
