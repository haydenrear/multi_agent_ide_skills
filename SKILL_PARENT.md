# multi_agent_ide_skills

This directory contains all controller skills for operating the `multi_agent_ide` system. Each skill is a focused, self-contained package of instructions, scripts, and references for a specific operational domain.

## Skills

| Skill | Purpose |
|-------|---------|
| `multi_agent_ide_controller` | **Start here.** Full controller loop — polling, permission/interrupt resolution, propagation monitoring, self-improvement. References all other skills. |
| `multi_agent_ide_deploy` | Clone to `/private/tmp`, sync, deploy, verify, restart. Run before starting any session. |
| `multi_agent_ide_api` | Swagger-first API interaction — OpenAPI schema discovery, endpoint reference, filter/propagator/transformer operations. |
| `multi_agent_ide_debug` | Log locations, error triage, exception knowledge base, stall detection. |
| `multi_agent_ide_contracts` | Authoritative schemas not available from OpenAPI — `Instruction` sealed interface, resolution enums, propagation types, filter/matcher enums. |
| `multi_agent_ide_ui_test` | TUI state inspection and UI-level actions. Rarely needed; load only when the controller skill tells you to. |

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
| `multi_agent_ide_debug` | `executables/` | `executables/reference.md` | Log search with named presets (`errors`, `node`, `goal`, `permission`, `propagation`, `overflow`, `acp`) |

### Key executables — load these before any session

**Controller monitoring** (`multi_agent_ide_controller/executables/`):
- `poll.py <nodeId>` — combined one-shot view: graph + propagations + permissions. **Primary polling command.**
- `permissions.py [--resolve]` — list and batch-resolve pending permissions with tool names and raw input.
- `ack_propagations.py <nodeId>` — acknowledge all PENDING propagation items.
- `validate_propagation.py <nodeId>` — verify propagatedText contains the Propagation record structure.
- `propagation_detail.py <nodeId>` — full propagation payload with parsed JSON.

**Debug / log search** (`multi_agent_ide_debug/executables/`):
- `search_log.py errors` — recent errors and exceptions in the runtime log.
- `search_log.py node <nodeId>` — all log lines for a specific node.
- `search_log.py overflow` — DB column overflow errors.
- `search_log.py acp` — ACP/LLM call failures.
- `search_log.py --follow` — tail the runtime log live.

### RULE: no inline scripts

**Never write inline Python one-liners or ad-hoc grep commands** for any task covered by the above scripts. If the task is not covered, write a new script to `executables/` first, add a row to `reference.md`, then invoke it. This applies to every skill in this directory.
