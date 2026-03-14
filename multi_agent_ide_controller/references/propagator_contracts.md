# Propagator Contracts

## Overview

Propagators observe action requests and responses as they flow through the workflow agent graph. Unlike filters (which transform or remove data), propagators **emit events** — they do not modify the payload. The typical use case is escalating controller-relevant information to a human or another process for review and acknowledgement.

An AI propagator intercepts the action payload, evaluates it against its `registrarPrompt`, and when it decides escalation is appropriate, uses the `AskUserQuestionTool` to push an acknowledgement request. Workflow execution pauses until the propagator interrupt is resolved.

## Propagator Match Points

Propagators bind to layer actions via `matchOn`, which determines whether the propagator intercepts the action **request** or the action **response**.

| `matchOn` value | When it fires | Payload seen |
|---|---|---|
| `ACTION_REQUEST` | Before the action executes | The action's input request object |
| `ACTION_RESPONSE` | After the action completes | The action's output result object |

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
| `layerBindings` | **required** | Array of layer binding objects (see below) |
| `executor` | **required** | Executor configuration object (see below) |

### AI executor fields (`executorType: "AI_PROPAGATOR"`)

| Field | Required | Description |
|---|---|---|
| `executorType` | **required** | Must be `"AI_PROPAGATOR"` |
| `registrarPrompt` | **required** | Guidance explaining what the propagator should escalate and why |
| `sessionMode` | optional | `PER_INVOCATION` \| `SAME_SESSION_FOR_ALL` \| `SAME_SESSION_FOR_ACTION` \| `SAME_SESSION_FOR_AGENT` |
| `configVersion` | optional | Version tag for tracking configuration changes |

The model used is always the system default — custom model selection is not supported.

### Layer binding fields

| Field | Type | Allowed values | Description |
|---|---|---|---|
| `layerId` | string | any valid layer ID | Which layer action this binding targets |
| `matchOn` | **enum** | `"ACTION_REQUEST"`, `"ACTION_RESPONSE"` | Whether to intercept the request or response side |
| `enabled` | boolean | `true`, `false` | Whether this binding is active |
| `includeDescendants` | boolean | `true`, `false` | Apply to child layers too |
| `isInheritable` | boolean | `true`, `false` | Allow one-shot propagation to descendant layers |
| `isPropagatedToParent` | boolean | `true`, `false` | Allow one-shot propagation to parent layer |
| `matcherKey` | **enum** | `"NAME"`, `"TEXT"` | What field to match against |
| `matcherType` | **enum** | `"REGEX"`, `"EQUALS"` | How to compare `matcherText` |
| `matcherText` | string | any string | Pattern or exact value to match |

## Propagator Interrupt Resolution

When an AI propagator decides to escalate, it raises an interrupt via `AskUserQuestionTool`. The controller polls for pending interrupts and the operator acknowledges or responds. The interrupt is resolved by sending an acknowledgement — no structured `resolutionNotes` object is required, just a plain acknowledgement.

### `PropagationResolutionType` enum

| Value | Meaning |
|---|---|
| `ACKNOWLEDGED` | Operator reviewed and acknowledged the escalation |
| `APPROVED` | Operator approved the escalated action/payload |
| `REJECTED` | Operator rejected the escalated action/payload |
| `DISMISSED` | Operator dismissed without taking action |
| `FEEDBACK` | Operator provided textual feedback back to the agent |

## Example Registration

```json
{
  "name": "out-of-domain-escalation",
  "description": "Escalates requests that appear out-of-domain or out-of-distribution",
  "sourcePath": "custom://ai-propagator/workflow-agent/coordinateWorkflow/request",
  "propagatorKind": "AI_TEXT",
  "priority": 100,
  "activate": true,
  "isInheritable": false,
  "isPropagatedToParent": false,
  "layerBindings": [
    {
      "layerId": "workflow-agent/coordinateWorkflow",
      "matchOn": "ACTION_REQUEST",
      "enabled": true,
      "includeDescendants": false,
      "isInheritable": false,
      "isPropagatedToParent": false,
      "matcherKey": "TEXT",
      "matcherType": "REGEX",
      "matcherText": "(?s).*"
    }
  ],
  "executor": {
    "executorType": "AI_PROPAGATOR",
    "sessionMode": "SAME_SESSION_FOR_ACTION",
    "registrarPrompt": "Escalate out-of-domain, out-of-distribution, or otherwise controller-relevant request and result payloads."
  }
}
```

## Execution Flow

1. An action fires at the bound layer (request or response side per `matchOn`).
2. The propagator executor receives the payload as `AiPropagatorRequest`.
3. `LlmRunner.runWithTemplate()` is called with the `propagation/ai_propagator` template, which includes the `registrarPrompt`, the payload text, and the full decorator chain (request, prompt-context, tool-context, result) keyed to agent `ai-propagator`.
4. If the AI decides escalation is warranted, it calls `AskUserQuestionTool` which raises an interrupt.
5. Workflow execution pauses. The controller operator sees the interrupt in the pending interrupts list.
6. The operator acknowledges the interrupt. Workflow resumes.

## Management Endpoints

| Action | Method | Path |
|---|---|---|
| Register propagator | POST | `/api/propagators/registrations` |
| Deactivate propagator | POST | `/api/propagators/registrations/{registrationId}/deactivate` |
| Update layer binding | PUT | `/api/propagators/registrations/{registrationId}/layer-bindings` |
| List registered propagators | GET | `/api/propagators/registrations` |
| Read attachable targets | GET | `/api/propagators/attachable-targets` |
