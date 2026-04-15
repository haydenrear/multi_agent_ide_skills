---
name: multi_agent_ide_view_agent_exec
description: Runtime execution of ACP agents over maintained, stale-aware mental model views. Supports per-view queries, root synthesis, two-phase fan-out discovery, and supervised multi-turn conversations via FIFO boundary controls.
---

Use this skill to execute queries against repository views — curated, stale-aware conceptual projections of the codebase maintained by the `multi_agent_ide_view_agents` skill.

For **managing views** (creating, updating content, adding references, rendering, chain-of-custody search), see the `multi_agent_ide_view_agents` skill. For **creating new views** (ideology, regen.py patterns, view boundary design), see the `multi_agent_ide_view_generation` skill. This skill is the **runtime execution layer** — it queries existing maintained views.

# Doctrine

`view_agent_exec` does not treat views as arbitrary file subsets for parallelization. It treats each view as a **maintained conceptual unit** whose mental models are grounded in source artifacts and may become stale over time.

Parallel execution is possible because views isolate conceptual scope, allowing many agents to reason independently over different maintained understandings of the system. This is a consequence of the view system's epistemic structure, not just an implementation convenience.

When querying a view, the agent must answer in terms of the **mental model preserved by that view** — processes, contracts, capabilities, workflows, failure modes — rather than devolving into one-paragraph-per-file summaries. The view's mental model is the unit of reasoning, not the file set.

Root synthesis should preferentially **compose child mental models** rather than rediscover the full repository from scratch. The root agent is a cognitive dashboard and orchestrator of child conceptual units, not a second monolithic agent that re-reads the world independently. If root duplicates work that per-view agents already performed, the progressive disclosure benefit is erased.

## Query Modes

There are two distinct kinds of queries this system supports:

**Content queries** — "Explain this workflow as preserved by this view." The agent reads the mental model, follows references to source artifacts, and answers based on the curated conceptual projection.

**Maintenance queries** — "What understanding has gone stale? What should be inspected first?" The agent surfaces conceptual drift, identifies which mental model sections no longer match their grounding artifacts, and recommends what to refresh. This is a large part of the value proposition — the system should not only answer what a view says, but also what has drifted and what that drift means conceptually.

## Staleness as Conceptual Drift

Staleness is not just a blocking error. It is **information about conceptual drift**.

Currently, the runner performs a pre-flight staleness check and rejects stale views with an error response containing refresh instructions. This is operationally clean for ensuring agents reason over current models.

However, staleness should be understood as a first-class signal:

- A stale section means some source artifact changed in a way that may invalidate the mental model grounded in it
- The *last known model* still exists and may still be largely correct — it is suspect, not destroyed
- The staleness reason (which files changed, which sections are affected) is itself useful information
- Controller agents should use staleness information to decide what needs maintenance before or after a query

When a view is stale, the error response includes:
- Which sections are stale
- The refresh command needed to make them current

To check staleness without querying:

```bash
uv run --project multi_agent_ide_python_parent/packages/view_agents_utils \
  view-model status views/my-view --repo /path/to/repo
```

## Evidence-Backed Chain of Custody

View agents operate over **evidence-backed mental models** — every claim in a mental model can be traced to frozen snapshots and live source artifacts through the metadata chain. This traceability is what allows staleness detection to mean something more precise than "something changed somewhere."

Each mental model section's metadata tracks curated `SourceFileRef` entries with:

- `repo_path` — path to the **live** source file
- `content_hash` — git blob hash when the reference was created
- `snapshot_path` — frozen copy inside `.snapshots/` at metadata creation time

This means an agent can compare the mental model's claims against both what was true when the model was written (snapshot) and what is true now (live source). The chain of custody makes conceptual drift inspectable, not just detectable.

# Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/query_view.py` | Query a single maintained conceptual unit |
| `scripts/query_root.py` | Run root-mode synthesis over child mental models |
| `scripts/fan_out.py` | Two-phase fan-out: parallel per-view queries + root synthesis |

# Prerequisites

- `claude-agent-acp` on PATH
- Repository with generated and current views (see `multi_agent_ide_view_agents` skill)
- `uv` installed with the `multi_agent_ide_python_parent` workspace synced

# Direct CLI Invocation (via `uv run`)

The `view-agent` CLI is defined in the `view_agent_exec` package:

```bash
uv run --project multi_agent_ide_python_parent/packages/view_agent_exec \
  view-agent query --view views/api-layer --repo /path/to/repo "Explain the API architecture"

uv run --project multi_agent_ide_python_parent/packages/view_agent_exec \
  view-agent query-root --repo /path/to/repo "Summarize the overall architecture"
```

> **Important:** Use `--project multi_agent_ide_python_parent/packages/view_agent_exec`, not the workspace root.

# Script-Based Usage

## Query a Single View

```bash
python scripts/query_view.py \
  --repo /path/to/repo \
  --view api-layer \
  "Explain the API architecture"
```

## Root Synthesis

```bash
python scripts/query_root.py \
  --repo /path/to/repo \
  "Summarize the overall architecture"
```

The root agent receives Phase 1 per-view responses (when provided via `--view-responses-file`) and the root mental model. It should compose child models into cross-view understanding, not re-read source code that per-view agents already analyzed.

## Two-Phase Fan-Out (Discovery Pattern)

```bash
python scripts/fan_out.py \
  --repo /path/to/repo \
  "Analyze the codebase architecture"
```

The fan-out pattern:

1. **Discovery:** Scans `views/` for directories with a `regen.py` (excluding the root `mental-models/`)
2. **Phase 1 (Parallel):** Launches one `query_view.py` subprocess per view via `ThreadPoolExecutor`, all running concurrently
3. **Phase 2 (Synthesis):** Writes Phase 1 results to a temp file, launches `query_root.py` with `--view-responses-file` for cross-view synthesis
4. Returns consolidated JSON

**Why parallelism works:** Views isolate conceptual scope. Each agent reasons over one maintained mental model independently. There is no shared state between per-view queries — the isolation is a consequence of concept-centered view boundaries, not just a threading convenience.

### Output Format

```json
{
  "phase_1_views": [...per-view ViewAgentResponse objects...],
  "phase_2_root": {...root ViewAgentResponse...},
  "views_queried": 16,
  "views_succeeded": 14,
  "views_failed": 2
}
```

### Planned: Routed Fan-Out

The current implementation always queries **all** views. For queries with narrow conceptual scope (e.g., "how does authentication work?"), many views may be irrelevant. A future improvement is a lightweight routing step that selects likely relevant views before fan-out, reducing cost without sacrificing coverage.

This does not exist in `fan_out.py` today. Until implemented, callers who know which views are relevant should use manual parallel dispatch (below) rather than always invoking full fan-out.

## Manual Parallel Dispatch

When you know which views to query — or when you want to avoid `fan_out.py` querying irrelevant views — deploy multiple `query_view.py` calls in parallel using **parallel tool calls**, then run root synthesis over the collected results.

This is the preferred pattern for controller agents and discovery workflows that can determine relevant views upfront.

### Pre-Flight: Render and Triage

Before querying, **render all views first** to get a structured summary of which views are current (queryable) vs stale (need maintenance):

```bash
uv run --project multi_agent_ide_python_parent/packages/view_agents_utils \
  view-model render --all --repo .
```

This outputs JSON to stdout with the structure:

```json
{
  "current_views": [
    {"view_name": "acp-module", "view_path": "views/acp-module", "sections": ["$.sections[\"...\"]", ...]},
    ...
  ],
  "stale_views": [
    {
      "view_name": "api-layer",
      "view_path": "views/api-layer",
      "stale_sections": [{"section_path": "$.sections[\"...\"]", "reasons": [{"reason": "content_hash_changed", "details": "..."}]}],
      "current_sections": ["$.sections[\"...\"]", ...],
      "refresh_command": "uv run --project ... view-model refresh views/api-layer/ --repo ."
    }
  ],
  "skipped_views": [...],
  "error_views": [...],
  "summary": {"total": 16, "current": 14, "stale": 2, "skipped": 0, "errored": 0}
}
```

Progress and staleness guidance go to stderr; only the JSON summary goes to stdout, so callers can parse it cleanly.

### Workflow

1. **Render all** — get the current/stale partition
2. **Fix stale views** — refresh stale sections and update their mental models as needed using `view-model refresh` and `view-model add-ref`
3. **Deploy parallel queries** — launch `query_view.py` for each relevant current view using parallel tool calls (one tool call per view, all in the same message)
4. **Collect responses** — gather the JSON responses from each parallel query
5. **Run root synthesis** — pass collected responses to `query_root.py` via `--view-responses-file`

### Example: Parallel Tool Calls

When using Claude Code or any agent with parallel tool call support, deploy view queries as independent parallel tool calls in a single message:

```
# These run concurrently — one tool call per view
Tool call 1: python scripts/query_view.py --repo . --view acp-module "How does session lifecycle work?"
Tool call 2: python scripts/query_view.py --repo . --view event-messaging "How does the event bus route messages?"
Tool call 3: python scripts/query_view.py --repo . --view orchestration-model "How does goal execution work?"
```

Each call is independent (views isolate conceptual scope), so they can safely execute in parallel. Collect the JSON responses, write them to a temp file, then run root synthesis:

```bash
# Write collected responses to a file
cat > /tmp/view-responses.json << 'EOF'
[...collected ViewAgentResponse objects...]
EOF

# Root synthesis over the results
python scripts/query_root.py \
  --repo . \
  --view-responses-file /tmp/view-responses.json \
  "Synthesize findings about the execution architecture"
```

### Why Manual Over Fan-Out

| | `fan_out.py` | Manual parallel dispatch |
|---|---|---|
| View selection | All views (or none) | Caller selects relevant views |
| Stale handling | Errors on stale views | Caller triages stale vs current upfront |
| Parallelism | ThreadPoolExecutor in one process | Parallel tool calls across the agent system |
| Best for | Broad codebase-wide analysis | Targeted queries, controller-driven workflows |

## Common Options

| Flag | Default | Description |
|------|---------|-------------|
| `--repo` | (required) | Path to the repository |
| `--model` | `claude-haiku-4-5` | Model for the ACP session |
| `--artifact-key` | (none) | Parent artifact key for tracing (`ak:01KJ...`) |
| `--permission-fifo-dir` | (none) | Directory with named pipes for supervised permission (see below) |
| `--conversation-fifo-dir` | (none) | Directory with named pipes for multi-turn conversation control (see below) |

## With Artifact Key (from Discovery/Planning Agent)

```bash
python scripts/fan_out.py \
  --repo /path/to/repo \
  --artifact-key ak:01KJ... \
  "Analyze the codebase architecture"
```

The artifact key connects the entire fan-out execution back to the parent orchestration context for observability and tracing.

# JSON Output

All queries return structured `ViewAgentResponse` JSON:

```json
{
  "view_name": "api-layer",
  "mode": "view",
  "query": "...",
  "response": "...",
  "mental_model_updated": false,
  "stale_sections_refreshed": [],
  "metadata_files_created": [],
  "error": null
}
```

# Supervised Execution Model

View agents are **deliberately narrow, subordinate workers with bounded authority**. This is not an implementation detail — it is part of how controller agents retain supervisory authority over sub-agents in the multi-agent system.

The execution model supports this through:

1. **Read-only by default** — the built-in permission handler denies any tool with write/edit/create/delete keywords
2. **FIFO-based boundary controls** — controller agents can intercept and approve/deny individual tool calls
3. **Conversation steering** — controller agents can drive multi-turn interactions, redirecting or terminating the view agent at each turn
4. **Structured output** — JSON responses enable programmatic processing without parsing free text

The caller (typically a controller or discovery agent in the Java multi_agent_ide system) launches view agents as background subprocesses and maintains asynchronous supervisory control through FIFOs. The key invariant is that view agents are **orchestratable in parallel without forcing synchronous serial reasoning** — the specific mechanism (FIFOs, subprocess polling) may evolve, but the supervisory boundary must be preserved.

## Background Launch Pattern

```bash
# Create FIFOs
CONV_DIR=$(mktemp -d)
mkfifo "$CONV_DIR/conversation_response"
mkfifo "$CONV_DIR/conversation_decision"

# Launch agent in background
python scripts/query_view.py \
  --repo /path/to/repo \
  --view api-layer \
  --conversation-fifo-dir "$CONV_DIR" \
  "Explain the API architecture" &
AGENT_PID=$!

# Poll the conversation FIFO (non-blocking reads via timeout)
# The caller does other work between polls
```

## Python Async Caller Pattern

```python
import json
import os
import select
import subprocess
import tempfile
from pathlib import Path

# 1. Create FIFOs
conv_dir = Path(tempfile.mkdtemp(prefix="view-agent-conv-"))
os.mkfifo(conv_dir / "conversation_response")
os.mkfifo(conv_dir / "conversation_decision")

# 2. Launch agent as background subprocess
proc = subprocess.Popen([
    "python", "scripts/query_view.py",
    "--repo", "/path/to/repo",
    "--view", "api-layer",
    "--conversation-fifo-dir", str(conv_dir),
    "Explain the API architecture",
])

# 3. Poll loop — open FIFO, read with select() for non-blocking check
def poll_response(conv_dir: Path, timeout: float = 1.0) -> dict | None:
    """Non-blocking read from conversation_response FIFO."""
    fd = os.open(str(conv_dir / "conversation_response"), os.O_RDONLY | os.O_NONBLOCK)
    try:
        ready, _, _ = select.select([fd], [], [], timeout)
        if not ready:
            return None
        data = os.read(fd, 65536).decode().strip()
        if not data:
            return None
        return json.loads(data)
    except (json.JSONDecodeError, OSError):
        return None
    finally:
        os.close(fd)

def send_decision(conv_dir: Path, decision: dict) -> None:
    """Write a decision to the conversation_decision FIFO."""
    with open(conv_dir / "conversation_decision", "w") as f:
        f.write(json.dumps(decision) + "\n")
        f.flush()

# 4. Poll periodically, do other work in between
import time
while proc.poll() is None:
    resp = poll_response(conv_dir)
    if resp is not None:
        print(f"Got response: {resp['response'][:100]}...")
        send_decision(conv_dir, {"action": "return"})
        break
    time.sleep(0.5)

proc.wait()
```

# Permission Boundary via Named Pipes

By default, the view agent uses a built-in read-only permission handler that denies write operations. For interactive supervisory control, pass `--permission-fifo-dir` pointing to a directory containing two named pipes:

- `permission_request` — the view agent writes JSON requests here
- `permission_decision` — the controller agent writes JSON decisions here

This is how controller agents enforce **per-tool-call authority boundaries** on subordinate view agents. The permission handler is not just access control — it is part of the supervisory relationship between controller and worker.

## Protocol

1. **Create the FIFOs** before launching the view agent:

```bash
PERM_DIR=$(mktemp -d)
mkfifo "$PERM_DIR/permission_request"
mkfifo "$PERM_DIR/permission_decision"
```

2. **Launch the view agent in the background** with the FIFO directory:

```bash
python scripts/query_view.py \
  --repo /path/to/repo \
  --view api-layer \
  --permission-fifo-dir "$PERM_DIR" \
  "Explain the API architecture" &
```

3. **Poll for requests** from `permission_request` (one JSON line per request):

```json
{"session_id": "sess_abc", "tool_call_id": "tc_123", "tool_name": "Write to file"}
```

4. **Write decisions** to `permission_decision` (one JSON line per decision):

```json
{"allow": true}
```

or to deny:

```json
{"allow": false}
```

The agent blocks on each request until a decision is received. If the decision FIFO returns empty or invalid JSON, the request is denied.

# Multi-Turn Conversation via Named Pipes

By default, each query runs as a single turn. For multi-turn conversations where the controller needs to steer the agent's investigation, pass `--conversation-fifo-dir`:

- `conversation_response` — the runner writes each agent response here
- `conversation_decision` — the controller writes its decision here

## Protocol

1. **Create the FIFOs** before launching:

```bash
CONV_DIR=$(mktemp -d)
mkfifo "$CONV_DIR/conversation_response"
mkfifo "$CONV_DIR/conversation_decision"
```

2. **Launch in background** with the FIFO directory (see examples above)

3. **Poll for responses** from `conversation_response`:

```json
{"response": "The API uses REST patterns with..."}
```

4. **Write decisions** to `conversation_decision`:

To send a follow-up:
```json
{"action": "message", "content": "Can you elaborate on the authentication flow?"}
```

To end the conversation and return the last response:
```json
{"action": "return"}
```

The agent continues within the same ACP session, preserving context across turns. Max 10 follow-up turns by default.

# Following Metadata References

## View-Level: SourceFileRef

Each `SourceFileRef` (visible via `view-model files <view> --repo .`) has:

- `repo_path` — repo-relative path to the **live** source file
- `content_hash` — git blob hash at reference creation time
- `snapshot_path` — frozen copy inside `.snapshots/` at metadata creation time

**To read the frozen snapshot** (what the mental model was built from):
```
views/<view-name>/mental-models/.metadata/<metadata-id>.snapshots/<snapshot_path>
```

**To read the live source file** (current repo state):
```
<repo-root>/<repo_path>
```

**To check for drift:**
```bash
view-model status views/<view-name>/ --repo .
```

If stale:
```bash
view-model refresh views/<view-name>/ --repo .
```

## Root-Level: ChildModelRef

Each `ChildModelRef` has:

- `view_name` — child view name
- `child_head_metadata_id` — the child's HEAD when the root was built
- `child_section_paths` — child sections referenced
- `snapshot_path` — frozen copy of the child's `mental-models.md`

Staleness means `child_head_metadata_id` no longer matches the child's current HEAD.

# Related Skills

- **`multi_agent_ide_view_generation`**: Ideology and patterns for creating views — what views are, how to identify good boundaries, regen.py script design.
- **`multi_agent_ide_view_agents`**: CLI tools for creating, updating, and managing views — content, references, rendering, chain-of-custody search. Use that skill for all write operations.
