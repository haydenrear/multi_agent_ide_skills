# Discovery Agent: View-Agent Integration Guide

## When to Use View-Agent Workflow

Use the view-agent two-phase workflow when:
1. The repository has a `views/` directory with generated views (check for `views/*/regen.py`)
2. You need to understand the repository architecture
3. The query benefits from parallel, focused analysis of different code modules
4. You want to leverage existing mental models and chain of custody

## How to Detect Available Views

```bash
# Check if views exist
ls views/*/regen.py 2>/dev/null
```

If no views are found, fall back to standard discovery methods. View generation is a prerequisite — use the `multi_agent_ide_view_generation` skill to create views first.

## The Two-Phase Flow

### Phase 1: Parallel Per-View Analysis

Each view gets its own Docker container running the query independently:
- Container mounts the repo read-only at `/repo`
- Only the target view's `mental-models/` is writable
- Docker socket is mounted so the agent can invoke `view-agent-utils` containers for `view-model` and `view-custody` tool commands
- The agent uses these tools to check staleness, read the mental model, and update stale sections as part of its reasoning
- Each view returns a structured JSON response

### Phase 2: Root Synthesis

After all per-view queries complete:
- A root container reads all per-view mental models via `view-model show`
- Uses `view-model status` to check for stale root sections
- Synthesizes cross-view patterns, data flows, and architectural decisions
- Returns a unified JSON response

### Invocation

```bash
python fan_out.py --repo /path/to/repo --model llama3.2 "Your query here"
```

## How to Interpret Results

The consolidated JSON output contains:

```json
{
  "phase_1_views": [
    {"view_name": "api-module", "response": "...", "error": null},
    {"view_name": "core-lib", "response": "...", "error": null}
  ],
  "phase_2_root": {"view_name": "root", "response": "...", "error": null},
  "views_queried": 2,
  "views_succeeded": 2,
  "views_failed": 0
}
```

- Check `views_failed` — if > 0, some views timed out or had errors
- Per-view `error` fields explain individual failures
- The root `response` provides the cross-view synthesis

## Fallback When No Views Exist

If the repository has no `views/` directory:
1. Skip view-agent workflow entirely
2. Use standard repository analysis (direct file reading, grep, etc.)
3. Consider suggesting view generation for future queries
