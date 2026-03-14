# Propagator Contracts

## Overview

Propagators observe payloads flowing through the workflow agent graph. Unlike filters (which transform or remove data), propagators **emit a notification** — they do not modify the payload. When an AI propagator decides that content warrants attention, it uses the `AskUserQuestionTool` to ask for acknowledgement. **The controller can only acknowledge.** There is no approval, rejection, feedback, or other action — just acknowledgement.

## Auto-registered OOD propagators (already running)

The system **automatically bootstraps an AI propagator for every action request and response** across all registered agent actions at startup. These default propagators already cover out-of-domain (OOD) and out-of-distribution (OOD) detection using the base `ai_propagator` template with a generic registrarPrompt:

> "Escalate out-of-domain, out-of-distribution, or otherwise controller-relevant request and result payloads."

The `ai_propagator.jinja` template already encodes this OOD stance — it instructs the model to escalate when the payload is out of domain for the current task, out of distribution relative to the surrounding workflow, unsafe, ambiguous, contradictory, or likely to require controller or human judgment.

**When to register a custom propagator:** Only register a new propagator when you need something beyond the default OOD coverage — either:
1. A **specific concern** not covered by the generic OOD prompt (provide a targeted `registrarPrompt`)
2. A **different attach point** — prompt contributors, specific graph events, or a context surface rather than an action request/response

Do not register a custom propagator that just repeats the default OOD prompt on an action request/response that is already auto-covered.

## Interrupt Resolution

When an AI propagator escalates, it calls `AskUserQuestionTool` with its reasoning and asks for acknowledgement. Workflow execution pauses. **The only resolution is acknowledgement** — the controller acknowledges the interrupt and workflow resumes. There is no structured response, no approval or rejection, no feedback channel back to the agent.

## Propagator Attach Points

Propagators can attach to more than just action requests and responses. Use the right attach point for the concern:

| Attach point | `matchOn` value | Use when |
|---|---|---|
| Action request payload | `ACTION_REQUEST` | You want to observe what an agent is about to do |
| Action response payload | `ACTION_RESPONSE` | You want to observe what an agent produced |
| Prompt contributor output | `PROMPT_CONTRIBUTOR` | You want to monitor what context is being injected into an LLM call — e.g. detect looping, degenerate, or repetitive context |
| Graph event | `GRAPH_EVENT` | You want to flag specific event types — e.g. repeated failures, unexpected state transitions |

### Example: monitor a prompt contributor for looping behavior

Register on a `CurationHistoryContextContributor` prompt contributor to detect when the curation history being injected into an LLM call shows signs of looping or degenerate repetition:

```json
{
  "name": "curation-history-loop-detector",
  "description": "Flags looping or degenerate curation history before it reaches the LLM",
  "sourcePath": "custom://propagator/prompt/curation-history-loop",
  "propagatorKind": "AI_TEXT",
  "priority": 100,
  "activate": true,
  "layerBindings": [
    {
      "layerId": "workflow-agent",
      "matchOn": "PROMPT_CONTRIBUTOR",
      "enabled": true,
      "includeDescendants": true,
      "matcherKey": "NAME",
      "matcherType": "REGEX",
      "matcherText": "curation-history.*"
    }
  ],
  "executor": {
    "executorType": "AI_PROPAGATOR",
    "sessionMode": "SAME_SESSION_FOR_ACTION",
    "registrarPrompt": "Flag if the curation history shows repeated identical phases, the same agent cycling without progress, or a degenerate loop pattern. The default OOD check already runs on action payloads — this prompt contributor propagator is specifically watching for loop/regression indicators in the injected context."
  }
}
```

### Example: monitor specific graph events

Register on `PermissionRequestedEvent` or repeated `NODE_STATUS_CHANGED` events to let the LLM flag unexpected escalation patterns:

```json
{
  "name": "permission-event-monitor",
  "description": "Flags unexpected permission escalations during workflow execution",
  "sourcePath": "custom://propagator/event/permission-escalation",
  "propagatorKind": "AI_TEXT",
  "priority": 100,
  "activate": true,
  "layerBindings": [
    {
      "layerId": "workflow-agent",
      "matchOn": "GRAPH_EVENT",
      "enabled": true,
      "includeDescendants": true,
      "matcherKey": "NAME",
      "matcherType": "REGEX",
      "matcherText": "PermissionRequestedEvent"
    }
  ],
  "executor": {
    "executorType": "AI_PROPAGATOR",
    "sessionMode": "SAME_SESSION_FOR_ACTION",
    "registrarPrompt": "This propagator fires on permission request events. Flag any permission escalation that looks unusual for the current workflow phase — unexpected tool requests, permission requests outside the normal execution path, or a sudden burst of permission requests that may indicate runaway agent behavior."
  }
}
```

## AI Propagator Registration

Registration endpoint:
- `POST /api/propagators/registrations`

### Request fields

| Field | Required | Description |
|---|---|---|
| `name` | **required** | Human-readable name for this propagator |
| `description` | **required** | What this propagator does |
| `sourcePath` | **required** | Logical identifier for this propagator instance |
| `propagatorKind` | **required** | `"AI_TEXT"` for AI-driven text propagation |
| `priority` | **required** | Execution order (lower = higher priority) |
| `activate` | optional | `true` to activate immediately (default: `false`) |
| `isInheritable` | optional | Allow propagation to descendant layers |
| `isPropagatedToParent` | optional | Allow propagation to parent layer |
| `layerBindings` | **required** | Array of layer binding objects |
| `executor` | **required** | Executor configuration object |

### AI executor fields (`executorType: "AI_PROPAGATOR"`)

| Field | Required | Description |
|---|---|---|
| `executorType` | **required** | Must be `"AI_PROPAGATOR"` |
| `registrarPrompt` | **required** | Specific guidance explaining what this propagator should look for and why — distinct from the default OOD concern already covered by auto-registered propagators |
| `sessionMode` | optional | `PER_INVOCATION` \| `SAME_SESSION_FOR_ALL` \| `SAME_SESSION_FOR_ACTION` \| `SAME_SESSION_FOR_AGENT` |
| `configVersion` | optional | Version tag for tracking configuration changes |

The model used is always the system default — custom model selection is not supported.

### Layer binding fields

| Field | Type | Allowed values | Description |
|---|---|---|---|
| `layerId` | string | any valid layer ID | Which layer this binding targets |
| `matchOn` | **enum** | `"ACTION_REQUEST"`, `"ACTION_RESPONSE"`, `"PROMPT_CONTRIBUTOR"`, `"GRAPH_EVENT"` | What surface to intercept |
| `enabled` | boolean | `true`, `false` | Whether this binding is active |
| `includeDescendants` | boolean | `true`, `false` | Apply to child layers too |
| `isInheritable` | boolean | `true`, `false` | Allow one-shot propagation to descendant layers |
| `isPropagatedToParent` | boolean | `true`, `false` | Allow one-shot propagation to parent layer |
| `matcherKey` | **enum** | `"NAME"`, `"TEXT"` | What field to match against |
| `matcherType` | **enum** | `"REGEX"`, `"EQUALS"` | How to compare `matcherText` |
| `matcherText` | string | any string | Pattern or exact value to match |

## Execution Flow

1. A payload arrives at the bound attach point (`ACTION_REQUEST`, `ACTION_RESPONSE`, `PROMPT_CONTRIBUTOR`, or `GRAPH_EVENT`).
2. The propagator executor receives the payload as `AiPropagatorRequest`.
3. `LlmRunner.runWithTemplate()` is called with the `propagation/ai_propagator` template. The template receives the `registrarPrompt`, the payload, and upstream context. The full decorator chain (request, prompt-context, tool-context, result) is always applied.
4. If the AI decides escalation is warranted, it calls `AskUserQuestionTool` with its reasoning and requests acknowledgement.
5. Workflow execution pauses. The controller operator sees the interrupt in the pending interrupts list.
6. The operator acknowledges. Workflow resumes.

## Management Endpoints

Use `api_schema.py` from the `multi_agent_ide_api` skill. The discovery flow is progressive:

```bash
# Step 1: find what endpoints exist under /api/propagators
python scripts/api_schema.py --level 1 --path /api/propagators

# Step 2: list all endpoints under that path prefix
python scripts/api_schema.py --level 2 --path /api/propagators

# Step 3: get the full request/response schema for a specific endpoint
#         discovered in step 2, e.g. /api/propagators/registrations
python scripts/api_schema.py --level 3 --path /api/propagators/registrations
```

Start with `--level 1 --path /api/propagators` to confirm the path prefix matches the deployed version — if it returns nothing, broaden to `--level 1` with no path to find the right prefix. Once you have a specific endpoint path from `--level 2`, use `--level 3` scoped to that path to get its exact request/response schema before calling it.
