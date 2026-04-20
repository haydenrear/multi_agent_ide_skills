# Discovery Agent: View-Agent Integration Guide

## When to Use View-Agent Workflow

Use the view-agent workflow when:
1. The repository has a `views/` directory with generated views (check for `views/*/regen.py`)
2. You need to understand the repository architecture or investigate conceptual drift
3. The query benefits from parallel, focused analysis of independent conceptual units
4. You want to leverage existing mental models and their chain of custody

## Pre-Flight: Render and Triage

Before querying, render all views to get a structured summary of which are current (queryable) vs stale (need maintenance):

```bash
uv run --project multi_agent_ide_python_parent/packages/view_agents_utils \
  view-model render --all --repo .
```

Progress goes to stderr. Stdout is a JSON summary:

```json
{
  "current_views": [
    {"view_name": "acp-module", "view_path": "views/acp-module", "sections": ["$.sections[\"...\"]"]}
  ],
  "stale_views": [
    {
      "view_name": "api-layer",
      "view_path": "views/api-layer",
      "stale_sections": [{"section_path": "...", "reasons": [{"reason": "content_hash_changed", "details": "..."}]}],
      "refresh_command": "uv run --project ... view-model refresh views/api-layer/ --repo ."
    }
  ],
  "summary": {"total": 16, "current": 14, "stale": 2, "skipped": 0, "errored": 0}
}
```

**Workflow:**
1. Parse the JSON summary
2. Fix stale views — run each `refresh_command`, then update mental models with `view-model update` + `view-model add-ref` as needed
3. Query only current views (stale views are rejected by the runner's pre-flight check)

## Two Execution Patterns

### Pattern 1: Manual Parallel Dispatch (preferred for targeted queries)

When you know which views are relevant, deploy multiple `query_view.py` calls as **parallel tool calls** — one per view, all in the same message. This avoids querying irrelevant views.

```
# These run concurrently as parallel tool calls
Tool call 1: python scripts/query_view.py --repo . --view acp-module "How does session lifecycle work?"
Tool call 2: python scripts/query_view.py --repo . --view event-messaging "How does the event bus route?"
Tool call 3: python scripts/query_view.py --repo . --view orchestration-model "How does goal execution work?"
```

Each returns structured JSON independently. Collect responses, write to a temp file, then run root synthesis:

```bash
# Write collected responses to file
cat > /tmp/view-responses.json << 'EOF'
[...collected ViewAgentResponse objects...]
EOF

# Root synthesis
python scripts/query_root.py \
  --repo . \
  --view-responses-file /tmp/view-responses.json \
  "Synthesize findings about the execution architecture"
```

### Pattern 2: Automated Fan-Out (broad codebase-wide analysis)

When you need to query all views:

```bash
python scripts/fan_out.py \
  --repo /path/to/repo \
  "Analyze the codebase architecture"

# With artifact key for tracing
python scripts/fan_out.py \
  --repo /path/to/repo \
  --artifact-key ak:01KJ... \
  "Analyze the codebase architecture"
```

The fan-out script:
1. Discovers all view directories under `views/` (those with `regen.py`, excluding `mental-models/`)
2. Launches one `query_view.py` subprocess per view in parallel via `ThreadPoolExecutor`
3. Writes Phase 1 results to a temp file
4. Launches `query_root.py` with `--view-responses-file` for cross-view synthesis
5. Returns consolidated JSON

## How View Agents Execute

View agents are **read-only subordinate workers** with bounded authority. They cannot modify views, update mental models, or write to the repository.

Each per-view query:
1. The runner (`run_view_query()`) performs a **pre-flight staleness check** — stale views are rejected with an error response containing refresh instructions
2. A prompt is built with the view directory, repo root, and the skill documentation path
3. An `ACPLLMProvider` creates an ACP session using the `claude-agent-acp` command (default model: `claude-haiku-4-5`)
4. The built-in **read-only permission handler** denies any tool with write/edit/create/delete keywords
5. The agent reads the mental model, follows source file references, and answers the query
6. The agent returns a structured JSON response

Root synthesis:
1. The root runner (`run_root_query()`) receives Phase 1 per-view responses via `--view-responses-file`
2. It provides the root mental model (`views/mental-models/`) plus the per-view responses to the root agent
3. The root agent **composes child mental models** — it should not re-read source code that per-view agents already analyzed

## Supervised Execution via FIFOs

For interactive control over view agents (permission decisions, multi-turn conversations), use named pipes:

### Permission FIFOs

```bash
PERM_DIR=$(mktemp -d)
mkfifo "$PERM_DIR/permission_request"
mkfifo "$PERM_DIR/permission_decision"

python scripts/query_view.py \
  --repo . --view api-layer \
  --permission-fifo-dir "$PERM_DIR" \
  "Explain the API" &
```

The agent writes `{"session_id": "...", "tool_call_id": "...", "tool_name": "..."}` to `permission_request`; the caller writes `{"allow": true/false}` to `permission_decision`.

### Conversation FIFOs

```bash
CONV_DIR=$(mktemp -d)
mkfifo "$CONV_DIR/conversation_response"
mkfifo "$CONV_DIR/conversation_decision"

python scripts/query_view.py \
  --repo . --view api-layer \
  --conversation-fifo-dir "$CONV_DIR" \
  "Explain the API" &
```

The agent writes `{"response": "..."}` to `conversation_response`; the caller writes `{"action": "message", "content": "follow-up"}` or `{"action": "return"}` to `conversation_decision`. Max 10 follow-up turns.

## ACP Artifact Key Threading

When called from a discovery or planning agent, the parent `ArtifactKey` is passed via `--artifact-key` for end-to-end tracing:

```
Parent agent (ak:01KJ...)
  └─ fan_out.py --artifact-key ak:01KJ...
       ├─ view query: api-layer     (traced via _current_artifact_key context var)
       ├─ view query: acp-module    (traced via _current_artifact_key context var)
       └─ root synthesis            (traced via _current_artifact_key context var)
```

The artifact key is set in the `acp_process.provider._current_artifact_key` context variable before the ACP session is created.

## Script Options

| Flag | Default | Description |
|------|---------|-------------|
| `--repo` | (required) | Path to the repository |
| `--view` | (required for query_view.py) | View name (e.g., `api-layer`) |
| `--model` | `claude-haiku-4-5` | Model for the ACP session |
| `--artifact-key` | (none) | Parent artifact key for tracing |
| `--permission-fifo-dir` | (none) | Directory with permission named pipes |
| `--conversation-fifo-dir` | (none) | Directory with conversation named pipes |
| `--view-responses-file` | (none, query_root.py only) | JSON file with Phase 1 per-view responses |

## Response Format

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

Fan-out returns consolidated output:

```json
{
  "phase_1_views": [...per-view ViewAgentResponse objects...],
  "phase_2_root": {...root ViewAgentResponse...},
  "views_queried": 16,
  "views_succeeded": 14,
  "views_failed": 2
}
```

- Check `views_failed` — if > 0, some views had errors (likely staleness rejections)
- Per-view `error` fields explain individual failures (stale sections, ACP errors)
- The root `response` provides cross-view synthesis

## Fallback When No Views Exist

If the repository has no `views/` directory:
1. Skip view-agent workflow entirely
2. Use standard repository analysis (direct file reading, grep, etc.)
3. Consider creating views using the `multi_agent_ide_view_generation` skill for future queries
