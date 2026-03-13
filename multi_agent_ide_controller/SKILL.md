---
name: multi_agent_ide_controller
description: Executable workflow skill for the full multi_agent_ide controller loop — polling, graph inspection, permission/interrupt resolution, and self-improvement. References multi_agent_ide_deploy, multi_agent_ide_api, multi_agent_ide_debug, and multi_agent_ide_validate_schema skills.
---

**Load these companion skills before starting a controller session:**
- `multi_agent_ide_deploy` — deploy/sync the application
- `multi_agent_ide_api` — Swagger UI, endpoint reference, API best practices
- `multi_agent_ide_debug` — log locations, error triage, debugging patterns
- `multi_agent_ide_validate_schema` — schemas not available from OpenAPI (filter instruction contracts, resolution enums, internal shapes); validate before use, update if out of sync
- `multi_agent_ide_ui_test` — (optional) only if you need TUI state inspection or UI-level actions

---

## Operating mode
- This skill is a self-improving loop: each run should end with a short analysis of what failed/worked, followed by concrete changes for the next run.
- Before starting, use `api_schema.py --level 3` to discover current request/response shapes from the live OpenAPI spec.
- During/after each redeploy, poll roughly every 60 seconds and check emitted actions/events, permission requests, interrupt requests, and node errors.
- During polling, maintain an in-memory workflow state model from emitted actions/events (active node(s), current phase, waits, pending permissions/interrupts, latest errors).
- Rebuild/update that model at each ~60-second interval and explicitly evaluate run status: progressing, stalled, or failed.
- Use `POST /api/ui/workflow-graph` as the primary source for this in-memory model, then drill into event listing / event detail as needed.
- Treat `workflow-graph` as the authoritative blocked-state view. `metrics.pendingItems` and blocked/`WAITING_INPUT` nodes are the first place to look for permissions, interrupts, and reviews.
- `send-message` (via `POST /api/ui/quick-actions`) only confirms the action was queued. Always re-check `workflow-graph` after every action before assuming the run resumed or advanced.
- Default to event-driven monitoring via the in-memory workflow model; do not require log inspection on every poll.
- If the run is stalled, regressing, or failing, then inspect the app log (`<project-root>/multi-agent-ide.log`) and increase event-detail / node-level resolution as needed.
- If the run shows no meaningful progress for multiple polls (2-3 intervals), treat it as stalled and perform deeper investigation with event-detail + log correlation.
- Every goal submission must include semantic tags that describe the kind of work being requested.
- If an error is not immediately resolvable, perform systematic triage using both events and logs, then report:
  - likely root cause,
  - why it was not recoverable in-run,
  - concrete changes to prevent recurrence.

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

When an AI propagator escalates via `AskUserQuestionTool`, answer via `POST /api/interrupts/resolve` with structured choices in `resolutionNotes`. See `multi_agent_ide_validate_schema` for the full schema.

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

- `ArtifactKey` is the universal hierarchical index for **everything**: agent sessions, messages, prompts, tool calls, stream deltas, and all other artifacts. Format: `ak:<ULID>/<ULID>/...`.
- **Each agent gets its own unique key.** The orchestrator has one key, discovery orchestrator has a different one, each discovery agent has its own, etc.
- **Recycled sessions**: When the workflow routes back to an agent (e.g. discovery orchestrator on `ROUTE_BACK`), that agent **reuses its own previous key** (same ACP session, conversation continues).
- **New sessions**: Dispatched agents always get a new ArtifactKey because multiple can run in parallel per dispatch fan-out.
- **Sending messages**: Use agent-level nodeIds from `ACTION_STARTED`, `NODE_ADDED`, or the `chatSessionId / agentNodeId` field from `CHAT_SESSION_CREATED` events. Never use `nodeId` from `CHAT_SESSION_CREATED` (that's the `messageParent` child), `NODE_STREAM_DELTA` (grandchild), or `ARTIFACT_EMITTED` child keys.
- See `references/session_identity_model.md` for full hierarchy details and recycling rules.

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

## Prompt locations (for prompt evolution)

- Workflow templates: `multi_agent_ide_java_parent/multi_agent_ide/src/main/resources/prompts/workflow`
- Root prompt resources: `multi_agent_ide_java_parent/multi_agent_ide/src/main/resources/prompts`
- Prompt assembly/context contracts: `multi_agent_ide_java_parent/multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/prompt`
- Library contributors: `multi_agent_ide_java_parent/multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/prompt/contributor`
- App contributors: `multi_agent_ide_java_parent/multi_agent_ide/src/main/java/com/hayden/multiagentide/prompt/contributor`
- Prompt context decorators: `multi_agent_ide_java_parent/multi_agent_ide/src/main/java/com/hayden/multiagentide/agent/decorator/prompt`

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

### CRITICAL: Use `--info` only when piping Gradle output to a file
Do not add `--info` for interactive runs. Use it only when redirecting to a log file.

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

### Workflow
1. **Before writing a new script**, read `executables/reference.md` and check if an existing script already handles the task.
2. **If a matching script exists**, use it. If it can be improved (better parsing, additional flags, cleaner output), update it in place.
3. **If no match exists**, write the new script to `executables/<descriptive-name>.py`, then add a row to `executables/reference.md` with the script name and a short description.
4. Scripts should be self-contained, accept CLI arguments, and print JSON or structured text to stdout.

This is part of the self-improvement loop — each session leaves behind better tooling for the next.

---

## Self-improvement

This skill is designed to evolve. After every session:

1. **Record what worked and what failed** — add a section to `workflows/standard_workflow.md` or create a new workflow variant in `workflows/` if the approach diverged from standard. Update `workflows/reference.md` with any new entries.
2. **Update the standard if strictly better** — if you found a better ordering, gating check, or polling heuristic, update `workflows/standard_workflow.md` directly. Don't accumulate cruft — replace inferior steps.
3. **Create variants for experimental approaches** — if you tried something different (e.g., a tighter poll loop for fast runs, a different permission-resolution strategy), record it as a separate file in `workflows/` and add it to `workflows/reference.md` so it can be compared later.
4. **Update domain references** — if you discovered new routing behavior, session identity edge cases, or filter interactions, update the relevant `references/*.md` file.
5. **Propagate to companion skills** — if the change affects API usage patterns, log search strategies, or deploy procedures, update `multi_agent_ide_api`, `multi_agent_ide_debug`, or `multi_agent_ide_deploy` accordingly.
6. **Grow the executables library** — any script you wrote or improved during the session should already be in `executables/` with an entry in `executables/reference.md`. Review and clean up if needed.
