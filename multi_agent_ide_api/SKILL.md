---
name: multi_agent_ide_api
description: Swagger-first API interaction skill for multi_agent_ide — OpenAPI schema discovery, endpoint reference, filter/propagator/transformer operations, and best practices.
---

Use this skill to interact with the running `multi_agent_ide` application through its REST API. All API operations should be performed by calling endpoints directly using the Swagger UI or constructing HTTP requests from the OpenAPI spec.

For UI-specific operations (TUI state inspection, UI actions), see `multi_agent_ide_ui_test` skill instead.

For schemas not available from OpenAPI (filter instruction contracts, resolution type enums, internal serialized shapes), see `multi_agent_ide_validate_schema` skill.

## Base URL
- Default: `http://localhost:8080`

## Swagger UI
- Available at: `http://localhost:8080/swagger-ui.html`
- Raw OpenAPI spec: `http://localhost:8080/v3/api-docs`

## OpenAPI Schema Discovery

Use `scripts/api_schema.py` for progressive schema exploration — it queries the live `/v3/api-docs` endpoint and returns structured output.

### Levels
- **Level 1** (default) — tag/group names only
- **Level 2** — endpoints (method + path + summary) grouped by tag
- **Level 3** — endpoints with request/response schema shapes
- **Level 4** — raw `/v3/api-docs` JSON dump

### Usage
```bash
# List all API groups
python scripts/api_schema.py

# List all endpoints
python scripts/api_schema.py --level 2

# Show request/response shapes for a group
python scripts/api_schema.py --level 3 --tag "Debug UI"
```

### Best Practices
- Always start with level 1 to see available groups before drilling down.
- Use level 3 when constructing a new API call — it shows field names without the full schema noise.
- Run against the live app so you always see the actual deployed schema.

## Calling Endpoints Directly

Instead of wrapper scripts, call endpoints directly using `curl`, `httpie`, or any HTTP client. Use `api_schema.py --level 3` to discover exact request/response shapes. All endpoints accept and return JSON.

Example:
```bash
# Start a goal
curl -X POST http://localhost:8080/api/ui/goals/start \
  -H 'Content-Type: application/json' \
  -d '{"goal":"...", "repositoryUrl":"/path/to/.git", "tags":["feature","workflow"]}'

# Poll workflow graph
curl -X POST http://localhost:8080/api/ui/workflow-graph \
  -H 'Content-Type: application/json' \
  -d '{"nodeId":"ak:01KJ..."}'
```

## API Endpoint Reference

### Debug UI (tag: "Debug UI") — Primary controller operations

| Method | Path | Operation |
|--------|------|-----------|
| POST | `/api/ui/goals/start` | Start a new goal |
| POST | `/api/ui/quick-actions` | Execute quick action (SEND_MESSAGE) |
| POST | `/api/ui/nodes/events` | List events (paginated) |
| POST | `/api/ui/nodes/events/detail` | Get event detail |
| POST | `/api/ui/workflow-graph` | **Primary polling endpoint** — workflow graph with metrics |
| POST | `/api/ui/nodes/state` | Get UI state snapshot |
| POST | `/api/ui/nodes/actions` | Dispatch UI action |

### Permissions (tag: "Permissions")

| Method | Path | Operation |
|--------|------|-----------|
| GET | `/api/permissions/pending` | List pending permissions |
| GET | `/api/permissions/detail?id=...` | Get permission detail |
| POST | `/api/permissions/resolve` | Resolve permission (ALLOW_ONCE/ALLOW_ALWAYS/REJECT_ONCE/REJECT_ALWAYS) |

### Interrupts (tag: "Interrupts")

| Method | Path | Operation |
|--------|------|-----------|
| POST | `/api/interrupts` | Request interrupt |
| POST | `/api/interrupts/detail` | Get interrupt detail |
| POST | `/api/interrupts/resolve` | Resolve interrupt (APPROVED/REJECTED/CANCELLED/FEEDBACK/RESOLVED) |

### Propagators and Propagation (tags: "Propagators", "Propagation Items", "Propagation Records")

**Propagators are the escalatory mechanism for extracting out-of-domain (OOD) and out-of-distribution signals.** When a propagator fires, it means the agent encountered something noteworthy — a deviation, a decision point, or information that should propagate up the supervision hierarchy. These endpoints are among the most informative in the entire API for understanding agent behavior.

| Method | Path | Operation |
|--------|------|-----------|
| GET | `/api/propagators/attachables` | Source of truth for attachment targets |
| GET | `/api/propagators/layers/{layerId}/registrations` | List propagators by layer |
| POST | `/api/propagators/registrations` | Register propagator |
| GET | `/api/propagations/items` | List pending propagation items |
| POST | `/api/propagations/items/{itemId}/resolve` | Resolve propagation item |
| GET | `/api/propagations/records` | List execution records |

PROPAGATION events in the node event stream (via `/api/ui/nodes/events`) are the controller-facing source of truth for exact action request/result payloads. Use `/api/ui/nodes/events/detail` on PROPAGATION events to review full payloads before approving or rejecting escalations.

When an AI propagator escalates via `AskUserQuestionTool`, it creates an interrupt. Answer it via `POST /api/interrupts/resolve` with structured choices in `resolutionNotes`.

### Filters (tag: "Filter Policies")

Always check `GET /api/filters/attachables` first — it is the source of truth for event type names, contributor names, and valid layer/contributor combinations.

| Method | Path | Operation |
|--------|------|-----------|
| GET | `/api/filters/attachables` | List attachable targets |
| POST | `/api/filters/layers/policies` | List policies by layer |
| POST | `/api/filters/json-path-filters/policies` | Register event filter |
| POST | `/api/filters/markdown-path-filters/policies` | Register prompt filter |
| POST | `/api/filters/ai-path-filters/policies` | Register AI filter |
| POST | `/api/filters/policies/deactivate` | Deactivate policy |
| POST | `/api/filters/policies/layers/enable` | Enable at layer |
| POST | `/api/filters/policies/layers/disable` | Disable at layer |
| POST | `/api/filters/policies/records/recent` | View filtered records |

### Transformers (tags: "Transformers", "Transformation Records")

| Method | Path | Operation |
|--------|------|-----------|
| GET | `/api/transformers/attachables` | List attachment targets |
| GET | `/api/transformers/layers/{layerId}/registrations` | List by layer |
| GET | `/api/transformations/records` | List execution records |

### Debug Runs (tag: "Debug Runs")

| Method | Path | Operation |
|--------|------|-----------|
| POST | `/api/runs/start` | Start debug run |
| GET | `/api/runs` | List runs (paginated) |
| POST | `/api/runs/get` | Get run by ID |
| POST | `/api/runs/timeline` | Get run timeline |
| POST | `/api/runs/actions` | Apply action to run |
| POST | `/api/runs/persistence-validation` | Trigger validation |

## Goal Tagging Policy
- Treat tags as required for every new goal.
- Prefer 3-8 short kebab-case descriptors covering:
  - change type: `bugfix`, `feature`, `refactor`, `investigation`, `test`, `docs`
  - subsystem: `controller`, `workflow`, `artifacts`, `ui`, `filters`, `worktree`, `acp`
  - intent: `routing`, `interrupt-handling`, `performance`, `stability`, `observability`, `diagnostic`

## API Best Practices
- Use `workflow-graph` as the primary status check — it exposes `metrics.pendingItems` for blocked/waiting nodes.
- After any send-message or action, always re-check `workflow-graph` before assuming the run advanced.
- Poll events at ~60-second intervals; only drill into event-detail when `workflow-graph` shows stalled/error state.
- `nodeId` scopes requests to that node and all descendant nodes.
- For schema introspection, prefer `api_schema.py --level 3 --tag <TagName>` — it reflects the live deployed version.
- For schemas not in OpenAPI (filter instruction contracts, resolution enums, internal serialized shapes), see `multi_agent_ide_validate_schema` skill.
