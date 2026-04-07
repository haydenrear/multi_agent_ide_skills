# Standard Controller Workflow

This is the living, canonical workflow for operating a multi_agent_ide controller session.
If you discover a strictly better approach during a session, update this file directly.
For experimental or alternative workflows, create a new file in this directory (e.g., `workflow_variant_<name>.md`).

## Steps

### Step 1 — Push and sync

**1a. Push changes from source repo (innermost submodule first):**

Submodule pointers must be committed from the inside out. Do **not** use `git submodule foreach --recursive` for add/commit/push — it runs each operation across all submodules before the next, so outer submodules stage stale pointers.

```bash
# 1. Innermost: skills/multi_agent_ide_skills
cd skills/multi_agent_ide_skills
git add . && git commit -m "preparing" && git push origin main
cd ../..

# 2. Middle: skills (now picks up the new multi_agent_ide_skills pointer)
cd skills
git add multi_agent_ide_skills && git add . && git commit -m "preparing" && git push origin main
cd ..

# 3. Sibling: multi_agent_ide_java_parent
cd multi_agent_ide_java_parent
git add . && git commit -m "preparing" && git push origin main
cd ..

# 4. Root: parent repo (picks up updated skills + java_parent pointers)
git add skills multi_agent_ide_java_parent && git commit -m "preparing" && git push origin main
```

Each step may no-op if there are no changes — that's fine (`|| true` if scripting).

**1b. Sync or create tmp repo** — use `multi_agent_ide_deploy` skill for `clone_or_pull.py` which handles clone/sync with a 3-phase verification gate.

Check `/private/tmp/multi_agent_ide_parent/tmp_repo.txt` for existing clone. If it exists and is valid, sync it.

There are two cases — **check which applies before running any commands**:

**Case 1 — Fresh clone or no local changes in any submodule:**
Use `git submodule` commands only when you know the working trees are clean (e.g., just after a first clone). These commands leave submodules in a detached HEAD state if run over an already-checked-out repo with local changes.
```bash
TMP_REPO=$(cat /private/tmp/multi_agent_ide_parent/tmp_repo.txt 2>/dev/null)
cd "$TMP_REPO"
git switch main
git pull --ff-only origin main
git submodule foreach --recursive 'git switch main || true'
git submodule foreach --recursive 'git pull --ff-only origin main || true'
git submodule foreach --recursive 'git reset --hard || true'
```

**Case 2 — Repo already exists and submodules may have staged or local changes:**
First check each submodule for changes before touching it. Do **not** use `git submodule` commands — they bypass branch tracking and leave detached HEADs. Instead, `cd` into each submodule that has upstream changes and pull directly:
```bash
TMP_REPO=$(cat /private/tmp/multi_agent_ide_parent/tmp_repo.txt 2>/dev/null)
cd "$TMP_REPO"

# Check for staged/local changes before pulling — do not clobber agent work
git status --short
git submodule foreach --recursive 'git status --short || true'

# For each submodule with upstream changes, cd in and pull:
cd "$TMP_REPO/skills" && git checkout main && git pull origin main
cd "$TMP_REPO/skills/multi_agent_ide_skills" && git checkout main && git pull origin main
cd "$TMP_REPO/multi_agent_ide_java_parent" && git checkout main && git pull origin main
# Only pull submodules that actually have changes — skip others
```

**Pre-deploy verification gate (required, do not skip — BLOCKS Step 2):**

This gate confirms the tmp repo matches what you pushed from the source repo. Run these commands **in the tmp repo**, then compare every SHA against the source repo. If any mismatch, do NOT proceed to deploy.

```bash
TMP_REPO=$(cat /private/tmp/multi_agent_ide_parent/tmp_repo.txt)
cd "$TMP_REPO"
git status --short
git submodule foreach --recursive 'git status --short || true'

# Print tmp repo SHAs
echo "=== TMP REPO SHAs ==="
echo "parent:     $(git rev-parse --short HEAD)"
echo "java_parent: $(git -C multi_agent_ide_java_parent rev-parse --short HEAD)"
echo "buildSrc:    $(git -C buildSrc rev-parse --short HEAD)"
echo "skills:      $(git -C skills rev-parse --short HEAD)"
echo "skills/mai:  $(git -C skills/multi_agent_ide_skills rev-parse --short HEAD)"
```

Then in your **source repo**, run the same SHA commands and confirm they match. If any repo/submodule is detached, not on `main`, or SHA doesn't match — stop and fix before proceeding. Common fix: you forgot to pull a submodule (use Case 2 cd-and-pull pattern above).

After sync, provision executor cwd:
```bash
mkdir -p <tmp-repo>/multi_agent_ide_java_parent/multi_agent_ide/bin
```

**Branch support:** The workflow supports both main-only and multi-branch parallel execution. See "Parallel execution with feature branches" section below for multi-branch workflows.

### Step 2 — Deploy
```
python skills/multi_agent_ide_skills/multi_agent_ide_deploy/scripts/deploy_restart.py --profile claudellama
```
No `--project-root` needed — reads the path from `tmp_repo.txt` automatically. If that file is missing, run `clone_or_pull.py` first.
See `multi_agent_ide_deploy` skill for full deploy options and profiles. Default profile is `claudellama`.

Review active filter policies at startup — they appear in the deploy response under `activeFilterPolicies`.

**If deploy fails** (health check timeout, `"ok": false`), check the build log first:
```bash
tail -100 /private/tmp/multi_agent_ide_parent/multi_agent_ide_parent/build-log.log
```
Common causes:
- **Build failure**: compilation error in pulled code — fix the code, re-push, re-pull, redeploy.
- **Stale goal in DB**: a previous goal's retry loop crashes the app at startup — reset the DB schema (`DROP SCHEMA public CASCADE; CREATE SCHEMA public;` in the postgres container) then redeploy.
- **Port conflict**: another process on 8080 — check `lsof -i :8080`.

Do NOT skip checking `build-log.log` — the deploy script's `"message": "Application failed health check"` does not distinguish between a build failure and a runtime failure.

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

**`repositoryUrl` must be a real local path** (e.g. `/private/tmp/multi_agent_ide_parent/multi_agent_ide_parent/.git`) — not a placeholder. Read it from `tmp_repo.txt`:
```bash
TMP_REPO=$(cat /private/tmp/multi_agent_ide_parent/tmp_repo.txt)
# Then use "$TMP_REPO/.git" as repositoryUrl
```

**Verify the goal actually started** — always check the application log immediately after submitting:
```bash
python skills/multi_agent_ide_skills/multi_agent_ide_debug/executables/error_search.py --type "Repository did not exist" --limit 3
```
Common failure: `Repository did not exist: REPO_PLACEHOLDER` — means `repositoryUrl` was not resolved to the actual path. The `POST` response returns `"status": "started"` even when the async executor fails immediately, so the HTTP response alone is **not** proof the goal is running.

### Step 4 — Poll workflow graph (use subscribe mode)

**Primary method — subscribe mode (preferred):**
```bash
python executables/poll.py <nodeId> --subscribe 600
```
This checks for activity (permissions, interrupts, conversations, propagations) every 5 seconds. When activity is detected, it runs a full poll and prints the result. When a blocker appears (permission, interrupt, conversation needing response), you see it immediately instead of waiting for a sleep cycle. Use `--tick 10` to check less frequently if desired. The loop runs for up to 600 seconds (10 min) then does a final poll — restart it to continue monitoring.

**IMPORTANT: Run subscribe mode synchronously, not in the background.** The entire point of subscribe mode is that it blocks until activity is detected and then wakes you up with actionable output. Do NOT run it as a background task and then sleep/poll the output file — that defeats the purpose. Run it as a normal synchronous Bash call with a long timeout (e.g., `timeout: 600000`). When it prints output, read it and act on it. When it finishes (timeout or goal completion), restart it if the goal is still running.

**One-shot mode — for quick status checks:**
```bash
python executables/poll.py <nodeId>
```

**Fallback — raw workflow-graph endpoint:**
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
# To reject with a reason sent to the AI agent:
curl -X POST http://localhost:8080/api/permissions/resolve \
  -H 'Content-Type: application/json' \
  -d '{"id": "<id>", "optionType": "REJECT_ONCE", "note": "Do not write files during discovery phase"}'
```

Use `executables/permissions.py` to inspect and batch-resolve permissions in one step.

**CRITICAL: `call_controller` permissions are NOT conversations.**
When you see a pending permission for `mcp__agent-tools__call_controller`, this is the agent asking for *permission to use the tool* — it is NOT the conversation itself. The `input` field in the permission may show a preview of the justification message, but this is just the tool call payload, not an interactive conversation requiring your review.

The correct flow is:
1. **Permission appears** for `call_controller` → resolve it (typically `ALLOW_ALWAYS` since agents need to call the controller as part of normal operation)
2. **After resolution**, the agent executes the tool call and a **conversation** appears in the conversations section of the next poll
3. **The conversation** is where you load checklists, review agent justifications, and send responses (INJECT_RESEARCH, JUSTIFICATION_PASSED, etc.)

Do not confuse these two steps. Do not load checklists or attempt adversarial review at the permission stage — that happens at the conversation stage.

**Phase-boundary violations — REJECT and correct:**
Discovery and planning agents are **read-only**. If a permission request shows a discovery agent, planning orchestrator, or planning agent attempting to write files (e.g., `create_new_file`, `replace_text_in_file`, `Terminal` with `cp`/`cat >`/`mkdir`), this is a phase-boundary violation:

1. **Reject** the permission: `python permissions.py --resolve --option REJECT_ONCE --note "Discovery agents are read-only — do not write files"`
2. **Send a corrective message** to the specific agent node explaining the violation:
```bash
curl -X POST http://localhost:8080/api/ui/message \
  -H 'Content-Type: application/json' \
  -d '{
    "nodeId": "<agent-nodeId>",
    "message": "CORRECTIVE ACTION: Your file write permission was REJECTED. The planning phase is READ-ONLY. You must NOT create, copy, modify, or write any files. Describe what needs to be created as ticket tasks — do not create files yourself."
  }'
```
3. **Log to `outstanding.md`** per Rule B below.

Only **ticket execution agents** should write files. This is a recurring issue (see outstanding #17, #27, #31).

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

### Step 9b — Respond to conversations

When the poll shows a pending conversation (under `═══ CONVERSATIONS ═══`), this is an agent calling `call_controller` with a justification message. This is where you load the agent-specific checklist, review the justification, and respond.

**Reading conversations:**
```bash
python executables/conversations.py <nodeId>
```

**Responding to conversations — required arguments:**
```bash
python executables/conversations.py <nodeId> --respond \
  --interrupt-id "<interruptId>" \
  --action-name <ACTION_NAME> \
  --message "<your message>"
```

All three flags are required when responding:
- `--interrupt-id` — the interrupt ID from the conversation output (e.g. `ak:01KNFJ.../01KNFJ...`). Copy this from the poll or conversations output.
- `--action-name` — the checklist ACTION step you are executing (e.g. `EXTRACT_REQUIREMENTS`, `INJECT_RESEARCH`, `JUSTIFICATION_PASSED`). This must match an action from the agent-specific checklist.
- `--message` — the text to send to the agent.

Add `--no-expect-response` for terminal actions like `JUSTIFICATION_PASSED` where you do not expect the agent to call back.

**Common mistake:** Forgetting `--interrupt-id` or `--action-name`. Both are always required. The poll and conversations output print the `interruptId` — copy it directly. The `--action-name` comes from the checklist ACTION table for the agent type you are reviewing.

**Example — full conversation flow:**
```bash
# 1. Read the conversation
python executables/conversations.py ak:01KNF...

# 2. Respond with a checklist action (expects agent to call back)
python executables/conversations.py ak:01KNF... --respond \
  --interrupt-id "ak:01KNF.../01KNF..." \
  --action-name INJECT_RESEARCH \
  --message "I found that ArtifactService.toEntity() serializes full children at line 359. Please confirm and update your result."

# 3. After agent calls back and you're satisfied, approve (terminal)
python executables/conversations.py ak:01KNF... --respond \
  --interrupt-id "ak:01KNF.../01KNF..." \
  --action-name JUSTIFICATION_PASSED \
  --message "Approved. Proceed." \
  --no-expect-response
```

### Step 10 — Continue polling (subscribe mode)

**Use subscribe mode** — do not sleep-and-poll manually:
```bash
python executables/poll.py <nodeId> --subscribe 600
```

Subscribe mode checks the activity endpoint every `--tick` seconds (default 5). It prints a full poll **only when activity is detected** — permissions, interrupts, conversations, propagation items, or goal completion. This eliminates wasted polls and surfaces blockers immediately.

When the subscribe loop prints a poll result:
- `pendingItems` non-empty → waiting for input → run Step 9 (handle blocked states)
- New propagation items → run Step 5 (review alignment)
- `GOAL_COMPLETED` → subscribe auto-stops
- Subscribe timeout (no activity for the full duration) → check if the run is stalled. Load `multi_agent_ide_debug` skill and follow its triage steps.

**Do not** use `sleep N && poll.py` loops or manual polling intervals. The subscribe mode is strictly better — it responds faster to blockers and avoids unnecessary polls during quiet periods.

### Step 10b — Check log for errors (after every 2-3 poll cycles or on stall)

**When to run:** After every 2-3 subscribe poll cycles (roughly every 60-90 seconds of activity), or immediately when the subscribe loop times out with no activity (potential stall).

```bash
python skills/multi_agent_ide_skills/multi_agent_ide_debug/executables/error_search.py
```

This prints an aggregate summary: count, time window, and description for every active error pattern. Review for:
- **New patterns that weren't active before** — something changed
- **High counts on critical patterns** (NODE_ERROR, NullPointerException, OutOfMemoryError) — investigate immediately
- **Duplicate artifact key explosion** (200+ matches) — possible session recycling issue; note in `outstanding.md` but may be non-fatal
- **Rate limiting / timeout patterns** — agents may be stuck waiting on LLM provider

For detail on a specific pattern:
```bash
python skills/multi_agent_ide_skills/multi_agent_ide_debug/executables/error_search.py --type "NODE_ERROR" --limit 5
python skills/multi_agent_ide_skills/multi_agent_ide_debug/executables/error_search.py --acp  # check ACP/LLM errors separately
```

**Decision tree:**
- **No errors or only known-benign patterns** → continue to Step 10 (next poll cycle)
- **New critical errors** → investigate immediately; if the run is broken, kill the app (`deploy_restart.py --kill-only`), fix, redeploy
- **Stall with no errors** → check ACP log (`--acp`), check if agent processes are alive, check for unresolved permissions/interrupts
- **Any error worth tracking** → add to `outstanding.md` per Rule A, and add the pattern to `error_patterns.csv` if not already there

> **Log suppression:** Always use summary mode first. Only drill into detail (`--type`) for specific patterns. Do not dump entire error outputs — they overwhelm context. Keep `--limit` low (default 5).

### Step 11 — Review ticket agent work after merge

**When to run:** after each ticket agent node transitions to COMPLETED and its merge-back is visible (check `workflow-graph` for the ticket node showing COMPLETED status).

The ticket agent's changes are merged into the main worktree at the end of each ticket. Review the actual code/files produced before the next ticket agent starts — catch scope creep, wrong files modified, or acceptance criteria not met while they are still isolated.

**What to check:**
1. **Files changed** — read the `filesModified` field from the `ACTION_RESPONSE runTicketAgent` propagation item (`propagation_detail.py --limit N --field agentResult`). Cross-check against the ticket's `relatedFiles` and acceptance criteria.
2. **Diff the worktree** — the ticket's worktree branch can be inspected directly:
   ```bash
   git -C <worktree-path> log --oneline -5
   git -C <worktree-path> diff HEAD~1
   ```
3. **Acceptance criteria** — verify each criterion from the ticket's `acceptanceCriteria` list is satisfied by the output.
4. **No unintended changes** — confirm no files outside the ticket scope were modified (e.g. unrelated Java classes, schema files changed without a Liquibase entry).

**Decision tree:**
- **All criteria met, no scope creep** → continue to Step 10 (next ticket).
- **Partial or incorrect implementation** → send a corrective message to the ticket-dispatch node (or trigger a route-back interrupt) before the next ticket picks up the merged result.
- **Wrong files modified or out-of-scope changes** → raise an interrupt via `POST /api/interrupts/resolve` with `resolutionType: REJECTED` to route back.

### Step 12 — Redeploy after changes
```bash
python skills/multi_agent_ide_skills/multi_agent_ide_deploy/scripts/deploy_restart.py
```

---

## Ongoing Tracking Rules

### Rule A — Log bugs and issues seen in propagation items to `outstanding.md`

When reviewing propagation items (Step 5) and you encounter a bug, error, or undesirable behavior (e.g., a propagator raises an escalation, an agent produces incorrect output, a constraint violation is detected, or a tool call fails), **add a new entry to `skills/multi_agent_ide_skills/multi_agent_ide_debug/references/outstanding.md`** before continuing.

Format:
```markdown
## N. <short title>

**Problem:** <what was observed, including nodeId / itemId if available>

**Root cause:** <diagnosed or suspected cause>

**Workaround:** <what you did to get past it>

**Fix needed:** <what should be implemented to resolve it permanently>
```

Do not skip this step even if the issue appears transient or was immediately resolved via a corrective message. The goal is a complete record of issues surfaced during live runs.

### Rule B — Log corrective messages sent to agents in `outstanding.md`

When you send a corrective message to an agent (Step 8) to steer or fix its behavior, **add a new entry to `outstanding.md`** recording both the issue and the corrective action taken.

This applies to any `SEND_MESSAGE` that corrects agent behavior — e.g., fixing a misinterpreted constraint, redirecting scope creep, clarifying a requirement that was hallucinated, or overriding a wrong routing decision.

**Example:** During a discovery phase, the agent flagged a constraint conflict because `CLAUDE.md` says "no parallel sub-agents" and the goal mentioned "parallel execution." The corrective message sent was: `"The CLAUDE.md directive about parallel sub-agents applies to Claude Code tool usage only — it does NOT restrict the feature being implemented."` — this should be recorded so the same misinterpretation can be addressed at the prompt level in a future fix.

Format: same as Rule A, with the corrective message text in the **Workaround** field and the prompt/constraint ambiguity described in the **Fix needed** field.

---

## Parallel Execution with Feature Branches

Use this workflow when working with multiple independent feature branches or when coordinating work across feature branches that will be merged back to main.

### When to use this workflow

- **Multi-ticket feature development**: Each ticket is assigned a separate feature branch (`feature/ticket-001`, `feature/ticket-002`, etc.), worked in parallel, then merged back to main
- **Exploration with risk isolation**: Work on experimental branches without affecting main; safely discard or merge back on completion
- **Multi-agent parallelization**: Different agents or runs work on different branches simultaneously, each maintaining an independent tmp clone
- **Concurrent release branches**: Maintain stable branches (e.g., `release/v2.0`) while main continues development

### Setup: Create a feature branch

Before starting work on a feature, create and push the branch from your source repo:

```bash
# From your source checkout (e.g., ~/IdeaProjects/multi_agent_ide_parent)
git switch main
git pull origin main
git switch -c feature/ticket-001
git push origin feature/ticket-001
```

**For submodules:** The feature branch should exist in each submodule before pushing the root repo branch. Otherwise, `clone_or_pull.py` will fail when it tries to switch submodules to the feature branch:

```bash
# In each submodule, create and push the feature branch
cd skills
git switch main && git pull origin main && git switch -c feature/ticket-001 && git push origin feature/ticket-001
cd ../multi_agent_ide_java_parent
git switch main && git pull origin main && git switch -c feature/ticket-001 && git push origin feature/ticket-001
cd ..

# Back in root, push the feature branch with updated submodule pointers
git push origin feature/ticket-001
```

**One-liner for all submodules** (run from root):
```bash
git submodule foreach --recursive 'git switch main && git pull origin main && git switch -c feature/ticket-001 && git push origin feature/ticket-001 || true'
git push origin feature/ticket-001
```

### Clone/sync to a feature branch

Instead of Step 1b in the standard workflow, use `clone_or_pull.py` with `--branch`:

```bash
# Clone fresh with feature branch
python skills/multi_agent_ide_skills/multi_agent_ide_deploy/scripts/clone_or_pull.py --branch feature/ticket-001

# Or sync an existing tmp repo to a feature branch
python skills/multi_agent_ide_skills/multi_agent_ide_deploy/scripts/clone_or_pull.py --branch feature/ticket-001
```

This performs the 3-phase deploy prep (clone/sync → verification gate → provision) on the specified branch. All submodules are automatically switched to the feature branch if it exists in each submodule.

**Note:** You may have multiple tmp repos, one per branch. The path is stored in `/private/tmp/multi_agent_ide_parent/tmp_repo.txt` after each `clone_or_pull.py` run. To switch between branches later, either:
- Re-run `clone_or_pull.py --branch <other-branch>` to sync an existing tmp repo to a different branch, or
- Delete `tmp_repo.txt` and run `clone_or_pull.py --branch <branch-name>` to create a fresh clone for the new branch

### Work on the feature branch

Once cloned/synced to a feature branch, follow the standard workflow (Steps 2–11) **without modification**. The tmp repo is on the feature branch, so all operations (deploy, agent runs, etc.) work on that branch. There is no special handling needed.

### Push changes from feature branch to tmp repo

Before deploying agents, push your changes from the source repo's feature branch to the remote:

```bash
# From source repo (e.g., ~/IdeaProjects/multi_agent_ide_parent)
git switch feature/ticket-001

# Push innermost submodule first, then work outward (same pattern as Step 1a)
cd skills/multi_agent_ide_skills
git add . && git commit -m "preparing" && git push origin feature/ticket-001
cd ../..

cd skills
git add multi_agent_ide_skills && git add . && git commit -m "preparing" && git push origin feature/ticket-001
cd ..

cd multi_agent_ide_java_parent
git add . && git commit -m "preparing" && git push origin feature/ticket-001
cd ..

git add skills multi_agent_ide_java_parent && git commit -m "preparing" && git push origin feature/ticket-001
```

Then sync the tmp repo to pull those changes:

```bash
python skills/multi_agent_ide_skills/multi_agent_ide_deploy/scripts/clone_or_pull.py --branch feature/ticket-001
```

### Merge feature branch back to main

After all work on the feature branch is complete and tested, merge it back to main:

```bash
# From source repo
git switch feature/ticket-001
git pull origin feature/ticket-001  # Ensure local is up to date with remote

# Merge to main
git switch main
git pull origin main
git merge feature/ticket-001  # Or use --ff-only if you want fast-forward only
git push origin main

# Also merge submodules
cd skills
git switch main && git pull origin main
git merge feature/ticket-001
git push origin main
cd ../multi_agent_ide_java_parent
git switch main && git pull origin main
git merge feature/ticket-001
git push origin main
cd ..
```

**One-liner for all submodules and root:**
```bash
git submodule foreach --recursive 'git switch main && git pull origin main && git merge feature/ticket-001 && git push origin main || true'
git switch main && git pull origin main && git merge feature/ticket-001 && git push origin main
```

If merge conflicts occur, resolve them in the source repo, commit, and push before proceeding.

### Pull merged changes into the tmp repo (optional)

If you deployed agents on a feature branch and want to apply the merged result to the tmp repo on main, pull the updated main:

```bash
python skills/multi_agent_ide_skills/multi_agent_ide_deploy/scripts/clone_or_pull.py --branch main
```

This switches the tmp repo back to main and pulls all merged changes (including the feature branch work now integrated into main). You can then redeploy and continue work on main if needed.

Alternatively, if you are done with the tmp repo on the feature branch, you can delete it:

```bash
rm /private/tmp/multi_agent_ide_parent/tmp_repo.txt
# The tmp repo directory will be cleaned up on the next clone_or_pull.py run
```

### Merge worktree changes after goal completion

When a goal completes, `poll.py` displays the `GoalCompletedEvent.worktreePath`. The worktree contains the agent's work on a derived branch (e.g. `main-<uuid>`) — there is **no automatic merge back to the source repo or tmp repo**.

The controller should manually merge worktree changes back into the project repo. Process each submodule that has changes, **innermost first** (`skills/multi_agent_ide_skills` → `skills` → root):

#### 1. Check for dangling commits

The worktree system sometimes creates temp branches (e.g. `main-212e9b45-...`) and switches away without merging, orphaning commits. Before merging, check for this:

```bash
cd <worktree-path>/<submodule>
git reflog --oneline -20
```

Look for entries like `checkout: moving from main-<uuid> to main` — this means the agent's branch was abandoned. If you find orphaned commits, cherry-pick them onto the current branch:

```bash
git cherry-pick <orphaned-commit-sha>
```

#### 2. Check remote URLs

Worktree repos may have origin pointing to the tmp repo's `.git` dir instead of GitHub. Verify and fix if needed:

```bash
git -C <worktree-submodule> remote -v
# If it points to a local .git path instead of github:
git -C <worktree-submodule> remote set-url origin git@github.com:haydenrear/<repo>.git
```

#### 3. Push the agent's branch to origin

```bash
git -C <worktree-submodule> push origin <branch-name>
```

#### 4. Merge into the project repo

In the project repo's corresponding submodule, fetch and merge the agent's branch:

```bash
cd ~/IdeaProjects/multi_agent_ide_parent/<submodule>
git fetch origin <branch-name>
git merge origin/<branch-name>
```

#### 5. Push and walk up the submodule chain

After merging and pushing the innermost submodule, commit the updated submodule pointer in the parent, push, and repeat until root is done:

```bash
# After pushing skills/multi_agent_ide_skills:
cd skills
git add multi_agent_ide_skills
git commit -m "Update multi_agent_ide_skills submodule pointer"
git push origin main

# After pushing skills:
cd ..
git add skills
git commit -m "Update skills submodule pointer"
git push origin main
```

**Order:** `skills/multi_agent_ide_skills` → `skills` → root (innermost → outermost).

**Tip:** If main hasn't diverged, the merge will be a fast-forward — `git pull origin <branch>` and `git push origin main` is sufficient.

### Multi-branch coordination

**For concurrent execution on different branches:**

1. Maintain separate tmp repo paths or use the same path (via `clone_or_pull.py --branch <branch>`) if switching between branches is acceptable
2. Coordinate timing: ensure branch-specific verification gates pass before deploying agents
3. Track which branch each agent/run is working on — use goal tags or logging to maintain clarity (e.g., `"tags": ["feature/ticket-001"]`)
4. After all feature branches complete, merge them to main in order of dependency
5. Pull the final merged main back into the tmp repo and redeploy to confirm end-to-end integration

### Troubleshooting branch workflows

**Branch doesn't exist in a submodule:**
```
error: pathspec 'feature/xyz' did not match any file(s) known to git
```

Solution: Create the feature branch in the submodule and push it before running `clone_or_pull.py`. See "Create a feature branch" section above.

**Detached HEAD after branch switch:**
```bash
# Verify you're on the correct branch
git -C <tmp-repo> branch -v
git -C <tmp-repo>/skills branch -v

# Re-run verification gate
python skills/multi_agent_ide_skills/multi_agent_ide_deploy/scripts/clone_or_pull.py --status
```

**SHA mismatch between source and tmp repo:**
Ensure all changes are committed and pushed in the source repo before syncing:
```bash
git switch feature/ticket-001
git status --short
git submodule foreach --recursive 'git status --short || true'

# Push everything
git submodule foreach --recursive 'git push origin feature/ticket-001 || true'
git push origin feature/ticket-001

# Then sync
python skills/multi_agent_ide_skills/multi_agent_ide_deploy/scripts/clone_or_pull.py --branch feature/ticket-001
```
