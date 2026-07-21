# Grounded Open-Source LLM Startup Advisor Briefings v1

## Runtime

The briefing generator uses a local Ollama service and defaults to:

```text
qwen3.5:9b
```

The model and provider are configurable through environment variables.
No proprietary hosted LLM or API key is required.

## Endpoint

```text
POST /api/v1/startup-advisor/briefings/generate/
```

Request:

```json
{
  "advisor_snapshot_id": "<uuid>"
}
```

The source must be an existing persisted `StartupAdvisorSnapshot`.
The endpoint never creates or refreshes deterministic readiness,
action-plan, recommendation, or advisor-snapshot data.

## Grounding contract

The prompt contains only the selected immutable advisor snapshot and a
versioned response schema.

Every top priority, scheme-guidance item, and risk must include source
references with:

- `source_type`;
- persisted source UUID;
- a JSON Pointer `field_path` that resolves inside that source object.

Server-side validation rejects:

- malformed structured output;
- invented source identifiers;
- missing field paths;
- non-contiguous priorities;
- scheme guidance without a persisted recommendation citation;
- unsupported additional fields.

Invalid or unavailable model output does not create a briefing row.

## Persistence

A successful `StartupAdvisorBriefing` stores:

- requester and startup profile;
- protected source advisor snapshot;
- provider and model identifiers;
- prompt and schema versions;
- exact prompt snapshot and response schema;
- generation parameters;
- validated structured briefing;
- input and output token counts when Ollama reports them;
- duration and non-sensitive response metadata.

Every successful generation creates a new historical briefing.

## Local setup

Start Ollama and pull the configured model:

```bash
docker compose up -d ollama
docker compose exec -T ollama ollama pull qwen3.5:9b
docker compose exec -T ollama ollama list
```

The default internal endpoint is:

```text
http://ollama:11434
```

A smaller model can be selected for lower-memory development machines:

```text
STARTUP_ADVISOR_LLM_MODEL=qwen3.5:4b
```

## Failure behavior

- inaccessible or unknown advisor snapshot: HTTP 404;
- local Ollama service or model unavailable: HTTP 503;
- malformed or ungrounded model output: HTTP 502;
- source snapshot changed during generation: HTTP 409.

## Tests

Automated tests use deterministic fake providers and `httpx.MockTransport`.
They do not download a model or make live LLM requests.
