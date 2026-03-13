# Program model and routing

This is a compact map of how the multi-agent workflow is modeled and routed.
Source files:
- `multi_agent_ide_java_parent/multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/agent/AgentModels.java`
- `multi_agent_ide_java_parent/multi_agent_ide/src/main/java/com/hayden/multiagentide/agent/AgentInterfaces.java`
- `multi_agent_ide_java_parent/multi_agent_ide/src/main/java/com/hayden/multiagentide/config/BlackboardRoutingPlanner.java`
- `multi_agent_ide_java_parent/multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/agent/ContextManagerTools.java`
- `multi_agent_ide_java_parent/multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/agent/BlackboardHistory.java`

## Core contracts

- `AgentRequest`:
  - Sealed request model for workflow nodes.
  - Happy-path request ordering is documented in the `permits` block comment in `AgentModels`.
- `Routing`:
  - Sealed `SomeOf` container for route decisions.
  - Non-null fields are candidate next routes; routing types do not execute work directly.
- `BlackboardRoutingPlanner`:
  - Resolves the next action from blackboard `lastResult()` type.
  - If `lastResult` is `AgentModels.Routing`, it extracts the first non-null record field before action matching.
  - Action selection then matches resolved type to action input bindings.
- `InterruptRequest`:
  - Typed interrupt request exists for orchestrators, collectors, dispatch, and side agents.
  - Interrupt handlers resume through `interruptService.handleInterrupt(...)`.
- `CollectorDecision`:
  - `decisionType` is one of `ADVANCE_PHASE`, `ROUTE_BACK`, `STOP`.
  - Collector branch handlers convert this into concrete routing requests.

## Main workflow spine

1. `OrchestratorRequest` → `OrchestratorRouting`
2. `DiscoveryOrchestratorRequest` → `DiscoveryOrchestratorRouting`
3. `DiscoveryAgentRequests` (dispatch) → `DiscoveryAgentDispatchRouting`
4. `DiscoveryAgentRequest` (subagents) → `DiscoveryAgentRouting`
5. `DiscoveryCollectorRequest` → `DiscoveryCollectorRouting`
6. `PlanningOrchestratorRequest` → `PlanningOrchestratorRouting`
7. `PlanningAgentRequests` (dispatch) → `PlanningAgentDispatchRouting`
8. `PlanningAgentRequest` (subagents) → `PlanningAgentRouting`
9. `PlanningCollectorRequest` → `PlanningCollectorRouting`
10. `TicketOrchestratorRequest` → `TicketOrchestratorRouting`
11. `TicketAgentRequests` (dispatch) → `TicketAgentDispatchRouting`
12. `TicketAgentRequest` (subagents) → `TicketAgentRouting`
13. `TicketCollectorRequest` → `TicketCollectorRouting`
14. `OrchestratorCollectorRequest` → `OrchestratorCollectorRouting`
15. Complete or route back.

Side nodes available from collectors and routing:
- `ReviewRequest` → `ReviewRouting`
- `MergerRequest` → `MergerRouting`
- `ContextManagerRequest` → `ContextManagerResultRouting`
- `ContextManagerRoutingRequest` → routes to context manager for intra-agent context reconstruction
- `CommitAgentRequest` → `CommitAgentResult` (git commit before merge)
- `MergeConflictRequest` → `MergeConflictResult` (git merge conflict resolution)

## Git commit and merge conflict workflow

The merge pipeline has two specialized request types that handle git operations:

### CommitAgentRequest
- Triggered when a ticket agent's worktree changes need to be committed before merge.
- Carries `sourceAgentType` to identify which agent produced the changes.
- Uses prompt template `workflow/worktree_commit_agent.jinja`.
- Returns `CommitAgentResult` with `successful`, `output`, and `commitMetadata`.

### MergeConflictRequest
- Triggered when a merge between worktrees (child→trunk or trunk→child) encounters conflicts.
- Carries `mergeDirection` and `conflictFiles` describing the exact conflicts.
- Uses prompt template `workflow/worktree_merge_conflict_agent.jinja`.
- Returns `MergeConflictResult` with `successful`, `output`, and `resolvedConflictFiles`.

Both types are part of the dispatch→collect→merge flow:
1. Ticket agent completes work in a child worktree.
2. `CommitAgentRequest` commits the changes.
3. Merge phase begins (`MergePhaseStartedEvent`).
4. If conflicts arise, `MergeConflictRequest` is issued.
5. After resolution, `MergePhaseCompletedEvent` records the outcome.

## Review and review route-back workflow

Review is a side node that can be invoked by any collector when quality gates are needed.

### ReviewRequest → ReviewRouting
- `ReviewRequest` carries `content`, `criteria`, and the context to review.
- `performReview()` in `AgentInterfaces` executes the review agent.
- Uses prompt template `workflow/review.jinja`.
- Returns `ReviewRouting`, which can route to:
  - `interruptRequest` (`ReviewInterruptRequest`) — escalate to human/controller for approval
  - `reviewResult` (`ReviewAgentResult`) — review completed, carry result forward
  - Any collector route (`orchestratorCollectorRequest`, `discoveryCollectorRequest`, `planningCollectorRequest`, `ticketCollectorRequest`) — route back to the originating collector
  - `contextManagerRequest` — route to context manager

### Review resolution route-back
- When a review result routes back to a collector, the collector uses `review_resolution.jinja` to interpret the review feedback.
- The `@ReviewRoute` annotation marks routing fields that represent review-initiated route-backs.
- This allows the workflow to loop: collector → review → route back to collector with feedback → re-run or advance.

### MergerRequest → MergerRouting
- `MergerRequest` carries `mergeSummary`, `conflictFiles`, and merge context.
- `performMerge()` executes the merger agent with template `workflow/merger.jinja`.
- `MergerRouting` mirrors `ReviewRouting` shape: can route to interrupt, result, any collector, or context manager.

## Unified interrupt handling

`handleUnifiedInterrupt()` provides a single action method for all interrupt types:
- Receives any `InterruptRequest` variant (orchestrator, collector, dispatch, agent, review, merger, context manager, Q&A).
- Returns `InterruptRouting`, which can route back to any phase: `orchestratorRequest`, `discoveryOrchestratorRequest`, `planningOrchestratorRequest`, `ticketOrchestratorRequest`, or any collector.
- The `InterruptRouteConfig` determines which phase to return to based on the interrupt's origin.

### QuestionAnswerInterruptRequest
- Used by AI propagators when they escalate via `AskUserQuestionTool`.
- The QA tool is fundamentally an **acknowledgement mechanism** — the propagator surfaces something noteworthy and the controller/human confirms awareness or provides structured input.
- Carries `type`, `reason`, `choices` (structured options), and `confirmationItems`.
- Resolved via `POST /api/interrupts/resolve` with `InterruptResolution` serialized in `resolutionNotes`.

## Data-layer policy subsystem: filters, transformers, propagators

The data-layer policy subsystem provides three interception mechanisms that operate on events and prompts as they flow through the system. These are **not** part of the agent routing — they operate at the infrastructure layer.

### Filters
- **Purpose**: Suppress, modify, or conditionally remove events and prompt contributions before they reach their destination.
- **Request type**: `AiFilterRequest` → `AiFilterResult` (for AI-powered filter logic).
- **Controller**: `FilterPolicyController` at `/api/filters/`.
- **Produces**: `Instruction` objects (see `multi_agent_ide_validate_schema` for the contract).
- **Event**: `AiFilterSessionEvent` in the event stream.

### Transformers
- **Purpose**: Transform controller endpoint responses before they are returned to the caller. Used to reshape, summarize, or annotate API output.
- **Request type**: `AiTransformerRequest` → `AiTransformerResult`.
- **Controller**: `TransformerController` at `/api/transformers/`, `TransformationRecordController` at `/api/transformations/records`.
- **Event**: `TransformationEvent` in the event stream (action, controllerId, endpointId).

### Propagators
- **Purpose**: Extract **out-of-domain (OOD) and out-of-distribution signals** from agent execution and escalate them to the controller or human. Propagators are the escalatory mechanism — when one fires, it means the agent encountered something noteworthy: a deviation from expected behavior, a decision point, or information that should propagate up the supervision hierarchy.
- **Request type**: `AiPropagatorRequest` → `AiPropagatorResult`.
- **Controller**: `PropagatorController` at `/api/propagators/`, `PropagationController` at `/api/propagations/items`, `PropagationRecordController` at `/api/propagations/records`.
- **Event**: `PropagationEvent` in the event stream (stage, action, sourceName, payloadType).
- **Key insight**: Propagation events are among the most informative signals in the entire system. They reveal what agents are actually deciding, where they deviate from expected patterns, and when they need human input on novel situations.

### Executables as a promotion pipeline
Controller executables (Python scripts in `executables/`) are the **first step in a promotion pipeline** toward becoming formal filters, transformers, or propagators. The workflow is:
1. During controller sessions, write ad-hoc Python scripts to process polled results, parse events, or analyze patterns.
2. If a script proves useful across multiple sessions, it's a candidate for promotion.
3. **Promote to filter**: If the script suppresses/modifies events → register it as a filter policy via the filter API.
4. **Promote to transformer**: If the script reshapes API responses → register it as a transformer.
5. **Promote to propagator**: If the script detects noteworthy patterns worth escalating → register it as a propagator.

## Collector branch handler behavior

### Discovery collector branch (`handleDiscoveryCollectorBranch`)
- `ROUTE_BACK` → `discoveryRequest`
- `ADVANCE_PHASE` → `planningRequest` (includes discovery curation)
- `STOP` → `orchestratorRequest`

### Planning collector branch (`handlePlanningCollectorBranch`)
- `ROUTE_BACK` → `planningRequest`
- `ADVANCE_PHASE` → `ticketOrchestratorRequest` (includes discovery + planning curation)
- `STOP` → `orchestratorCollectorRequest`

### Ticket collector branch (`handleTicketCollectorBranch`)
- `ROUTE_BACK` → `ticketRequest`
- `ADVANCE_PHASE` → `orchestratorCollectorRequest`
- `STOP` → `orchestratorCollectorRequest`

### Orchestrator collector branch (`handleOrchestratorCollectorBranch`)
- `ROUTE_BACK` → `orchestratorRequest` (can carry discovery/planning/ticket curation)
- `ADVANCE_PHASE` → `collectorResult` (progress/complete signal)
- `STOP` → `collectorResult` (stop signal)

## Context manager behavior

- `routeToContextManager(...)` creates `ContextManagerRequest` from the last non-context request.
- `ContextManagerRoutingRequest` is a lighter routing-only variant for intra-agent context reconstruction.
- Default type is `INTROSPECT_AGENT_CONTEXT` if unspecified.
- `ContextManagerRequest` carries many `returnTo*` fields; it is the re-entry router for interrupted or degraded flow.
- Guidance in prompt contributor expects exactly one active `returnTo*` route when possible.
- `contextManagerRequest(...)` and stuck-handler recovery run with `ContextManagerTools` attached in tool context.

## Context manager tools and shared memory

Context-manager tool surface (`ContextManagerTools`):
- `traceHistory(actionName?, inputTypeFilter?)`
- `listHistory(offset, limit, time filters, action filter)`
- `searchHistory(query, maxResults, entryId?)`
- `listMessageEvents(entryId, offset, limit)`
- `getHistoryItem(index)`
- `addHistoryNote(entryIndices, noteContent, tags)`

Memory model (`BlackboardHistory`):
- History is attached to the agent process and subscribed to graph events.
- It stores both action inputs (`DefaultEntry`) and grouped message/event streams (`MessageEntry`).
- Events are classified by node/parent targets so context can be reconstructed across the execution tree.
- Context-manager tools resolve the root session/node id and query this shared history.

## Stuck-loop guardrails

- `handleStuck(...)` triggers context-manager recovery.
- Max stuck handler invocations is `3` (`MAX_STUCK_HANDLER_INVOCATIONS`).
- Degenerate/invalid states throw via `degenerateLoop(...)`, which also emits error events.
- `BlackboardHistory.detectLoop(...)` uses repeated type counts (default threshold `3`) to detect loop-like behavior.

## Dispatch subagents and merge phase

Dispatch subagents:
- `WorkflowDiscoveryDispatchSubagent`
- `WorkflowPlanningDispatchSubagent`
- `WorkflowTicketDispatchSubagent`

Pattern:
1. Dispatch request list to subagent subprocesses.
2. Build `*AgentResults`.
3. Apply `ResultsRequestDecorator` chain (child → trunk merge phase).
4. Route via dispatch template to corresponding collector request.

## Prompt templates used by workflow actions

Main templates (from `AgentInterfaces` constants, all `.jinja` extension):

Core:
- `workflow/orchestrator.jinja`
- `workflow/orchestrator_collector.jinja`

Discovery phase:
- `workflow/discovery_orchestrator.jinja`
- `workflow/discovery_dispatch.jinja`
- `workflow/discovery_agent.jinja`
- `workflow/discovery_collector.jinja`

Planning phase:
- `workflow/planning_orchestrator.jinja`
- `workflow/planning_dispatch.jinja`
- `workflow/planning_agent.jinja`
- `workflow/planning_collector.jinja`

Ticket phase:
- `workflow/ticket_orchestrator.jinja`
- `workflow/ticket_dispatch.jinja`
- `workflow/ticket_agent.jinja`
- `workflow/ticket_collector.jinja`

Review and merge:
- `workflow/review.jinja`
- `workflow/review_resolution.jinja` (review route-back interpretation)
- `workflow/merger.jinja`

Git/worktree operations:
- `workflow/worktree_commit_agent.jinja`
- `workflow/worktree_merge_conflict_agent.jinja`

Context manager:
- `workflow/context_manager.jinja`
- `workflow/context_manager_interrupt.jinja`

Shared partials:
- `workflow/_collector_base.jinja`
- `workflow/_context_manager_body.jinja`
- `workflow/_interrupt_guidance.jinja`

Prompt template file location:
- `multi_agent_ide_java_parent/multi_agent_ide/src/main/resources/prompts/workflow`

## Prompt extension architecture (summary)

- `PromptContext` carries runtime prompt inputs (`currentRequest`, `previousRequest`, `blackboardHistory`, upstream/previous context, metadata/model).
- `PromptContextFactory` builds `PromptContext` from typed `AgentModels.AgentRequest` and populates contributors.
- `PromptContributorService` merges:
  - registry contributors (`PromptContributor` beans),
  - dynamic contributors from all `PromptContributorFactory` beans.
- Contributors are sorted by `priority` and injected into the LLM call.
- `AgentInterfaces.decoratePromptContext(...)` then applies ordered `PromptContextDecorator` beans before execution.
- New dynamic guidance is added by creating a new `PromptContributorFactory`; no manual wiring is needed.

Key prompt architecture locations:
- `multi_agent_ide_java_parent/multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/prompt/PromptContext.java`
- `multi_agent_ide_java_parent/multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/prompt/PromptContextFactory.java`
- `multi_agent_ide_java_parent/multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/prompt/PromptContributorService.java`
- `multi_agent_ide_java_parent/multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/prompt/contributor/ArtifactKeyPromptContributorFactory.java`
- `multi_agent_ide_java_parent/multi_agent_ide/src/main/java/com/hayden/multiagentide/agent/decorator/prompt/PromptContextDecorator.java`

See `references/prompt_architecture.md` for concrete extension steps and file paths.

## Event formatting: CliEventFormatter

Source: `multi_agent_ide_java_parent/multi_agent_ide/src/main/java/com/hayden/multiagentide/cli/CliEventFormatter.java`

`CliEventFormatter` renders `GraphEvent` instances into human-readable text for the Debug UI controller endpoints. Key behaviors:

- **Truncation**: All field values are truncated to `MAX_FIELD_LENGTH` (default `160` characters) via `summarize()`. When viewing events through `/api/ui/nodes/events`, payloads are abbreviated.
- **Disable truncation**: Pass any negative value (e.g. `-1`) for `maxFieldLength` or `truncate` to disable truncation entirely and return the full untruncated body. `0` is treated as the endpoint default.
- **CliEventArgs**: Controls formatting — `maxFieldLength` (override truncation limit; negative = no truncation), `prettyPrint` (multi-line indented output), `layerId` (apply layer-specific filters).
- **Event detail**: `/api/ui/nodes/events/detail` uses a higher default `maxFieldLength` of `20000` and supports `pretty` mode. Positive values are clamped to `[120, 80000]`.
- **Event list**: `/api/ui/nodes/events` uses a `truncate` parameter (default `180`, positive values clamped to `[80, 10000]`) for the summary field.
- **Filter integration**: Events pass through `ControllerEventFilterIntegration` (can suppress events entirely) and `PathFilterIntegration` (can modify text payloads) before formatting.
- **Propagation special case**: `PropagationEvent` payloads auto-expand to full `prettyPrint()` length regardless of `maxFieldLength` (when `maxFieldLength` is positive).

## Runtime interpretation tips

- If a routing response sets multiple route fields, treat that as ambiguous and inspect event detail plus prompt context.
- If repeated visits occur for the same request type with no new collector advance, suspect loop/regression.
- Keep `nodeId` stable across one debug run; all descendants belong to the same execution scope.

## How next action is chosen (Embabel planner path)

Source:
- `multi_agent_ide_java_parent/multi_agent_ide/src/main/java/com/hayden/multiagentide/config/BlackboardRoutingPlanner.java`

Routing sequence:
1. Planner reads `lastResult()` from blackboard world state.
2. If `lastResult` implements `AgentModels.Routing`, planner extracts first non-null record component.
3. Planner applies special branch handling for `OrchestratorCollectorResult` decision types.
4. Planner picks the first action whose input binding type matches resolved object type.
5. That selected action method in `AgentInterfaces` executes next.

Practical implication:
- Routing records should normally have exactly one non-null route field.
- Multiple non-null route fields can cause ambiguous behavior and planner errors.
- Context-manager recovery decisions should emit one non-null return route field after history reconstruction.
