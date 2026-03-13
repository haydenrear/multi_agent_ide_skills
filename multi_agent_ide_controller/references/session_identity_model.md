# Session Identity Model: ArtifactKey, NodeId, and ACP Sessions

This reference describes how `ArtifactKey` values serve as the unified hierarchical identity for workflow nodes, agent sessions, messages, prompts, and all other artifacts, and how to send messages to the correct agent.

## Source of truth files

- ArtifactKey definition and hierarchy:
  - `multi_agent_ide_java_parent/acp-cdc-ai/src/main/java/com/hayden/acp_cdc_ai/acp/events/ArtifactKey.java`
- ACP session creation and message/stream key hierarchy:
  - `multi_agent_ide_java_parent/acp-cdc-ai/src/main/kotlin/com/hayden/acp_cdc_ai/acp/AcpChatModel.kt`
  - `multi_agent_ide_java_parent/acp-cdc-ai/src/main/kotlin/com/hayden/acp_cdc_ai/acp/AcpSessionManager.kt`
  - `multi_agent_ide_java_parent/acp-cdc-ai/src/main/kotlin/com/hayden/acp_cdc_ai/acp/AcpStreamWindowBuffer.kt`
- Session recycling and context ID resolution:
  - `multi_agent_ide_java_parent/multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/service/RequestEnrichment.java`
- Agent process creation and message routing:
  - `multi_agent_ide_java_parent/multi_agent_ide/src/main/java/com/hayden/multiagentide/infrastructure/AgentRunner.java`
- OutputChannel message dispatch (ArtifactKey -> ACP session):
  - `multi_agent_ide_java_parent/multi_agent_ide/src/main/java/com/hayden/multiagentide/config/MultiAgentEmbabelConfig.java`
- Artifact types (all keyed by ArtifactKey):
  - `multi_agent_ide_java_parent/acp-cdc-ai/src/main/java/com/hayden/acp_cdc_ai/acp/events/Artifact.java`
- Prompt/artifact emission with child keys:
  - `multi_agent_ide_java_parent/multi_agent_ide/src/main/java/com/hayden/multiagentide/agent/decorator/prompt/ArtifactEmissionLlmCallDecorator.java`

## ArtifactKey: the universal hierarchical index

`ArtifactKey` is used to index **everything** in the system, not just agent sessions. It is a hierarchical, time-sortable identifier where child keys represent nested artifacts within a parent scope.

Format: `ak:<ULID-segment>/<ULID-segment>/...`

- **Prefix**: always `ak:`
- **Segments**: 26-character ULID values (Crockford Base32, time-sortable)
- **Separator**: `/`
- **Hierarchy**: child keys are parent key + `/` + new ULID segment

Key operations:
- `ArtifactKey.createRoot()` - creates a new root key
- `parentKey.createChild()` - creates a child key under the parent
- `key.parent()` - returns the parent key (empty if root)
- `key.isDescendantOf(ancestor)` - checks ancestry
- `key.root()` - extracts the root segment

## Each agent has its own unique session key

Every agent action in the workflow gets its **own distinct `ArtifactKey`** as its session key (`chatModelKey`). These are all children of the root orchestrator key, but each agent has a different child segment:

```
ak:ROOT                   <- root orchestrator (chatModelKey for orchestrator session)
ak:ROOT/CHILD_A           <- discovery orchestrator (its own chatModelKey)
ak:ROOT/CHILD_B           <- discovery agent #1 (its own chatModelKey)
ak:ROOT/CHILD_C           <- discovery agent #2 (its own chatModelKey)
ak:ROOT/CHILD_D           <- discovery dispatch (its own chatModelKey)
ak:ROOT/CHILD_A           <- discovery collector (RECYCLED: reuses discovery orch's key)
ak:ROOT/CHILD_E           <- planning orchestrator (its own chatModelKey)
...
```

**Recycling** means that when the workflow routes back to the same agent type (e.g. discovery orchestrator on a `ROUTE_BACK`), it reuses **that agent's existing key** - not that agents share keys. The ACP session persists and new messages append to the existing conversation for that agent.

## Hierarchical ArtifactKey within a session

Within each agent's session, the `ArtifactKey` hierarchy continues downward. The agent's `chatModelKey` is the parent, and everything inside that session is a child:

```
ak:ROOT/CHILD_A                            <- agent session (chatModelKey)
ak:ROOT/CHILD_A/MSG_PARENT                 <- messageParent (created at session init)
ak:ROOT/CHILD_A/MSG_PARENT/STREAM_1        <- NodeStreamDeltaEvent (LLM output chunk)
ak:ROOT/CHILD_A/MSG_PARENT/STREAM_2        <- another stream delta
ak:ROOT/CHILD_A/PROMPT_1                   <- RenderedPromptArtifact
ak:ROOT/CHILD_A/PROMPT_1/TEMPLATE_VER      <- prompt template version (child of prompt)
ak:ROOT/CHILD_A/PROMPT_1/ARGS              <- prompt args artifact (child of prompt)
ak:ROOT/CHILD_A/PROMPT_1/CONTRIBUTOR_1     <- prompt contributor output (child of prompt)
ak:ROOT/CHILD_A/TOOL_CALL_1                <- ToolCallArtifact
```

This hierarchy is established in `AcpChatModel.createSessionContext`:
```kotlin
val chatKey = ArtifactKey(memoryId)       // the agent's session key
val messageParent = chatKey.createChild() // child key for messages in this session
```

The `AcpSessionContext` stores both:
- `chatModelKey` - the agent's session identity (used for routing messages to the ACP session)
- `messageParent` - child key under which stream deltas and messages are indexed

Similarly, `ArtifactEmissionLlmCallDecorator` creates child keys under the session for prompts, prompt template versions, prompt args, contributor outputs, tool calls, and evidence artifacts.

## Why this matters: only send messages to agent-level keys

**Critical**: When sending a message to an agent, you must target the **agent-level nodeId** (the `chatModelKey`), not any of its child keys. Child keys represent individual messages, prompts, stream deltas, tool calls, etc. - they are not agent sessions.

How to identify the correct key:
- `ACTION_STARTED` events contain the agent-level nodeId: `node=ak:ROOT/CHILD_A action=discovery-orchestrator`
- `CHAT_SESSION_CREATED` events expose the agent key via `chatSessionId / agentNodeId`: this is the `chatModelId` field, which is the agent-level key you can send messages to. Note: the `nodeId` field on this event is the `messageParent` (a child key), but the `chatModelId` / `chatSessionId` field is the correct agent-level key.
- `NODE_STREAM_DELTA` events are children of `messageParent`: `node=ak:ROOT/CHILD_A/MSG_PARENT/STREAM_1` (two levels below the agent key)

**Rule**: To send a message, use:
- The `node=` value from `ACTION_STARTED` or `NODE_ADDED` events, OR
- The `chatSessionId / agentNodeId` value from `CHAT_SESSION_CREATED` events (this is the `chatModelId`)

Never use the `nodeId` from `CHAT_SESSION_CREATED` (that's the `messageParent` child), `NODE_STREAM_DELTA` (grandchild), or `ARTIFACT_EMITTED` child artifacts.

## Session lifecycle: recycled vs new

### Recycled sessions (same agent reuses its own key on route-back)

These agent types **reuse their own previous ArtifactKey** (and therefore their own existing ACP session) when the workflow routes back to them:

| Agent Type | Action Name | Recycles Own Key? |
|---|---|---|
| Orchestrator | `orchestrator` | Yes |
| Discovery Orchestrator | `discovery-orchestrator` | Yes |
| Planning Orchestrator | `planning-orchestrator` | Yes |
| Ticket Orchestrator | `ticket-orchestrator` | Yes |
| Discovery Collector | `discovery-collector` | Yes |
| Planning Collector | `planning-collector` | Yes |
| Ticket Collector | `ticket-collector` | Yes |
| Orchestrator Collector | `orchestrator-collector` | Yes |
| Discovery Dispatch | `discovery-dispatch` | Yes |
| Planning Dispatch | `planning-dispatch` | Yes |
| Ticket Dispatch | `ticket-dispatch` | Yes |
| Review | `review-agent` | Yes |
| Merger | `merger-agent` | Yes |
| Context Manager | `context-manager` | Yes |

**Recycling logic** (from `RequestEnrichment.resolveContextId`):
1. Check `shouldCreateNewSession` - if false, attempt recycling
2. Look up the most recent request of the same type in `BlackboardHistory`
3. If found with a non-null `contextId`, reuse **that agent's own** `contextId`
4. Otherwise, generate a new child key under the root

### New sessions (always fresh ArtifactKey)

These **dispatched agent** types always get a **new** ArtifactKey (new ACP session) because multiple instances can run in parallel:

| Agent Type | Action Name | New Session? |
|---|---|---|
| Discovery Agent | `discovery-agent` | Always new |
| Planning Agent | `planning-agent` | Always new |
| Ticket Agent | `ticket-agent` | Always new |

**Decision logic** (from `RequestEnrichment.shouldCreateNewSession`):
```java
return model instanceof AgentModels.DiscoveryAgentRequest
    || model instanceof AgentModels.PlanningAgentRequest
    || model instanceof AgentModels.TicketAgentRequest;
```

These are the agents that run inside dispatch subprocesses (`WorkflowDiscoveryDispatchSubagent`, `WorkflowPlanningDispatchSubagent`, `WorkflowTicketDispatchSubagent`) and can have multiple concurrent instances per dispatch fan-out.

## How messages reach a specific agent

### Message flow: send-message -> ACP session

1. **Script call**: `quick_action.py send-message --node-id <nodeId> --message <text>`
2. **HTTP**: `POST /api/llm-debug/ui/quick-actions` with `{ actionType: "SEND_MESSAGE", nodeId, message }`
3. **Server**: Creates an `AddMessageEvent` with the `nodeId`
4. **AgentRunner**: Receives the event, calls `addMessageToAgent(message, nodeId)`
5. **OutputChannel**: `llmOutputChannel.send(new MessageOutputChannelEvent(nodeId, message))`
6. **MultiAgentEmbabelConfig OutputChannel handler**:
   - Parses `nodeId` as an `ArtifactKey`
   - Searches `ChatSessionCreatedEvent` records for a matching session
   - Finds the closest matching `chatModelId` by string proximity
   - Sets `EventBus.Process` thread-local to the matched session key
   - Calls `chatModel.call(new Prompt(...))` with the session key as the model name
   - The `AcpChatModel` routes this to the correct ACP session

### Session matching logic

The OutputChannel finds the target session by:
```java
graphRepository.getAllMatching(ChatSessionCreatedEvent.class, n -> matchesThisSession(evt, n))
    .min(Comparator.comparing(c -> c.chatModelId().value().replace(event.getProcessId(), "").length()))
    .map(ChatSessionCreatedEvent::chatModelId);
```

This finds `ChatSessionCreatedEvent` records where the `chatModelId` matches the `processId`, preferring the closest (shortest suffix difference) match.

## Practical guide for the supervisor skill

### Identifying agent-level keys from events

When polling events, different event types carry keys at different levels of the hierarchy:

| Event Type | Key Level | Safe to message? |
|---|---|---|
| `NODE_ADDED` | Agent node (`nodeId`) | Yes - use `nodeId` directly |
| `ACTION_STARTED` | Agent node (`nodeId`) | Yes - use `nodeId` directly |
| `NODE_STATUS_CHANGED` | Agent node (`nodeId`) | Yes - use `nodeId` directly |
| `CHAT_SESSION_CREATED` | `nodeId` = messageParent (child), but `chatSessionId/agentNodeId` = agent key | Yes - use the `chatSessionId / agentNodeId` field (not the `nodeId`) |
| `NODE_STREAM_DELTA` | Stream chunk (grandchild of agent) | No - this is a grandchild key |
| `ARTIFACT_EMITTED` | Varies (agent or child) | Check depth - only agent-level keys |

### Targeting the right agent

- To message the **orchestrator**: use the root nodeId (depth 1, e.g. `ak:ROOT`)
- To message a **phase orchestrator** (discovery/planning/ticket): use the child nodeId from that agent's `ACTION_STARTED` event (depth 2, e.g. `ak:ROOT/CHILD_A`)
- To message a **dispatched agent**: use the specific agent's nodeId from its `ACTION_STARTED` event (depth 2, e.g. `ak:ROOT/CHILD_B`) - these are always unique per dispatch

### Session recycling means conversation continuity

When an agent's session is recycled (route-back), the **same ArtifactKey** continues to identify that agent's session. The ACP session persists, so new messages append to the agent's existing conversation history. This means you can keep sending messages to a recycled orchestrator session across multiple routing loops without losing context.
