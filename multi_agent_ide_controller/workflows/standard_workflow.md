# Standard Controller Workflow

This is the living, canonical workflow for operating a multi_agent_ide controller session.
If you discover a strictly better approach during a session, update this file directly.
For experimental or alternative workflows, create a new file in this directory (e.g., `workflow_variant_<name>.md`).

## Steps

### Step 1 — Push and sync

**1a. Push changes from source repo:**
```bash
git submodule foreach --recursive 'git add . || true'
git submodule foreach --recursive 'git commit -m "preparing" || true'
git submodule foreach --recursive 'git push origin main || true'
git add .
git commit -m "preparing"
git push origin main
```

**1b. Sync or create tmp repo** — use `multi_agent_ide_deploy` skill for `clone_or_pull.py` which handles clone/sync with a 3-phase verification gate.

Check `/private/tmp/multi_agent_ide_parent/tmp_repo.txt` for existing clone. If it exists and is valid, sync it:
```bash
TMP_REPO=$(cat /private/tmp/multi_agent_ide_parent/tmp_repo.txt 2>/dev/null)
cd "$TMP_REPO"
git switch main
git pull --ff-only origin main
git submodule foreach --recursive 'git switch main || true'
git submodule foreach --recursive 'git pull --ff-only origin main || true'
git submodule foreach --recursive 'git reset --hard || true'
```

**Pre-deploy verification gate (required, do not skip):**
```bash
git status --short
git submodule foreach --recursive 'git status --short || true'
git rev-parse --short HEAD
git -C multi_agent_ide_java_parent rev-parse --short HEAD
```
Compare SHAs against what you just pushed. If any repo/submodule is detached, not on `main`, or SHA doesn't match — stop and fix before proceeding.

After sync, provision executor cwd:
```bash
mkdir -p <tmp-repo>/multi_agent_ide_java_parent/multi_agent_ide/bin
```

**Only deploy and run from `main`.** Do not use other branches unless explicitly asked.

### Step 2 — Deploy
```
python skills/multi_agent_ide_deploy/scripts/deploy_restart.py --profile claudellama
```
No `--project-root` needed — reads the path from `tmp_repo.txt` automatically. If that file is missing, run `clone_or_pull.py` first.
See `multi_agent_ide_deploy` skill for full deploy options and profiles. Default profile is `claudellama`.

Review active filter policies at startup — they appear in the deploy response under `activeFilterPolicies`.

### Step 3 — Start goal
```bash
curl -X POST http://localhost:8080/api/ui/goals/start \
  -H 'Content-Type: application/json' \
  -d '{
    "goal": "<goal>",
    "repositoryUrl": "<local-path-with-.git>",
    "tags": ["<descriptor>", "<descriptor>"]
  }'
```

### Step 4 — Poll workflow graph
```bash
curl -X POST http://localhost:8080/api/ui/workflow-graph \
  -H 'Content-Type: application/json' \
  -d '{"nodeId": "<nodeId>"}'
```
Run immediately after `start-goal`, after every `send-message` / action, and after every permission/interrupt resolution. Use `workflow-graph` first to decide if the run is progressing, waiting on input, or stalled.

### Step 5 — Validate alignment via propagation items (after each agent completes)

**When to run:** whenever `workflow-graph` shows a node has completed (new ACTION_COMPLETED events, or new child nodes since the last poll). This fires per-agent — check after each agent finishes, not just on any event growth. Propagators fire at action request/response boundaries, so items reflect what each agent was asked to do and what it decided.

The controller's job is not only to confirm the workflow completes — it is to **verify after each agent action that the work aligns with the goal**, and interrupt when it does not.

Use `executables/poll.py` for a combined one-shot view. It prints each item's `itemId` and a truncated summary. **The summary is always truncated — treat it as a navigation aid only, not a review.**

#### 5a — Identify new items from poll output

`poll.py` prints each propagation item as:
```
  [ACTION_REQUEST] <layer>  status=<status>  itemId=<id>
    summary: <truncated>
    <truncated payload>
    → python propagation_detail.py <nodeId> --limit 1  (review full payload)
```

Track which `itemId` values you have already reviewed. When a new `itemId` appears (i.e., one you haven't seen before), **always read the full payload before continuing** — do not rely on the truncated summary.

#### 5b — Read every new ACTION_REQUEST and ACTION_RESPONSE in full

```bash
# Read the most recent N items in full (use --raw for complete JSON, --limit to scope)
python executables/propagation_detail.py <nodeId> --limit 3 --raw

# Or extract a specific field across items
python executables/propagation_detail.py <nodeId> --limit 3 --field goal
python executables/propagation_detail.py <nodeId> --limit 3 --field agentResult
python executables/propagation_detail.py <nodeId> --limit 3 --field collectorDecision
```

**What to check in the full payload:**
- `goal` — confirms the agent received the right task, not a hallucinated or drifted version
- `agentResult` / `output` — what the agent decided or produced; look for scope creep, wrong files, or invented requirements
- `delegationRationale` — why work was dispatched the way it was; should match the original ticket intent
- `collectorDecision.decisionType` — ADVANCE_PHASE / ROUTE_BACK / STOP; verify the reason is sound
- `recommendations` / `planningResults` — any planning output; check for hallucinated steps or out-of-scope changes
- Phase violations — e.g., a discovery agent that executed code changes instead of just reading files

If any field looks wrong, **do not continue polling**. Go to Step 8 to steer before the next agent runs.

**Decision tree:**
- **On-track** → continue to Step 6 (poll events) for detail if needed, or skip directly to Step 10 (continue polling).
- **Off-track, hallucination, or scope creep detected** → go to Step 8 (apply action / send message) to steer or interrupt before the next agent picks up the result.
- **Phase violation** (e.g., discovery agent implemented code) → send a corrective message to the **specific agent's nodeId** (not the root orchestrator nodeId). Each agent has its own ACP session — a message to the root will not reach the agent. Get the agent nodeId from `poll.py`'s graph output (e.g., the `discovery-agent` node's id under the dispatch node) and use that in `SEND_MESSAGE`. The workflow orchestrator may already have caught the violation, but confirm before proceeding.
- **No items returned** → propagators have not fired yet for this node (early in run, or no propagators registered for this layer). Continue to Step 6.

> This endpoint returns items across all statuses (not just PENDING) ordered by recency, so it reflects the latest payload the propagator saw regardless of whether an escalation was raised.

### Step 6 — Poll events
```bash
curl -X POST http://localhost:8080/api/ui/nodes/events \
  -H 'Content-Type: application/json' \
  -d '{"nodeId": "<nodeId>"}'
```

### Step 7 — Expand events as needed
```bash
curl -X POST http://localhost:8080/api/ui/nodes/events/detail \
  -H 'Content-Type: application/json' \
  -d '{"nodeId": "<nodeId>", "eventId": "<eventId>"}'
```

### Step 8 — Apply action or send message

**CRITICAL: Always target the specific agent nodeId, not the root.**
Each agent (discovery-agent, ticket-agent, etc.) has its own ACP session. A message to the root orchestrator nodeId will not reach the running agent. Get the target nodeId from `poll.py`'s graph tree — it's the leaf node that is currently `RUNNING` or `WAITING_INPUT`.

```bash
curl -X POST http://localhost:8080/api/ui/quick-actions \
  -H 'Content-Type: application/json' \
  -d '{
    "actionType": "SEND_MESSAGE",
    "nodeId": "<specific-agent-nodeId-from-poll-graph>",
    "message": "<text>"
  }'
```
Do not treat the response as proof the workflow moved. Re-run `workflow-graph` and confirm status changes, message/tool-count growth, or cleared `pendingItems`.

### Step 9 — Handle blocked states
Check `workflow-graph` for non-empty `pendingItems` first.

**PERMISSION blocked:**
```bash
# List pending permissions (shows requestId, nodeId, toolCallId)
curl http://localhost:8080/api/permissions/pending

# Get full detail — response has: requestId, nodeId, toolCallId, permissions, toolCalls[]
# toolCalls[].title = tool name, toolCalls[].rawInput = what the agent wants to do
curl "http://localhost:8080/api/permissions/detail?id=<requestId-or-nodeScope>"

# Review toolCalls[].rawInput before approving. Use executables/permissions.py for readable output.
curl -X POST http://localhost:8080/api/permissions/resolve \
  -H 'Content-Type: application/json' \
  -d '{"id": "<id>", "optionType": "ALLOW_ALWAYS"}'
```

Use `executables/permissions.py` to inspect and batch-resolve permissions in one step.

**INTERRUPT/REVIEW blocked:**
```bash
# Get detail
curl -X POST http://localhost:8080/api/interrupts/detail \
  -H 'Content-Type: application/json' \
  -d '{"id": "<requestId-or-nodeScope>"}'

# Resolve
curl -X POST http://localhost:8080/api/interrupts/resolve \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "<id>",
    "originNodeId": "<nodeId>",
    "resolutionType": "APPROVED"
  }'
```

For both, `id` can be a concrete request id **or** an ArtifactKey node scope — server searches within that scope.

**PROPAGATION blocked:**
```bash
# Check propagation events
curl -X POST http://localhost:8080/api/ui/nodes/events \
  -H 'Content-Type: application/json' \
  -d '{"nodeId": "<nodeId>", "eventType": "PROPAGATION"}'

# Get pending propagation items
curl http://localhost:8080/api/propagations/items

# Resolve propagation item
curl -X POST http://localhost:8080/api/propagations/items/<itemId>/resolve \
  -H 'Content-Type: application/json' \
  -d '{"resolutionType": "APPROVED"}'
```

When a propagator escalates via `AskUserQuestionTool`, it creates an interrupt — resolve via `POST /api/interrupts/resolve` with structured choices in `resolutionNotes`. See `multi_agent_ide_validate_schema` for the `InterruptResolution` schema.

### Step 10 — Continue polling
Poll every 60 seconds for long-running runs. Watch `workflow-graph` for:
- `chatMessageEvents` / `toolEvents` growth → progressing → run Step 5 (propagation check)
- `pendingItems` non-empty → waiting for input → run Step 9 (handle blocked states)
- No growth across 2-3 polls → stalled → load the `multi_agent_ide_debug` skill and follow its triage steps. Check `executables/reference.md` for available log search scripts before doing anything else.

### Step 11 — Redeploy after changes
```bash
python skills/multi_agent_ide_deploy/scripts/deploy_restart.py
```
