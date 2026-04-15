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

Each view gets its own ACP agent subprocess running the query independently:
- The ACP agent (e.g. `claude-agent-acp`) has terminal access and can run `view-model` CLI commands directly
- Sandbox args control filesystem isolation — the agent can read the repo and write to the view's mental-models directory
- The agent uses `view-model status`, `view-model render`, `view-model update` to check staleness, read content, and refresh stale sections
- Each view returns a structured JSON response

### Phase 2: Root Synthesis

After all per-view queries complete:
- A root ACP agent reads all per-view mental models via `view-model render`
- Uses `view-model status` to check for stale root sections
- Synthesizes cross-view patterns, data flows, and architectural decisions
- Returns a unified JSON response

### Invocation

```bash
# Basic invocation
python fan_out.py --repo /path/to/repo "Your query here"

# With ACP args (sandbox, permissions)
python fan_out.py --repo /path/to/repo \
  --command claude-agent-acp \
  --args '--permission-mode acceptEdits --add-dir /path/to/worktree' \
  "Your query here"

# With artifact key for tracing (from parent discovery/planning agent)
python fan_out.py --repo /path/to/repo \
  --artifact-key ak:01KJ... \
  "Your query here"
```

### ACP Artifact Key Threading

When called from a discovery or planning agent, the parent agent's `ArtifactKey` is passed via `--artifact-key`. The exec script creates a child key for each view query, enabling end-to-end tracing:

```
Parent agent (ak:01KJ...)
  └─ fan_out.py --artifact-key ak:01KJ...
       ├─ view query: api-layer  (ak:01KJ.../01KK...)
       ├─ view query: core-lib   (ak:01KJ.../01KL...)
       └─ root synthesis         (ak:01KJ.../01KM...)
```

### Sandbox Args from application.yml

The Java application's `application.yml` defines sandbox args per provider profile:

```yaml
providers:
  claude:
    command: claude-agent-acp
    args: ${ACP_ARGS:}   # Enriched at runtime by SandboxTranslationStrategy
```

When the discovery/planning agent invokes the Python exec scripts, it passes the same sandbox args. The `SandboxTranslationStrategy` pipeline adds:
- **Claude profile**: `--add-dir <worktree>`, `--permission-mode acceptEdits`
- **Codex profile**: `-c cd=<worktree>`, `-c sandbox=workspace-write`

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
