# Workflow Position and Branching Guide

This guide captures the workflow-position guidance injected into runtime prompts so you can reason about routing without opening source code.

## Source of truth files

- Core routing/model contracts:
  - `multi_agent_ide_java_parent/multi_agent_ide/src/main/java/com/hayden/multiagentide/agent/AgentInterfaces.java`
  - `multi_agent_ide_java_parent/multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/agent/AgentModels.java`
- Planner/action resolution:
  - `multi_agent_ide_java_parent/multi_agent_ide/src/main/java/com/hayden/multiagentide/config/BlackboardRoutingPlanner.java`
- Context reconstruction and memory tools:
  - `multi_agent_ide_java_parent/multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/agent/ContextManagerTools.java`
  - `multi_agent_ide_java_parent/multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/agent/BlackboardHistory.java`
- Workflow-position contributor implementation:
  - `multi_agent_ide_java_parent/multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/prompt/contributor/WeAreHerePromptContributor.java`

Use these when you need to augment routing structure, add branches, or validate that this guide still matches runtime behavior.

## Action resolution model (SomeOf/Routing -> next action)

- A routing result record is a SomeOf-style container: each nullable field is a possible next request.
- The planner (`BlackboardRoutingPlanner`) unwraps the first non-null field from the routing record.
- That unwrapped request object is matched by input type to the next Embabel action.
- In practice, exactly one route field should be non-null for deterministic flow.

## Context-manager recovery path

- Trigger:
  - a routing result selects `contextManagerRequest`, or stuck-handler invokes context-manager recovery.
- Compute context from shared memory:
  - Context manager uses `ContextManagerTools` to query `BlackboardHistory` (`trace/list/search/message events/item`).
  - Blackboard history includes both agent request/results entries and message/event stream entries.
- Return:
  - context manager emits `ContextManagerResultRouting` with one non-null return route to resume normal flow.
- Guardrails:
  - repeated loop patterns are detectable via `BlackboardHistory.detectLoop` (thresholded),
  - stuck-handler has capped retries before no-resolution behavior.

## Subgraph intuition (important mental model)

Think of the workflow as nested subgraphs, not a single flat chain.

- Top-level macro graph:
  - `Orchestrator`
  - `Discovery` subgraph
  - `Planning` subgraph
  - `Ticket` subgraph
  - `OrchestratorCollector`
- Each phase subgraph follows a repeating shape:
  - `PhaseOrchestrator` -> `PhaseDispatch` -> `PhaseAgent(s)` -> `PhaseCollector`
- Dispatch nodes can fan out to multiple agents (one-to-many), then collapse back through collector nodes.
- The top-level orchestrator/collector pair behaves like the parent control subgraph, while Discovery/Planning/Ticket are nested execution subgraphs.

## Main workflow spine

1. Orchestrator
2. Discovery Orchestrator
3. Discovery Agent Dispatch
4. Discovery Agents
5. Discovery Collector
6. Planning Orchestrator
7. Planning Agent Dispatch
8. Planning Agents
9. Planning Collector
10. Ticket Orchestrator
11. Ticket Agent Dispatch
12. Ticket Agents
13. Ticket Collector
14. Orchestrator Collector
15. Complete

## Routing fields by stage (high-value view)

### Orchestrator
- `interruptRequest`
- `collectorRequest`
- `orchestratorRequest` (typically enters discovery)
- `contextManagerRequest`

### Discovery Orchestrator
- `interruptRequest`
- `agentRequests` (dispatch discovery)
- `collectorRequest`
- `contextManagerRequest`

### Discovery Agent Dispatch / Discovery Agent
- dispatch -> `collectorRequest` or `interruptRequest` or `contextManagerRequest`
- agent -> `agentResult` or `interruptRequest` or `contextManagerRequest`

### Discovery Collector
- `collectorResult` is the normal branch trigger:
  - `ADVANCE_PHASE` -> planning request
  - `ROUTE_BACK` -> discovery request
- also may route to orchestrator/review/merger/context manager

### Planning Orchestrator
- `interruptRequest`
- `agentRequests` (dispatch planning)
- `collectorRequest`
- `contextManagerRequest`

### Planning Agent Dispatch / Planning Agent
- dispatch -> planning collector request
- agent -> `agentResult`
- both support interrupt/context-manager routes

### Planning Collector
- `collectorResult` branch:
  - `ADVANCE_PHASE` -> ticket orchestrator request
  - `ROUTE_BACK` -> planning request
- can also route to discovery/orchestrator collector/review/merger/context manager

### Ticket Orchestrator
- `interruptRequest`
- `agentRequests` (dispatch ticket execution)
- `collectorRequest`
- `contextManagerRequest`

### Ticket Agent Dispatch / Ticket Agent
- dispatch -> ticket collector request
- agent -> `agentResult`
- both support interrupt/context-manager routes

### Ticket Collector
- `collectorResult` branch:
  - `ADVANCE_PHASE` -> orchestrator collector request
  - `ROUTE_BACK` -> ticket request
- can also route to review/merger/context manager

### Orchestrator Collector
- `collectorResult` branch:
  - `ADVANCE_PHASE` -> complete workflow
  - `ROUTE_BACK` -> orchestrator request (phase restart/refinement)
- can also route to discovery/planning/ticket/review/merger/context manager

## Side nodes

### Review
- returns to one collector (`orchestrator`, `discovery`, `planning`, or `ticket`)
- supports interrupt/context-manager routes

### Merger
- returns to one collector (`orchestrator`, `discovery`, `planning`, or `ticket`)
- supports interrupt/context-manager routes

### Context Manager
- recovery/re-entry router
- can route to orchestrators, collectors, dispatch nodes, individual agents, review, or merger
- should normally carry one dominant return target

## Runtime markers and loop hints

- Current node marker: `>>> [Node] <<< YOU ARE HERE`
- Previously visited node marker: `[visited]`
- Execution history table includes action + input type
- Loop warning appears when the same request type appears repeatedly in one run

## How to use this during debugging

1. Poll with `quick_action.py poll-events --node-id <nodeId>`.
2. Expand suspect events with `quick_action.py event-detail --node-id <nodeId> --event-id <eventId>`.
3. Map current request type to expected next branch fields.
4. If branch choice diverges repeatedly, inspect prompt template/contributor context before changing code flow.
