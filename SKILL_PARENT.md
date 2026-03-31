# multi_agent_ide_skills

This directory contains all controller skills for operating the `multi_agent_ide` system. Each skill is a focused, self-contained package of instructions, scripts, and references for a specific operational domain.

## Skills

| Skill | Purpose |
|-------|---------|
| `multi_agent_ide_controller` | **Start here.** Full controller loop — submitting goals, polling workflow graph, permission/interrupt resolution, propagation monitoring, self-improvement. **Use this skill for all goal submission and polling operations.** |
| `multi_agent_ide_deploy` | Clone to `/private/tmp`, sync, deploy, verify, restart. Run before starting any session. |
| `multi_agent_ide_api` | **Use this for all API interaction.** Swagger-first endpoint discovery via `scripts/api_schema.py`, OpenAPI schema inspection, propagator/filter/transformer registration. **Always use `api_schema.py` to discover endpoint shapes before constructing any curl call — never guess field names.** |
| `multi_agent_ide_debug` | **Use this for all log searching.** Log locations, `error_search.py` (summary + detail modes with `error_patterns.csv`), error triage, stall detection. **Never grep the log files directly — use `error_search.py`.** |
| `multi_agent_ide_contracts` | Authoritative schemas not available from OpenAPI — `Instruction` sealed interface, resolution enums, propagation types, filter/matcher enums. |
| `multi_agent_ide_ui_test` | TUI state inspection and UI-level actions. Rarely needed; load only when the controller skill tells you to. |

## Skill responsibilities — who owns what

This is the canonical ownership table. When in doubt about which skill to consult, check here first.

| Task | Skill to use |
|------|-------------|
| Submit a goal (`/api/ui/goals/start`) | `multi_agent_ide_controller` (references `multi_agent_ide_api` for schema) |
| Poll workflow graph | `multi_agent_ide_controller` → `executables/poll.py` |
| Discover endpoint URL or request shape | `multi_agent_ide_api` → `scripts/api_schema.py` |
| List or register propagators/filters/transformers | `multi_agent_ide_api` (schema discovery) + `multi_agent_ide_controller` (session scripting) |
| Search runtime logs or build logs | `multi_agent_ide_debug` → `executables/error_search.py` |
| Resolve permissions/interrupts | `multi_agent_ide_controller` → `executables/permissions.py` / `interrupts.py` |
| Deploy or restart the app | `multi_agent_ide_deploy` → `scripts/deploy_restart.py` |
| Look up internal type schemas | `multi_agent_ide_contracts` |

## Conversational topology documents

The controller skill includes two directories for phase-gate review:

| Directory | Purpose |
|-----------|---------|
| `multi_agent_ide_controller/conversational-topology/` | Review checklists and ACTION tables for each agent type at phase gates |
| `multi_agent_ide_controller/conversational-topology-history/` | Chronological change log — tracks when and why checklists were updated |

See `multi_agent_ide_controller/SKILL.md` for full usage instructions.

### CRITICAL: JUSTIFICATION_PASSED vs INJECT_RESEARCH protocol

The `controller_response.jinja` template matches on the action name `JUSTIFICATION_PASSED` (and `APPROVED`) and instructs the agent to **immediately return its structured JSON result without calling `call_controller` again**. This has critical implications for how the controller shares information with agents:

- **NEVER include new information in a JUSTIFICATION_PASSED message.** New findings, corrections, or context in a JUSTIFICATION_PASSED message create a conflict: the agent wants to integrate the information (which requires calling back) but is told to return immediately. This causes looping or dropped information.
- **Use `INJECT_RESEARCH` to share all new information.** This action expects the agent to confirm receipt, integrate the findings into its proposed result, and call `call_controller` again. Only after the agent has confirmed integration and you are satisfied with the refined result should you send JUSTIFICATION_PASSED.
- **JUSTIFICATION_PASSED is purely a terminal approval signal.** It should confirm the already-integrated result and may include a reminder about JSON output format, but must not contain anything the agent needs to act on.

The flow is: checklist ACTIONs → INJECT_RESEARCH (expects confirmation) → agent integrates and calls back → verify refined result → JUSTIFICATION_PASSED (terminal, no new info, `--no-expect-response`).

---

## Loading companion skills

The `multi_agent_ide_controller` skill lists exactly which companions to load at the top of its `SKILL.md`. Follow that list — it is kept up to date as skills evolve.

For targeted work (e.g., just deploying, just debugging logs), you can load only the relevant skill. For a full controller session, load all companions.

---

## Executables — read this before starting any session

Every skill that involves repeated scripted operations has an `executables/` or `scripts/` directory. **These directories are the preferred way to interact with the system.**

### Why executables matter

- **Parsing API responses by hand is error-prone.** The executables know the exact field names, handle edge cases, and produce clean output.
- **They are living documentation.** Each script records the actual response shape, field names, and edge cases discovered during real sessions — things that are not always visible from the API schema alone.
- **Future models will use them.** When you add a script, you are leaving a tool for the next session. When you improve a script, you are fixing a problem once instead of rediscovering it every time.

### Workflow — always follow this

1. **Before writing any inline parse/call code**, check the relevant `executables/reference.md` (or `scripts/` listing) to see if a script already handles the task.
2. **If a matching script exists**, use it. If it can be improved — better field names, additional flags, cleaner output — update it in place.
3. **If no match exists**, write a new script and add a row to `executables/reference.md` so it can be found next time.
4. Scripts should be self-contained, accept CLI args (`--host`, `--limit`, etc.), and print structured output to stdout.

### Where to look

| Skill | Scripts location | Reference index | What they do |
|-------|-----------------|-----------------|--------------|
| `multi_agent_ide_controller` | `executables/` | `executables/reference.md` | Poll workflow state, inspect/resolve permissions, ack propagations, validate propagation record structure |
| `multi_agent_ide_api` | `scripts/` | listed in SKILL.md | Query OpenAPI schema, discover endpoints |
| `multi_agent_ide_deploy` | `scripts/` | listed in SKILL.md | Clone/sync repo, deploy, restart |
| `multi_agent_ide_debug` | `executables/` | `executables/reference.md` | Error search via `error_search.py` + `error_patterns.csv`, interrupt tracing |

### Key executables — load these before any session

**Controller monitoring** (`multi_agent_ide_controller/executables/`):
- `poll.py <nodeId> --subscribe 600` — **primary monitoring command**: checks activity every 5s, full poll on activity (permissions, interrupts, conversations, propagations). Auto-stops on goal completion. Use `--subscribe` for all ongoing monitoring — do not sleep-and-poll manually.
- `poll.py <nodeId>` — one-shot status view (graph + propagations + permissions). Use for quick checks only.
- `permissions.py [--resolve]` — list and batch-resolve pending permissions with tool names and raw input.
- `ack_propagations.py <nodeId>` — acknowledge all PENDING propagation items.
- `validate_propagation.py <nodeId>` — verify propagatedText contains the Propagation record structure.
- `propagation_detail.py <nodeId>` — full propagation payload with parsed JSON.

**Debug / log search** (`multi_agent_ide_debug/executables/`):
- `error_search.py` — **primary error tool**: aggregate summary of all known error patterns with counts and time windows.
- `error_search.py --type "NODE_ERROR"` — last 5 matches for a specific error type (substring match on expression or description).
- `error_search.py --type 4 --limit 20` — last 20 matches for CSV row 4.
- `error_search.py --acp` — search ACP error log instead of runtime log.
- `error_search.py --raw "some pattern"` — ad-hoc grep (bypasses CSV).
- **CRITICAL**: When you encounter a new recurring error not already in `error_patterns.csv`, you **MUST** add a new row immediately. This CSV is the institutional memory for error detection — skipping this step means future sessions will miss the same error.

### RULE: no inline scripts

**Never write inline Python one-liners or ad-hoc grep commands** for any task covered by the above scripts. If the task is not covered, write a new script to `executables/` first, add a row to `reference.md`, then invoke it. This applies to every skill in this directory.

---

## Submodule commit chain — CRITICAL

This repo (`multi_agent_ide_skills`) is nested inside a submodule chain:

```
multi_agent_ide_parent  →  skills  →  multi_agent_ide_skills
```

When committing changes in `multi_agent_ide_skills`, you **MUST** propagate the commit through every intermediate submodule up to the root. If you skip a level, `git clone --recurse-submodules` will fail because the parent's submodule pointer references a commit that was never pushed to the intermediate repo.

### Commit order (innermost → outermost)

1. `cd multi_agent_ide_skills` → `git add`, `git commit`, `git push`
2. `cd skills` → `git add multi_agent_ide_skills`, `git commit`, `git push`
3. `cd multi_agent_ide_parent` → `git add skills`, `git commit`, `git push`

The same applies to `multi_agent_ide_java_parent` and any other submodule.

### Verification — run after every commit session

After committing and pushing all levels, **always** run from the root:

```bash
cd <multi_agent_ide_parent> && git submodule foreach --recursive git status
```

Every submodule must show either `nothing to commit, working tree clean` or only pre-existing unrelated changes. If any submodule shows `(new commits)` or `(modified content)` for files you just changed, you missed a level — go back and commit/push that intermediate repo before pushing the parent.
