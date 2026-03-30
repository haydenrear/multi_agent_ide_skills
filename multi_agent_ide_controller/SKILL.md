---
name: multi_agent_ide_controller
description: Executable workflow skill for the full multi_agent_ide controller loop — polling, graph inspection, permission/interrupt resolution, and self-improvement. References multi_agent_ide_deploy, multi_agent_ide_api, multi_agent_ide_debug, and multi_agent_ide_contracts skills.
---

**Load these companion skills before starting a controller session:**
- `multi_agent_ide_deploy` — deploy/sync the application
- `multi_agent_ide_api` — **required for all API interaction**: use `scripts/api_schema.py` to discover endpoint shapes before every new curl call. Covers goal submission, propagator/filter/transformer registration, schema introspection. Never guess field names — always check the live schema first.
- `multi_agent_ide_debug` — **required for all log searching**: use `executables/error_search.py` for structured error search (summary + detail modes). Never grep log files directly.
- `multi_agent_ide_contracts` — internal contract reference for types not in OpenAPI (Instruction sealed interface, resolution enums, propagation types, filter/transformer/propagator request shapes); validate before use, update if out of sync
- `multi_agent_ide_ui_test` — (optional) only if you need TUI state inspection or UI-level actions

---

## API operations — always use multi_agent_ide_api for schema discovery

Before constructing **any** API call, run `api_schema.py` from the `multi_agent_ide_api` skill to get the live request/response shape. Never guess field names.

```bash
# Discover all API groups
python skills/multi_agent_ide_skills/multi_agent_ide_api/scripts/api_schema.py

# Get endpoint list for a group
python skills/multi_agent_ide_skills/multi_agent_ide_api/scripts/api_schema.py --level 2 --tag "Debug UI"

# Get full request/response shapes for a group
python skills/multi_agent_ide_skills/multi_agent_ide_api/scripts/api_schema.py --level 3 --tag "Propagators"
```

### Common controller operations and their endpoints

| Operation | Method + Path | Schema source |
|-----------|--------------|---------------|
| **Submit a goal** | `POST /api/ui/goals/start` | `api_schema.py --level 3 --tag "Debug UI"` |
| **Poll workflow graph** | `POST /api/ui/workflow-graph` | same |
| **Send message to agent** | `POST /api/ui/quick-actions` | same |
| **List propagator registrations** | `POST /api/propagators/registrations/by-layer` | `api_schema.py --level 3 --tag "Propagators"` |
| **Register a propagator** | `POST /api/propagators/registrations` | same |
| **List propagation records** | `GET /api/propagations/records` | `api_schema.py --level 3 --tag "Propagation Records"` |
| **List pending propagation items** | `GET /api/propagations/items` | `api_schema.py --level 3 --tag "Propagation Items"` |
| **List pending permissions** | `GET /api/permissions/pending` | `api_schema.py --level 3 --tag "Permissions"` |
| **Resolve permission** | `POST /api/permissions/resolve` | same |
| **List pending interrupts** | `GET /api/interrupts/pending` | `api_schema.py --level 3 --tag "Interrupts"` |
| **Resolve interrupt** | `POST /api/interrupts/resolve` | same |

> **IMPORTANT:** The paths above are best-effort references. Always verify against the live spec before use. If a call returns an unexpected response, run `api_schema.py --level 3` for that tag to get the current shape.

---

## Kill running goals before fixing bugs

**When you discover a bug in a running workflow (wrong output, null fields, misrouted data), kill the goal immediately before investigating or fixing:**

```bash
# Kill the running app to stop spending money on a broken run
python skills/multi_agent_ide_skills/multi_agent_ide_deploy/scripts/deploy_restart.py --kill-only
# OR: send SIGTERM directly using the PID file
kill $(cat /private/tmp/multi_agent_ide_parent/multi_agent_ide.pid)
```

Do not let the agent continue running while you diagnose — every LLM call costs money and produces output you will not use. Fix the code, redeploy, and start a fresh goal.

---

## Operating mode

This skill is a self-improving loop. There are several workflow variants in `workflows/`, which are constantly refined and improved across sessions — see `workflows/reference.md` for the full index. The **standard workflow** (`workflows/standard_workflow.md`) is the best place to start; it covers the canonical step-by-step loop from deploy through polling and blocked-state resolution.

> All detailed step-by-step operating instructions live in the workflow files. Follow them rather than re-deriving the loop from scratch each session.

## Propagator escalation: the most informative signal

**Propagators are the escalatory mechanism for extracting out-of-domain (OOD) and out-of-distribution signals from agent execution.** When a propagator fires, it means the running agent encountered something noteworthy — a deviation from expected behavior, a decision point requiring controller awareness, or information that should propagate up the supervision hierarchy.

The propagation event stream reveals:
- What agents are actually deciding and why
- Where they deviate from expected patterns
- When they need human/controller input on novel situations
- How action requests and results flow through the system

**Key endpoints for propagation monitoring:**
- `POST /api/ui/nodes/events` (filter to PROPAGATION type) — see propagation events in the node stream
- `POST /api/ui/nodes/events/detail` — full propagated request/response payload
- `GET /api/propagations/items` — pending items needing resolution
- `POST /api/propagations/items/{itemId}/resolve` — resolve escalations

When a propagator escalates via `AskUserQuestionTool`, resolve via `POST /api/interrupts/resolve`. The primary action is **acknowledgement** — confirm awareness of the escalated signal. The `resolutionNotes` field can carry additional context but is not expected to contain a structured response; the propagator is reporting an observation, not waiting for a command. See `multi_agent_ide_contracts` for the interrupt resolution types.

## Domain references (load first)

Read these before starting a controller session:

| Reference | Purpose |
|-----------|---------|
| `references/program_model.md` | AgentModels routing, phase transitions, collector branching |
| `references/session_identity_model.md` | ArtifactKey hierarchy, recycled vs new sessions, message targeting |
| `references/prompt_architecture.md` | Prompt assembly, contributor contracts, extensibility |
| `references/we_are_here_prompt.md` | Current prompt state and design rationale |
| `references/filter_policy_contracts.md` | Data-layer filter instruction set, matcher fields, Python templates |

## Program context summary

- Treat routing records as decision containers: non-null fields represent the requested next route.
- `CollectorDecision` is the primary branch trigger (`ADVANCE_PHASE`, `ROUTE_BACK`, `STOP`) and is interpreted by collector branch handlers.
- `nodeId` is the root execution key; descendants are part of the same run scope.
- Source-of-truth implementation files:
  - `multi_agent_ide_java_parent/multi_agent_ide/src/main/java/com/hayden/multiagentide/agent/AgentInterfaces.java`
  - `multi_agent_ide_java_parent/multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/agent/AgentModels.java`
  - `multi_agent_ide_java_parent/multi_agent_ide/src/main/java/com/hayden/multiagentide/config/BlackboardRoutingPlanner.java`
  - `multi_agent_ide_java_parent/multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/agent/ContextManagerTools.java`
  - `multi_agent_ide_java_parent/multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/agent/BlackboardHistory.java`

## Session identity model (critical for message targeting)

See `references/session_identity_model.md` for the full hierarchy, recycling rules, and message targeting guide.

Key intuitions:
- `ArtifactKey` is the universal hierarchical index for everything — sessions, messages, prompts, tool calls, stream deltas. Format: `ak:<ULID>/<ULID>/...`.
- **Each agent gets its own unique key**, formed as a child of its parent: orchestrator is the root (`ak:ROOT`), discovery orchestrator is a child of that (`ak:ROOT/CHILD_A`), discovery dispatcher is a child of the discovery orchestrator (`ak:ROOT/CHILD_A/CHILD_B`), and so on down the hierarchy.
- **Recycled sessions**: Orchestrators, collectors, dispatchers, review, merger, context-manager, and **AI propagator** agents **reuse their own previous key** when the workflow routes back to them (e.g. discovery orchestrator on `ROUTE_BACK`). The same ACP session continues — conversation history is preserved. This means a nodeId you see requesting permissions may not be in the current workflow graph tree but is still a live, recycled session from an earlier phase.
- **AI propagator sessions**: The AI propagator (`AI_PROPAGATOR` agent type, typically claude-haiku-4-5) gets an ArtifactKey as a direct child of the root orchestrator. The session mode is configurable at registration time — by default it recycles (reuses the same key across propagation calls), but other session modes exist. Because propagator sessions appear as direct children of root but are NOT workflow agents, they will **not appear in the workflow graph tree**. When you see a permission from a direct-child nodeId that's not in the graph, check `error_search.py node <nodeId>` for `AI_PROPAGATOR` before assuming it's a stale agent.
- **Non-recycled (dispatched) agents**: Ticket agents, discovery agents, and planning agents always get a **new** ArtifactKey. These run as parallel dispatch subprocesses — multiple instances can exist simultaneously per fan-out, and it is ill-posed to recycle their sessions.
- **Sending messages**: Use agent-level nodeIds from `ACTION_STARTED` or `NODE_ADDED` events, or the `chatSessionId / agentNodeId` field from `CHAT_SESSION_CREATED`. Never use the `nodeId` from `CHAT_SESSION_CREATED` (that is the `messageParent` child key, one level below the agent).

## Embabel action routing semantics (critical)

- Agent methods return routing records whose nullable fields represent candidate next requests.
- `BlackboardRoutingPlanner` reads the blackboard `lastResult()` and, when it is a routing record, extracts the first non-null record component as the routed request.
- That extracted object type is matched to each action input binding to select the next action method.
- Special handling for `OrchestratorCollectorResult`:
  - `ADVANCE_PHASE` or `STOP` routes to `finalCollectorResult`.
  - `ROUTE_BACK` routes to `handleOrchestratorCollectorBranch`.
- Expect exactly one non-null routing field; multiple non-null fields are ambiguous and treated as an error condition.

## Context manager recovery model

- Any agent can route to context-manager by emitting `contextManagerRequest`.
- `ContextManagerTools` reads shared run memory from `BlackboardHistory` for the root session/node:
  - `traceHistory`, `listHistory`, `searchHistory`, `listMessageEvents`, `getHistoryItem`, `addHistoryNote`.
- `BlackboardHistory` tracks repeated input types (`detectLoop`, threshold default `3`).
- `handleStuck` caps context-manager recovery attempts (`MAX_STUCK_HANDLER_INVOCATIONS = 3`).
- **Degenerate loop detection**: `DegenerateLoopPolicy` / `DefaultDegenerateLoopPolicy` monitors the `BlackboardHistory` action sequence for repeated node patterns. When the same node sequence repeats `REPETITION_THRESHOLD` times (default 6), it publishes a `NodeErrorEvent` and throws `DegenerateLoopException` to escalate the loop to the supervisor. This fires independently of context-manager routing — it is a circuit-breaker that prevents infinite regress.
  - Source: `multi_agent_ide_java_parent/multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/agent/DefaultDegenerateLoopPolicy.java`

## Prompt locations (for prompt evolution)

See `references/prompt_architecture.md` for the full pipeline and contributor pattern.

- Workflow templates: `multi_agent_ide_java_parent/multi_agent_ide/src/main/resources/prompts/workflow`
- Root prompt resources: `multi_agent_ide_java_parent/multi_agent_ide/src/main/resources/prompts`
- Prompt assembly/context contracts: `multi_agent_ide_java_parent/multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/prompt`
- Library contributors: `multi_agent_ide_java_parent/multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/prompt/contributor`
- App contributors: `multi_agent_ide_java_parent/multi_agent_ide/src/main/java/com/hayden/multiagentide/prompt/contributor`
- Prompt context decorators: `multi_agent_ide_java_parent/multi_agent_ide/src/main/java/com/hayden/multiagentide/agent/decorator/prompt`

**Runtime prompt modification via filters and transformers**: Filters and transformers registered via the REST API (`/api/filters`, `/api/transformers`) are the lightweight mechanism for testing prompt changes without a redeploy. A transformer can reshape API responses seen by agents; a filter can suppress or modify events before they reach the prompt context. Use this as a fast experimental loop — register a transformer, run a goal, inspect results, iterate. Promote stable changes to actual contributor code. See `multi_agent_ide_api` for the registration endpoints and `multi_agent_ide_contracts` for the request shapes.

---

## Workflows (`workflows/`)

See `workflows/reference.md` for the full index. Start with the **standard workflow**:

**Follow `workflows/standard_workflow.md` for the canonical step-by-step loop.**

The standard workflow covers: push/sync → deploy → start goal → poll workflow-graph → handle blocked states → continue polling → redeploy.

> **Endpoint troubleshooting:** All endpoint URLs in this skill and in workflow files are best-effort references. If any call returns an unexpected response, fall back to the `multi_agent_ide_api` skill — use `api_schema.py --level 3` to discover the current request/response shapes from the live OpenAPI spec. If the issue persists after schema verification, report the problem to the user so we can fix the endpoint, the documentation, or both.

---

## Testing matrix

Run tests before deploying code changes:

| Test suite | Approximate duration | Bash timeout |
|------------|---------------------|--------------|
| Unit tests (`./gradlew :multi_agent_ide_java_parent:multi_agent_ide:test`) | ~3 minutes | 180000ms |
| Spring integration (`./gradlew :multi_agent_ide_java_parent:multi_agent_ide:test -Pprofile=integration`) | ~5-10 minutes | 600000ms |
| Full pipeline (`multi_agent_ide_java_parent/tests.sh`) | ~25 minutes | 900000ms |
| ACP integration (`./gradlew :multi_agent_ide_java_parent:multi_agent_ide:test -Pprofile=acp-integration`) | ~60 minutes | 3600000ms |
| ACP chat model (`./gradlew :multi_agent_ide_java_parent:acp-cdc-ai:test -Pprofile=acp-integration`) | ~3 minutes | 3600000ms |

- ACP chat model tests matter only when working on base-level ACP/Claude Code or Codex.
- Skip tests that don't cover your change surface.
- For `multi_agent_ide` integration tests: must use `-Pprofile=integration`, otherwise `**/integration/**` is excluded.
- For ACP chat model tests in `acp-cdc-ai`: must use `-Pprofile=acp-integration`.
- Do not run in parallel sub-agents, with async tasks, or as background tasks - poll manually every 5-10 mins when running long-running tests.

### CRITICAL: Use `--info` only when piping Gradle output to a file
Do not add `--info` for interactive runs. Use it only when redirecting to a log file.

### Polling pattern for workflow monitoring

**Always use subscribe mode** for workflow monitoring — do not sleep-and-poll:
```bash
python executables/poll.py <nodeId> --subscribe 600
```
This checks the activity endpoint every 5 seconds and only runs a full poll when something needs attention (permission, interrupt, conversation, propagation, or goal completion). It surfaces blockers immediately and avoids wasted polls.

Use `--tick 10` for a less frequent check interval. The loop auto-stops on `GOAL_COMPLETED`.

**One-shot mode** (`poll.py <nodeId>` without `--subscribe`) is for quick status checks only — not for ongoing monitoring.

### Polling pattern for long-running test suites
```bash
cd /path/to/module && ./gradlew :multi_agent_ide_java_parent:multi_agent_ide:test -Pprofile=acp-integration --info > /tmp/acp-integration-test.log 2>&1 &
TEST_PID=$!

while kill -0 $TEST_PID 2>/dev/null; do
  sleep 60
  echo "Still running... $(tail -1 /tmp/acp-integration-test.log)"
done

echo "Done. Exit code: $?"
grep -i "FAILED\|BUILD" /tmp/acp-integration-test.log | tail -10
```
For 60-minute acp-integration tests, increase sleep to 120 seconds.

---

## Reusable executables (`executables/`)

When you need to script over polled results, parse event payloads, transform workflow data, or automate any repeated controller operation, **write a Python executable to `executables/`** instead of using inline one-off code.

### RULE: No inline Python — always use `executables/`

**Never write inline Python one-liners or shell heredocs** for controller operations. This includes polling, acknowledgement, propagation parsing, permission inspection, or any other API call.

Instead:
1. **Before writing a new script**, read `executables/reference.md` and check if an existing script already handles the task.
2. **If a matching script exists**, use it directly: `python skills/multi_agent_ide_skills/multi_agent_ide_controller/executables/<name>.py <args>`. If it can be improved (better parsing, additional flags, cleaner output), update it in place.
3. **If no match exists**, write the new script to `executables/<descriptive-name>.py`, add a row to `executables/reference.md`, then invoke it from there.
4. Scripts must be self-contained, accept CLI arguments, and print JSON or structured text to stdout.

**Example — correct:**
```bash
python skills/multi_agent_ide_skills/multi_agent_ide_controller/executables/ack_propagations.py ak:01KK...
```

**Example — wrong (never do this):**
```bash
python3 -c "import urllib.request, json; ..."
```

This is part of the self-improvement loop — each session leaves behind better tooling for the next.

---

## Conversational topology (`conversational-topology/`)

The `conversational-topology/` directory contains the review checklists and gate criteria used when evaluating agent output at each phase transition. These are **living documents** — they evolve as new failure modes are discovered.

Checklists exist for **all 14 agent types** — see `conversational-topology/reference.md` for the full index organized by phase.

### When to consult

- **Every phase gate**: Before approving any phase transition, load and follow the checklists.
- **Every agent justification call**: When any agent calls `callController`, use the agent-specific checklist to drive the conversation.
- **When reviewing propagator signals**: Propagators check form, not substance. The checklists ensure you independently verify semantic correctness.

### How to use

1. Load `conversational-topology/checklist.md` for the general review protocol (extract requirements, map to outputs, check hallucinations, escalation rules)
2. Load the agent-specific checklist for the agent type that called (e.g. `checklist-orchestrator.md`, `checklist-discovery-agent.md`, `checklist-ticket-collector.md`)
3. Execute each ACTION row sequentially — stop at the first FAIL
4. For each response to the agent, include the `--action-name` to track which checklist step you are executing
5. If there are further checklist items after responding, tell the agent to call back via `call_controller` after addressing your feedback
6. Record your gate decision with evidence

### Action name tracking (REQUIRED)

The `--action-name` flag in `conversations.py --respond` is **required**. It records the checklist ACTION step being executed (e.g. `EXTRACT_REQUIREMENTS`, `VERIFY_SCOPE`, `CHECK_ARCHITECTURE`).

This tracking serves two purposes:
1. **Conversation continuity**: The controller can step through multiple checklist ACTIONs across multiple conversation round-trips with the same agent
2. **Self-improvement**: By recording which ACTION steps are most frequently exercised, which lead to FAILs, and which agents need the most back-and-forth, we can identify weak points in agent prompts and strengthen them

Example usage:
```bash
# Step 1: Ask agent about scope coverage
python conversations.py <nodeId> --respond \
  --interrupt-id <id> \
  --action-name VERIFY_SCOPE \
  --message "Which files did you examine for requirement 2? Your findings only mention 1 file for a cross-cutting change."

# Step 2 (after agent calls back): Check architecture
python conversations.py <nodeId> --respond \
  --interrupt-id <id> \
  --action-name CHECK_ARCHITECTURE \
  --message "Good scope coverage now. What architectural patterns connect these components?"

# Step 3 (final approval): No further items
python conversations.py <nodeId> --respond \
  --interrupt-id <id> \
  --action-name APPROVE \
  --message "All checklist items pass. Proceed with your structured result." \
  --no-expect-response
```

### Conversation continuation protocol

When the controller has further checklist items to review:

1. Respond to the agent with feedback on the current ACTION step
2. End the message with a clear instruction to call back: *"After addressing this, call `call_controller` again with your updated analysis."*
3. The agent will receive this via the `controller_response.jinja` template, which instructs them to use `call_controller` for follow-ups

When the controller has completed all checklist items:

1. Respond with explicit approval
2. Use `--no-expect-response` to signal the conversation is complete
3. The agent will proceed to return its final structured result

When a checklist item FAILs and the issue is critical:

1. Respond with the specific failure and what needs to change
2. The agent must address the issue and call back — do NOT approve until resolved
3. If the agent returns its result without calling back, the phase gate should reject it

### How to update

When you observe a new failure mode during a session:

1. Add the failure mode to the relevant agent-specific checklist (Common Failure Modes section)
2. If it warrants a new ACTION row, add it with the appropriate Gate level (FAIL/WARN/ESCALATE)
3. Record the change in `conversational-topology-history/reference.md` with the date, reason, and session context
4. Update `conversational-topology/reference.md` change history if the document structure changed

### History tracking (`conversational-topology-history/`)

The `conversational-topology-history/` directory is a **changelog for checklist modifications only** — not a session log. Only write to it when you change a checklist file (add a failure mode, add/remove an ACTION row, update red flags). Do not record per-conversation evidence or gate decisions here. This enables pattern detection — if the same failure mode keeps appearing, the checklists need stronger gates or the agent prompts need adjustment.

---

## Self-improvement

This skill is designed to evolve. After every session:

1. **Record what worked and what failed** — add a section to `workflows/standard_workflow.md` or create a new workflow variant in `workflows/` if the approach diverged from standard. Update `workflows/reference.md` with any new entries.
2. **Update the standard if strictly better** — if you found a better ordering, gating check, or polling heuristic, update `workflows/standard_workflow.md` directly. Don't accumulate cruft — replace inferior steps.
3. **Create variants for experimental approaches** — if you tried something different (e.g., a tighter poll loop for fast runs, a different permission-resolution strategy), record it as a separate file in `workflows/` and add it to `workflows/reference.md` so it can be compared later.
4. **Update domain references** — if you discovered new routing behavior, session identity edge cases, or filter interactions, update the relevant `references/*.md` file.
5. **Propagate to companion skills** — if the change affects API usage patterns, log search strategies, or deploy procedures, update `multi_agent_ide_api`, `multi_agent_ide_debug`, or `multi_agent_ide_deploy` accordingly.
6. **Grow the executables library** — any script you wrote or improved during the session should already be in `executables/` with an entry in `executables/reference.md`. Review and clean up if needed.
