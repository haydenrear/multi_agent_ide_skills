---
name: multi_agent_ide_view_agent_exec
description: Python scripts for querying views using Ollama. Supports per-view queries, root synthesis, and two-phase fan-out for parallel discovery.
---

Use this skill to query repository views using local Ollama models.

For **managing views** (creating, updating content, adding references, rendering, chain-of-custody search), see the `multi_agent_ide_view_agents` skill instead — this skill is only for querying existing views with an LLM.

## Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/query_view.py` | Query a single view |
| `scripts/query_root.py` | Run root-mode cross-view synthesis |
| `scripts/fan_out.py` | Two-phase fan-out: parallel per-view queries + root synthesis |

## Prerequisites

- Ollama installed and running locally with a model pulled (e.g. `ollama pull llama3.2`)
- Repository with generated views (see `multi_agent_ide_view_agents` skill for creating/managing views)

## Usage

### Query a Single View

```bash
python scripts/query_view.py \
  --repo /path/to/repo \
  --view api-layer \
  --model llama3.2 \
  "Explain the API architecture"
```

### Root Synthesis

```bash
python scripts/query_root.py \
  --repo /path/to/repo \
  --model llama3.2 \
  "Summarize the overall architecture"
```

### Two-Phase Fan-Out (Discovery Agent Pattern)

```bash
python scripts/fan_out.py \
  --repo /path/to/repo \
  --model llama3.2 \
  --timeout 120 \
  "Analyze the codebase architecture"
```

The fan-out script:
1. Detects all view directories under `views/`
2. Launches one query per view in parallel
3. Waits for all to complete (with configurable timeout)
4. Launches a root query for cross-view synthesis
5. Returns consolidated JSON output

## Staleness Handling

The query agent uses `view-model status` (from the `multi_agent_ide_view_agents` skill) to detect stale sections before querying. If sections are stale, it can use `view-model update` and `view-model add-ref` to refresh them as part of its reasoning. See the `multi_agent_ide_view_agents` skill for full CLI documentation.

## JSON Output

All queries return structured JSON:

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

## Related Skills

- **`multi_agent_ide_view_agents`**: CLI tools for creating, updating, and managing views (content, references, rendering, chain-of-custody). Use that skill for all write operations.
