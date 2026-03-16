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

### Step 5 — Validate alignment via propagation items (on progress detected)

**When to run:** whenever `workflow-graph` shows progress (new `chatMessageEvents`, `toolEvents`, or completed nodes since the last poll).

The controller's job is not only to confirm the workflow completes — it is to **intermittently verify that the work being done aligns with the goal**, and interrupt when it does not.

```bash
curl -X POST http://localhost:8080/api/propagations/items/by-node \
  -H 'Content-Type: application/json' \
  -d '{"nodeId": "<nodeId>", "limit": 2}'
```

Read the `propagatedText` field of each item — this is the full serialized action request or response payload that passed through the propagators. Assess whether the content reflects on-track progress toward the goal.

**Decision tree:**
- **On-track** → continue to Step 6 (poll events) for detail if needed, or skip directly to Step 9 (continue polling).
- **Off-track or concerning** → go to Step 8 (apply action / send message) to steer or interrupt before continuing.
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
```bash
curl -X POST http://localhost:8080/api/ui/quick-actions \
  -H 'Content-Type: application/json' \
  -d '{
    "action": "SEND_MESSAGE",
    "nodeId": "<nodeId>",
    "message": "<text>"
  }'
```
Do not treat the response as proof the workflow moved. Re-run `workflow-graph` and confirm status changes, message/tool-count growth, or cleared `pendingItems`.

### Step 9 — Handle blocked states
Check `workflow-graph` for non-empty `pendingItems` first.

**PERMISSION blocked:**
```bash
# List pending permissions
curl http://localhost:8080/api/permissions/pending

# Get detail (by id or node scope)
curl "http://localhost:8080/api/permissions/detail?id=<requestId-or-nodeScope>"

# Review content before approving — if unusual, ask before resolving
curl -X POST http://localhost:8080/api/permissions/resolve \
  -H 'Content-Type: application/json' \
  -d '{"id": "<id>", "optionType": "ALLOW_ALWAYS"}'
```

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
- No growth across 2-3 polls → stalled → escalate to `multi_agent_ide_debug` skill

### Step 11 — Redeploy after changes
```bash
python skills/multi_agent_ide_deploy/scripts/deploy_restart.py
```
