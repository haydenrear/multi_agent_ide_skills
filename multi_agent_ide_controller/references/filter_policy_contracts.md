# Filter Policy Contracts

## Overview

Data-layer filters use **instruction-based path filtering**. A Python script receives a serialized domain object and returns a JSON list of instructions that describe how to transform or remove it.

- **Graph events** → string filtering over either controller-formatted event text (`MARKDOWN_PATH` / `REGEX`) or serialized stream JSON (`JSON_PATH` / `REGEX`)
- **Prompt contributors** → string filtering over contributor text (`MARKDOWN_PATH` / `REGEX`)
- `AI_PATH` is a filter kind, not a `targetPath.pathType`; AI executors still return instructions whose `targetPath.pathType` is `REGEX`, `JSON_PATH`, or `MARKDOWN_PATH`

## Python Script Contract

The script must define a function (default name: `filter`) that:
- Receives: a single string argument (the serialized domain object)
- Returns: a JSON string containing a bare JSON array of instructions

### Return schema
```json
[
  {
    "op": "REMOVE | REPLACE | SET | REPLACE_IF_MATCH | REMOVE_IF_MATCH",
    "targetPath": {
      "pathType": "REGEX | JSON_PATH | MARKDOWN_PATH",
      "expression": "string"
    },
    "matcher": {
      "matcherType": "REGEX | EQUALS",
      "value": "required for *_IF_MATCH"
    },
    "value": "required for REPLACE/SET/REPLACE_IF_MATCH",
    "order": 0
  }
]
```

An empty array (`[]`) means passthrough (no transformation). A top-level `instructions` envelope is not consumed by `PathFilter`; it silently falls back to no-op because the executor response is deserialized as `List<Instruction>` directly.

Operational note:
- External `PYTHON` and `BINARY` executors launch with `filter.bins` as subprocess cwd.
- In local/tmp deployments for this repo, the built app config resolves `filter.bins` to `<tmp-repo>/multi_agent_ide_java_parent/multi_agent_ide/bin` because `{{PROJ_DIR}}` is the Spring app module project dir.
- Ensure that directory exists before testing external executors, or process start can fail before your script/binary runs.
- Controller/UI graph-event text filtering runs against raw `event.prettyPrint()` text. For `ARTIFACT_EMITTED` / `RenderedPromptArtifact` events, nested markdown is usually tab-indented inside that pretty-print payload, so `MARKDOWN_PATH` can no-op even when the same logical text is visible in the UI.
- Prompt-contributor `AI_PATH` worked in live validation. Graph-event `AI_PATH` on controller/query-time surfaces still passed through in the validated `AddMessageEvent` / `RenderedPromptArtifact` cases, so inspect context resolution before assuming graph-event AI will execute.

## Instruction Reference

### Operations

| Op | Requires `value` | Effect |
|---|---|---|
| `REMOVE` | No | Remove content at the target path |
| `REPLACE` | Yes | Replace content at the target path with `value` |
| `SET` | Yes | Set content at the target path to `value` (creates if absent) |
| `REPLACE_IF_MATCH` | Yes (`value`) + Yes (`matcher`) | Replace selected content only when matcher evaluates true |
| `REMOVE_IF_MATCH` | No (`value`) + Yes (`matcher`) | Remove selected content only when matcher evaluates true |

Instructions are applied in ascending `order`.

### Common Patterns

| Goal | Op | targetPath | value |
|---|---|---|---|
| **Drop entire graph event** | `REMOVE` | `{"pathType": "JSON_PATH", "expression": "$"}` | — |
| **Drop entire prompt contributor** | `REMOVE` | `{"pathType": "MARKDOWN_PATH", "expression": "#"}` | — |
| Remove a field from event | `REMOVE` | `{"pathType": "JSON_PATH", "expression": "$.fieldName"}` | — |
| Remove nested field | `REMOVE` | `{"pathType": "JSON_PATH", "expression": "$.parent.child"}` | — |
| Remove a section from contributor | `REMOVE` | `{"pathType": "MARKDOWN_PATH", "expression": "## Section Name"}` | — |
| Mask tokens in raw text | `REPLACE` | `{"pathType": "REGEX", "expression": "token-[0-9]+"}` | `"token-***"` |
| Replace a field value | `REPLACE` | `{"pathType": "JSON_PATH", "expression": "$.fieldName"}` | new value |
| Replace a section's content | `REPLACE` | `{"pathType": "MARKDOWN_PATH", "expression": "## Section"}` | new markdown text |
| Add a new field | `SET` | `{"pathType": "JSON_PATH", "expression": "$.newField"}` | value |
| Add a new section | `SET` | `{"pathType": "MARKDOWN_PATH", "expression": "## New Section"}` | markdown text |
| Replace only when field equals | `REPLACE_IF_MATCH` | `{"pathType": "JSON_PATH", "expression": "$.severity"}` | `"LOW"` |
| Remove section only when regex matches | `REMOVE_IF_MATCH` | `{"pathType": "MARKDOWN_PATH", "expression": "## Debug"}` | — |

## Path Semantics

### RegexPath

Java regex expressions applied to the raw string payload supplied by the invoking integration surface.

| Expression | Targets |
|---|---|
| `token-[0-9]+` | matching token-like substrings |
| `(?s).*` | the full payload text (use carefully) |
| `(?i)error` | case-insensitive occurrences of `error` |

### JsonPath

Standard JsonPath expressions. Used for serialized graph event payloads (for example, stream/SSE/WebSocket event output).

| Expression | Targets |
|---|---|
| `$` | The entire root object (remove = drop event) |
| `$.fieldName` | A top-level field |
| `$.parent.child` | A nested field |
| `$.array[0]` | First element of an array |
| `$.array[*].field` | A field in every array element |

### MarkdownPath

**Header-based only.** Expressions reference markdown headers. Used for prompt contributor text and any controller/UI event text that is actually markdown-structured.

Important:
- MarkdownPath does **not** target arbitrary text spans. It only targets heading scopes (`#`, `## ...`, `### ...`, etc.).
- `#` is treated as the root document scope. A `REMOVE` on `#` drops the entire contributor/template output, regardless of the markdown content type.

| Expression | Targets |
|---|---|
| `#` | The entire document (remove = drop contributor) |
| `## Section Name` | A level-2 section and all content up to the next same-or-higher-level header |
| `### Sub Section` | A level-3 section and all content up to the next same-or-higher-level header |

Rules:
- Headers are matched by exact text after the `#` prefix (e.g. `## Debug Info` matches the header `## Debug Info`).
- A `Remove` on a section removes the header line and all content up to (but not including) the next header at the same or higher level.
- A `Remove` on `#` removes everything.

## Template Python Filter Functions

### Event filter: drop all NODE_STATUS_CHANGED payloads
```python
def filter(event_json: str) -> str:
    """Called with serialized GraphEvent JSON. Returns instruction list JSON."""
    import json
    event = json.loads(event_json)
    if event.get("eventType") == "NODE_STATUS_CHANGED":
        return json.dumps([
            {"op": "REMOVE", "targetPath": {"pathType": "JSON_PATH", "expression": "$"}, "order": 0}
        ])
    return json.dumps([])
```

### Event filter: strip a verbose field from events
```python
def filter(event_json: str) -> str:
    import json
    event = json.loads(event_json)
    if "stackTrace" in event:
        return json.dumps([
            {"op": "REMOVE", "targetPath": {"pathType": "JSON_PATH", "expression": "$.stackTrace"}, "order": 0}
        ])
    return json.dumps([])
```

### Event filter: drop events from a specific agent
```python
def filter(event_json: str) -> str:
    import json
    event = json.loads(event_json)
    if event.get("sourceAgent") == "discovery-orchestrator":
        return json.dumps([
            {"op": "REMOVE", "targetPath": {"pathType": "JSON_PATH", "expression": "$"}, "order": 0}
        ])
    return json.dumps([])
```

### Prompt contributor filter: remove "Debug Info" section
```python
def filter(contributor_text: str) -> str:
    """Called with contributor output text. Returns instruction list JSON."""
    import json
    return json.dumps([
        {"op": "REMOVE", "targetPath": {"pathType": "MARKDOWN_PATH", "expression": "## Debug Info"}, "order": 0}
    ])
```

### Prompt contributor filter: drop entire contributor
```python
def filter(contributor_text: str) -> str:
    import json
    return json.dumps([
        {"op": "REMOVE", "targetPath": {"pathType": "MARKDOWN_PATH", "expression": "#"}, "order": 0}
    ])
```

### Prompt contributor filter: replace a section
```python
def filter(contributor_text: str) -> str:
    import json
    return json.dumps([
        {"op": "REPLACE",
         "targetPath": {"pathType": "MARKDOWN_PATH", "expression": "## Context"},
         "value": "## Context\nSimplified context for this phase.",
         "order": 0}
    ])
```

### Prompt contributor filter: remove section only if matcher matches
```python
def filter(contributor_text: str) -> str:
    import json
    return json.dumps([
        {"op": "REMOVE_IF_MATCH",
         "targetPath": {"pathType": "MARKDOWN_PATH", "expression": "## Debug Info"},
         "matcher": {"matcherType": "REGEX", "value": "(?i)internal|scratch"},
         "order": 0}
    ])
```

## AI Executor Registration Notes

Dedicated registration endpoint:
- `POST /api/filters/ai-path-filters/policies`

Discovery/inspection endpoints are unchanged:
- `GET /api/filters/layers/{layerId}/policies`
- `GET /api/filters/policies/{policyId}/layers/{layerId}/records/recent`

When registering `executorType=AI`, the fields are:

| Field | Required | Description |
|---|---|---|
| `executorType` | **required** | Must be `"AI"` |
| `registrarPrompt` | **required** | Guidance explaining the filter's purpose — what it should act on and why |
| `sessionMode` | optional | `PER_INVOCATION` \| `SAME_SESSION_FOR_ALL` \| `SAME_SESSION_FOR_ACTION` \| `SAME_SESSION_FOR_AGENT` |
| `configVersion` | optional | Version tag for tracking configuration changes |

The model used is always the system default — custom model selection is not supported for AI filters.

### Execution flow

AI filters delegate to `LlmRunner.runWithTemplate()` using an `AiFilterContext` built from the originating `PromptContributorContext` or a `GraphEventObjectContext`-derived prompt context. The service (`FilterExecutionService.runAiFilter()`) extracts `OperationContext` from the filter context, builds an `AiFilterRequest` with the payload, applies the full decorator chain (request, prompt-context, tool-context, result) keyed to agent name `ai-filter`, action `path-filter`, method `runAiFilter`, then passes the decorated context to the `AiPathFilter` which calls the executor and runs the result through dispatching interpreters keyed by each instruction `targetPath.pathType`.

**Prerequisite**: AI filters require filter context that can resolve both `PromptContext` and `OperationContext`: either a `PromptContributorContext` (or `PathFilterContext` wrapping one), or a `GraphEventObjectContext` whose artifact key can be traced back to an agent process. When unavailable, execution is skipped with PASSTHROUGH and a warning is logged.

## Layer Binding & Matcher Reference

When registering a policy, the `layerBindings` array controls where the filter runs and which objects it matches. The matcher fields are **enums with fixed allowed values** — the server rejects anything else.

### Layer binding fields

| Field | Type | Allowed values | Description |
|---|---|---|---|
| `layerId` | string | any valid layer ID | Which layer this binding targets |
| `enabled` | boolean | `true`, `false` | Whether this binding is active |
| `includeDescendants` | boolean | `true`, `false` | Apply to child layers too |
| `isInheritable` | boolean | `true`, `false` | Allow one-shot propagation to descendant layers |
| `isPropagatedToParent` | boolean | `true`, `false` | Allow one-shot propagation to parent layer |
| `matcherKey` | **enum** | `"NAME"`, `"TEXT"` | **What field** on the domain object to match against |
| `matcherType` | **enum** | `"REGEX"`, `"EQUALS"` | **How** to compare `matcherText` against the resolved value |
| `matcherText` | string | any string | The regex pattern (if REGEX) or exact value (if EQUALS) to match |
| `matchOn` | **enum** | `"GRAPH_EVENT"`, `"PROMPT_CONTRIBUTOR"` | **Which domain object type** this binding applies to |

### matcherKey (enum: `NAME` | `TEXT`)

| Value | When `matchOn=GRAPH_EVENT` | When `matchOn=PROMPT_CONTRIBUTOR` |
|---|---|---|
| `NAME` | Matches against the GraphEvent class simple name (e.g. `"AddMessageEvent"`, `"PermissionRequestedEvent"`, `"NodeAddedEvent"`), not the payload `eventType` field (e.g. `"ADD_MESSAGE_EVENT"`) | Matches against the PromptContributor bean/logical name (e.g. `"debug-context"`, `"we-are-here"`, `"repo-summary"`) |
| `TEXT` | Matches against the string payload seen by the invoking integration surface: controller/UI formatted text for event list/detail paths, serialized JSON for stream/SSE/WebSocket paths | Matches against the contributor's template/static text content |

### matcherType (enum: `REGEX` | `EQUALS`)

| Value | Behavior | Example `matcherText` values |
|---|---|---|
| `REGEX` | `matcherText` is a Java regex pattern applied with full-string `matches()` semantics. Use `(?s).*...*` when you need substring matching. | `"AddMessage.*"`, `"(?s).*error.*"`, `"debug-.*"`, `"^Permission.*Event$"` |
| `EQUALS` | `matcherText` must exactly equal the resolved value (case-sensitive, full string) | `"AddMessageEvent"`, `"debug-context"` |

### matchOn (enum: `GRAPH_EVENT` | `PROMPT_CONTRIBUTOR`)

| Value | Required for command | Constraint |
|---|---|---|
| `GRAPH_EVENT` | `register-event-filter` | **Must** be `GRAPH_EVENT` for event filters. Server rejects `PROMPT_CONTRIBUTOR` here. |
| `PROMPT_CONTRIBUTOR` | `register-prompt-filter` | **Must** be `PROMPT_CONTRIBUTOR` for prompt filters. Server rejects `GRAPH_EVENT` here. |

### CLI flag → matcher field mapping

The CLI flags automatically set the correct enum values:

| CLI flag | `matcherKey` | `matchOn` | `matcherType` |
|---|---|---|---|
| `--event-type-pattern <pattern>` | `NAME` | `GRAPH_EVENT` | `REGEX` (default) or `EQUALS` (with `--match-exact`) |
| `--event-text-pattern <pattern>` | `TEXT` | `GRAPH_EVENT` | `REGEX` (default) or `EQUALS` (with `--match-exact`) |
| `--contributor-name-pattern <pattern>` | `NAME` | `PROMPT_CONTRIBUTOR` | `REGEX` (default) or `EQUALS` (with `--match-exact`) |
| `--contributor-text-pattern <pattern>` | `TEXT` | `PROMPT_CONTRIBUTOR` | `REGEX` (default) or `EQUALS` (with `--match-exact`) |

### Concrete examples

**1. Match graph events by class name (regex)**
```json
{"matcherKey": "NAME", "matcherType": "REGEX", "matcherText": "AddMessage.*", "matchOn": "GRAPH_EVENT"}
```
CLI: `register-event-filter ... --event-type-pattern "AddMessage.*"`

**2. Match a specific graph event type (exact)**
```json
{"matcherKey": "NAME", "matcherType": "EQUALS", "matcherText": "AddMessageEvent", "matchOn": "GRAPH_EVENT"}
```
CLI: `register-event-filter ... --event-type-pattern "AddMessageEvent" --match-exact`

**3. Match graph events whose payload contains "error" (case-insensitive regex)**
```json
{"matcherKey": "TEXT", "matcherType": "REGEX", "matcherText": "(?i)error", "matchOn": "GRAPH_EVENT"}
```
CLI: `register-event-filter ... --event-text-pattern "(?i)error"`

**4. Match a prompt contributor by exact bean name**
```json
{"matcherKey": "NAME", "matcherType": "EQUALS", "matcherText": "debug-context", "matchOn": "PROMPT_CONTRIBUTOR"}
```
CLI: `register-prompt-filter ... --contributor-name-pattern "debug-context" --match-exact`

**5. Match prompt contributors whose name starts with "debug-"**
```json
{"matcherKey": "NAME", "matcherType": "REGEX", "matcherText": "debug-.*", "matchOn": "PROMPT_CONTRIBUTOR"}
```
CLI: `register-prompt-filter ... --contributor-name-pattern "debug-.*"`

**6. Match prompt contributors whose text mentions "TODO"**
```json
{"matcherKey": "TEXT", "matcherType": "REGEX", "matcherText": "TODO", "matchOn": "PROMPT_CONTRIBUTOR"}
```
CLI: `register-prompt-filter ... --contributor-text-pattern "TODO"`

## Layer Hierarchy

The system bootstraps this layer hierarchy on startup. Filters inherit down the tree — a filter on a parent layer applies to all descendants.

```
controller                              (CONTROLLER, depth 0)
├── controller-ui-event-poll            (CONTROLLER_UI_EVENT_POLL, depth 1)
└── workflow-agent                      (WORKFLOW_AGENT, depth 1)
    ├── workflow-agent/routeToContextManager           (WORKFLOW_AGENT_ACTION, depth 2)
    ├── workflow-agent/contextManagerRequest           (WORKFLOW_AGENT_ACTION, depth 2)
    ├── workflow-agent/coordinateWorkflow              (WORKFLOW_AGENT_ACTION, depth 2)
    ├── workflow-agent/handleUnifiedInterrupt          (WORKFLOW_AGENT_ACTION, depth 2)
    ├── workflow-agent/finalCollectorResult            (WORKFLOW_AGENT_ACTION, depth 2)
    ├── workflow-agent/consolidateWorkflowOutputs      (WORKFLOW_AGENT_ACTION, depth 2)
    ├── workflow-agent/consolidateDiscoveryFindings    (WORKFLOW_AGENT_ACTION, depth 2)
    ├── workflow-agent/consolidatePlansIntoTickets     (WORKFLOW_AGENT_ACTION, depth 2)
    ├── workflow-agent/consolidateTicketResults        (WORKFLOW_AGENT_ACTION, depth 2)
    ├── workflow-agent/kickOffAnyNumberOfAgentsForCodeSearch (WORKFLOW_AGENT_ACTION, depth 2)
    ├── workflow-agent/dispatchDiscoveryAgentRequests  (WORKFLOW_AGENT_ACTION, depth 2)
    ├── workflow-agent/decomposePlanAndCreateWorkItems (WORKFLOW_AGENT_ACTION, depth 2)
    ├── workflow-agent/dispatchPlanningAgentRequests   (WORKFLOW_AGENT_ACTION, depth 2)
    ├── workflow-agent/finalizeTicketOrchestrator      (WORKFLOW_AGENT_ACTION, depth 2)
    ├── workflow-agent/orchestrateTicketExecution      (WORKFLOW_AGENT_ACTION, depth 2)
    ├── workflow-agent/dispatchTicketAgentRequests     (WORKFLOW_AGENT_ACTION, depth 2)
    ├── workflow-agent/performMerge                    (WORKFLOW_AGENT_ACTION, depth 2)
    ├── workflow-agent/performReview                   (WORKFLOW_AGENT_ACTION, depth 2)
    ├── workflow-agent/handleTicketCollectorBranch     (WORKFLOW_AGENT_ACTION, depth 2)
    ├── workflow-agent/handleDiscoveryCollectorBranch  (WORKFLOW_AGENT_ACTION, depth 2)
    ├── workflow-agent/handleOrchestratorCollectorBranch (WORKFLOW_AGENT_ACTION, depth 2)
    ├── workflow-agent/handlePlanningCollectorBranch   (WORKFLOW_AGENT_ACTION, depth 2)
    ├── discovery-dispatch-subagent     (WORKFLOW_AGENT, depth 2)
    │   ├── discovery-dispatch-subagent/ranDiscoveryAgent           (WORKFLOW_AGENT_ACTION, depth 3)
    │   ├── discovery-dispatch-subagent/transitionToInterruptState  (WORKFLOW_AGENT_ACTION, depth 3)
    │   └── discovery-dispatch-subagent/runDiscoveryAgent           (WORKFLOW_AGENT_ACTION, depth 3)
    ├── planning-dispatch-subagent      (WORKFLOW_AGENT, depth 2)
    │   ├── planning-dispatch-subagent/ranPlanningAgent            (WORKFLOW_AGENT_ACTION, depth 3)
    │   ├── planning-dispatch-subagent/transitionToInterruptState  (WORKFLOW_AGENT_ACTION, depth 3)
    │   └── planning-dispatch-subagent/runPlanningAgent            (WORKFLOW_AGENT_ACTION, depth 3)
    └── ticket-dispatch-subagent        (WORKFLOW_AGENT, depth 2)
        ├── ticket-dispatch-subagent/ranTicketAgentResult        (WORKFLOW_AGENT_ACTION, depth 3)
        ├── ticket-dispatch-subagent/transitionToInterruptState  (WORKFLOW_AGENT_ACTION, depth 3)
        └── ticket-dispatch-subagent/runTicketAgent              (WORKFLOW_AGENT_ACTION, depth 3)
```

### Layer ID format

| Layer type | ID pattern | Example |
|---|---|---|
| Root controller | `controller` | `controller` |
| UI event poll | `controller-ui-event-poll` | `controller-ui-event-poll` |
| Agent | short name | `workflow-agent`, `discovery-dispatch-subagent` |
| Action | `<parent-agent>/<methodName>` | `workflow-agent/coordinateWorkflow`, `ticket-dispatch-subagent/runTicketAgent` |

### Inheritance examples

| Bind filter to | Applies to |
|---|---|
| `controller` | Everything (all agents, all actions, UI event poll) |
| `workflow-agent` | All 22 WorkflowAgent actions + all 3 sub-agents and their actions |
| `discovery-dispatch-subagent` | Only the 3 discovery sub-agent actions |
| `workflow-agent/performReview` | Only the `performReview` action |
| `controller-ui-event-poll` | Only the UI event poll layer |

## Endpoint Table

| Subcommand | Method | Path |
|---|---|---|
| `register-event-filter` | POST | `/api/filters/json-path-filters/policies` |
| `register-prompt-filter` | POST | `/api/filters/markdown-path-filters/policies` |
| `list-policies` | GET | `/api/filters/layers/{layerId}/policies` |
| `deactivate-policy` | POST | `/api/filters/policies/{policyId}/deactivate` |
| `toggle-policy-layer` | POST | `/api/filters/policies/{policyId}/layers/{layerId}/enable` or `disable` |
| `view-filtered-records` | GET | `/api/filters/policies/{policyId}/layers/{layerId}/records/recent` |
| `list-layer-children` | GET | `/api/filters/layers/{layerId}/children` |
