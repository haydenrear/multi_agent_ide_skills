---
name: multi_agent_ide_debug
description: Instructional debugging skill for multi_agent_ide — log locations, error triage, node error patterns, and log search best practices.
---

Use this skill when the running `multi_agent_ide` application is behaving unexpectedly and you need to investigate errors, stalls, or unexpected behavior through logs and event correlation.

## Log Locations

| Log | Path | Contains |
|-----|------|----------|
| **Application runtime** | `<project-root>/multi-agent-ide.log` | Workflow events, goal completion, node status changes, errors. **Start here for all runtime issues.** |
| **Build / Gradle** | `<project-root>/build-log.log` | Gradle build output only — does NOT contain runtime events. |
| **ACP/LLM errors** | `<project-root>/multi_agent_ide_java_parent/multi_agent_ide/claude-agent-acp-errs.log` | LLM call failures from the ACP chat model. ACP errors are also emitted on the event bus. |

> **Do not confuse build log and runtime log.** The build log only has compile/boot output. All workflow and agent behavior is in `multi-agent-ide.log`.

## Log Search Best Practices

**Always use `executables/error_search.py` — do not write inline grep commands.**

```bash
EXEC=skills/multi_agent_ide_skills/multi_agent_ide_debug/executables/error_search.py

python $EXEC                           # summary: all known errors with counts + time windows
python $EXEC --type "NODE_ERROR"       # last 5 matches for NODE_ERROR pattern
python $EXEC --type 4                  # last 5 matches for pattern at CSV row 4
python $EXEC --type "Duplicate" --limit 20  # last 20 matches for duplicate key errors
python $EXEC --acp                     # search ACP error log instead
python $EXEC --raw "some pattern"      # ad-hoc grep (bypasses CSV)
```

Error patterns are defined in `executables/error_patterns.csv` — each row has a grep expression and a description. The summary mode shows count, first/last timestamp, and description for every active pattern.

The script resolves the project root automatically from `tmp_repo.txt`. See `executables/reference.md` for the full listing.

### CRITICAL: Keep error_patterns.csv up to date

**Every time you encounter a new recurring error in the logs that is not already covered by `error_patterns.csv`, you MUST add a new row immediately.** This is vitally important — the CSV is the institutional memory for error detection. If you skip this step, future sessions will miss the same error and waste time rediscovering it. A pattern only needs to appear twice to qualify as "recurring." Add the grep expression and a short description, then verify with `error_search.py --type "<new pattern>"` that it matches.

### Log output suppression

When reviewing log output, **always use `--limit`** to control how many lines are returned. Large error outputs (e.g., 200+ duplicate artifact key errors) will overwhelm context. The summary mode is designed to avoid this — it shows counts and timestamps, not the full lines. Only use detail mode (`--type`) when you need to inspect specific errors, and keep `--limit` low (default 5).

## Exception knowledge base

Before investigating any exception, **check the exception references first** to avoid wasting time on known issues.

### Ignored exceptions (`references/ignore-exceptions.md`)
Contains exceptions that are confirmed benign and should be skipped. **Before you spend any resources triaging an error**, check this file — if the exception matches an entry, do not investigate further.

When you confirm a new exception is safe to ignore (e.g., expected in the environment, cosmetic, no user impact), add it to `references/ignore-exceptions.md` with a short rationale.

### Common exceptions & gotchas (`references/common-exceptions.md`)
Tracks recurring issues, known failure patterns, and application weak points. This builds institutional memory across sessions.

**When to add entries:**
- You see a recurring bug or failure pattern across multiple runs
- You identify a fragile area of the application that breaks under specific conditions
- You discover a non-obvious gotcha (e.g., ordering dependency, race condition, config sensitivity)
- You find a workaround for a known issue

This file is not for exceptions to ignore — it's for understanding what commonly goes wrong and why, so future sessions can diagnose faster.

---

## Reusable executables (`executables/`)

When you need to script log analysis, parse error patterns, correlate events, or automate any repeated debug operation, **write a Python executable to `executables/`** instead of using inline one-off code.

### Workflow
1. **Read `executables/reference.md` first.** Check if an existing script already handles the task.
2. **If a matching script exists**, use it. If it can be improved — new preset, better output, additional flag — update it in place and note the change in `reference.md`.
3. **If no match exists**, write the new script to `executables/<descriptive-name>.py`, add a row to `executables/reference.md`, then use it.
4. **Never write inline grep commands or one-off Python for log search.** If the existing scripts don't cover the need, that means a script is missing — add it.
5. Scripts should be self-contained, accept CLI arguments, and print structured output to stdout.

This is part of the self-improvement workflow — each debug session leaves behind better tooling for the next.

---

## Node Error Triage

When `workflow-graph` shows `NODE_ERROR` events or stalled nodes:

0. **Check exception knowledge base first:**
   Read `references/ignore-exceptions.md` — if the exception matches a known-ignorable entry, skip investigation. Check `references/common-exceptions.md` for known patterns that may speed up diagnosis.

1. **Check runtime log first:**
   ```bash
   python skills/multi_agent_ide_skills/multi_agent_ide_debug/executables/error_search.py
   python skills/multi_agent_ide_skills/multi_agent_ide_debug/executables/error_search.py --type "NODE_ERROR"
   ```

2. **Check ACP errors for LLM call failures:**
   ```bash
   python skills/multi_agent_ide_skills/multi_agent_ide_debug/executables/error_search.py --acp
   ```

3. **Correlate with event detail:**
   ```bash
   curl -X POST http://localhost:8080/api/ui/nodes/events/detail \
     -H 'Content-Type: application/json' \
     -d '{"nodeId": "<nodeId>", "eventId": "<errorEventId>"}'
   ```

4. **Check workflow graph for pending items:**
   ```bash
   curl -X POST http://localhost:8080/api/ui/workflow-graph \
     -H 'Content-Type: application/json' \
     -d '{"nodeId": "<nodeId>"}'
   ```
   Look for `pendingItems` with type `PERMISSION`, `INTERRUPT`, `REVIEW`, or `PROPAGATION`.

5. **Update exception references:** If this is a new recurring issue, add it to `references/common-exceptions.md`. If confirmed safe to ignore, add to `references/ignore-exceptions.md`.

> **Endpoint troubleshooting:** If any endpoint call in this triage flow returns an unexpected response or error, fall back to the `multi_agent_ide_api` skill — use `api_schema.py --level 3` to explore the current schema and verify the request shape. If the issue persists after schema verification, report it to the user so we can fix it.

## Common Failure Modes

| Symptom | Likely cause | Where to look |
|---------|-------------|---------------|
| Run stalled, no events | LLM/provider failure | `claude-agent-acp-errs.log` |
| `NODE_ERROR` events | Java exception or routing failure | `multi-agent-ide.log` |
| Permission gate never clears | `resolve-permission` not called | `workflow-graph` pendingItems |
| Interrupt never resolves | `resolve-interrupt` not called | `workflow-graph` pendingItems |
| Build fails on deploy | Compile error or missing buildSrc commit | `build-log.log` |
| Missing `multi_agent_ide_python_parent` error | Submodule not available in this environment | Expected — ignore for Java-side workflow validation |
| External filter executor fails | Missing `bin` directory | Check `<tmp-repo>/multi_agent_ide_java_parent/multi_agent_ide/bin` exists |

## Stall Detection and Recovery

A run is stalled when:
- `workflow-graph` shows no growth in `chatMessageEvents`, `toolEvents`, or `streamTokens` across 2-3 consecutive polls (~2-3 minutes).
- No `pendingItems` are visible (not waiting for input — genuinely stuck).

**Recovery steps:**
1. Check runtime log for exceptions: `python skills/multi_agent_ide_skills/multi_agent_ide_debug/executables/error_search.py`
2. Check ACP errors for provider/credit failures: `python skills/multi_agent_ide_skills/multi_agent_ide_debug/executables/error_search.py --acp`
3. Run `event-detail` on the most recent event for the stuck node.
4. If the agent is looping (same event type repeatedly), check `BlackboardHistory` loop detection — threshold is 3 repetitions.
5. If unrecoverable: redeploy with `multi_agent_ide_deploy` skill, then restart goal.

## Prompt and Routing Debug

When an agent is making wrong decisions or routing incorrectly:

- **Prompt locations**: `multi_agent_ide_java_parent/multi_agent_ide/src/main/resources/prompts/workflow`
- **Routing source**: `multi_agent_ide_java_parent/multi_agent_ide/src/main/java/com/hayden/multiagentide/config/BlackboardRoutingPlanner.java`
- **Agent models**: `multi_agent_ide_java_parent/multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/agent/AgentModels.java`

Use `POST /api/ui/nodes/events/detail` to see full rendered prompts in `ARTIFACT_EMITTED` events.

## Data-Layer Filters and Their Effect on Debugging

Active filters can suppress or transform events visible in event polling and detail. If you suspect missing data:
1. Check active policies: `POST /api/filters/layers/policies` with `{ "layerId": "controller-ui-event-poll" }`
2. View what was filtered: `POST /api/filters/policies/records/recent` with `{ "policyId": "<uuid>", "layerId": "<layerId>" }`
3. Temporarily deactivate: `POST /api/filters/policies/deactivate` with `{ "policyId": "<uuid>" }`

See `multi_agent_ide_api` skill for the full filter endpoint reference. For filter instruction schemas (Python executor contracts), see `multi_agent_ide_validate_schema` skill.

---

## When endpoints don't behave as documented

All endpoint examples in this skill are best-effort references. The live application is the source of truth.

1. **Fall back to `multi_agent_ide_api` skill** — use `api_schema.py --level 3 --tag "<TagName>"` to discover the current request/response shapes from the running app's OpenAPI spec.
2. **If the schema matches but the call still fails**, check whether the app is running, whether the node/event IDs are valid, and review `multi-agent-ide.log` for server-side errors.
3. **If you can't resolve it**, tell the user what you tried and what the error is — so we can fix the endpoint, the documentation, or both.
