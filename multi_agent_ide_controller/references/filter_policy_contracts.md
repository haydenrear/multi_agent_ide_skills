# Filter Policy Contracts

> **Schemas live in `multi_agent_ide_contracts`** — load that skill for:
> - `Instruction` JSON schema (op, targetPath, matcher, value, order)
> - Path type semantics (`REGEX`, `JSON_PATH`, `MARKDOWN_PATH`)
> - Matcher enums (`matcherKey`, `matcherType`, `matchOn`)
> - Python filter function contract and templates
>
> Reference file: `multi_agent_ide_contracts/references/filter_instruction_contract.schema.md`
>
> Always validate against the Java source before relying on any enum value — see `multi_agent_ide_contracts/SKILL.md` for the source file index.

---

## Overview

Data-layer filters use **instruction-based path filtering**. A Python script receives a serialized domain object and returns a JSON list of instructions that describe how to transform or remove it.

- **Graph events** → string filtering over either controller-formatted event text (`MARKDOWN_PATH` / `REGEX`) or serialized stream JSON (`JSON_PATH` / `REGEX`)
- **Prompt contributors** → string filtering over contributor text (`MARKDOWN_PATH` / `REGEX`)
- `AI_PATH` is a filter kind, not a `targetPath.pathType`; AI executors still return instructions whose `targetPath.pathType` is `REGEX`, `JSON_PATH`, or `MARKDOWN_PATH`

## AI Executor Registration

Dedicated registration endpoint: `POST /api/filters/ai-path-filters/policies`

When registering `executorType=AI`:

| Field | Required | Description |
|---|---|---|
| `executorType` | **required** | Must be `"AI"` |
| `registrarPrompt` | **required** | Guidance explaining the filter's purpose — what it should act on and why |
| `sessionMode` | optional | `PER_INVOCATION` \| `SAME_SESSION_FOR_ALL` \| `SAME_SESSION_FOR_ACTION` \| `SAME_SESSION_FOR_AGENT` |
| `configVersion` | optional | Version tag for tracking configuration changes |

**Operational notes:**
- External `PYTHON` and `BINARY` executors launch with `filter.bins` as subprocess cwd. In local/tmp deployments, `filter.bins` resolves to `<tmp-repo>/multi_agent_ide_java_parent/multi_agent_ide/bin` — ensure this directory exists before testing external executors.
- Prompt-contributor `AI_PATH` works. Graph-event `AI_PATH` requires the filter context to resolve both `PromptContext` and `OperationContext` — when unavailable, execution is skipped with PASSTHROUGH.
- AI filters require an `OperationContext` traceable to an agent process; when unavailable, execution is skipped.

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

| Operation | Method | Path |
|---|---|---|
| Register event filter | POST | `/api/filters/json-path-filters/policies` |
| Register prompt filter | POST | `/api/filters/markdown-path-filters/policies` |
| List policies for layer | GET | `/api/filters/layers/{layerId}/policies` |
| Deactivate policy | POST | `/api/filters/policies/{policyId}/deactivate` |
| Toggle policy on layer | POST | `/api/filters/policies/{policyId}/layers/{layerId}/enable` or `disable` |
| View filtered records | GET | `/api/filters/policies/{policyId}/layers/{layerId}/records/recent` |
| List layer children | GET | `/api/filters/layers/{layerId}/children` |
