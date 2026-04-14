---
name: multi_agent_ide_view_generation
description: Instructional skill for generating per-view Python scripts that create symlink-based repository views. Views provide progressive disclosure of large codebases by partitioning files into coherent subsets, each with its own regeneration script and mental-models directory.
---

Use this skill when you need to generate or maintain **repository views** — symlink-based directory structures that present a coherent subset of a repository's files for focused analysis.

## What Are Views?

A **view** is a directory under `views/` at the repository root containing:

1. **Symbolic links** pointing back into the source tree (relative paths)
2. A **`regen.py`** Python script that recreates the symlinks
3. A **`mental-models/`** subdirectory for the view's mental model and metadata chain

Views partition a repository into focused slices — for example, an `api-module` view might contain only the REST controllers and data models, while a `core-lib` view covers shared utilities and domain logic. This enables agents to reason over a manageable subset of files rather than the entire codebase.

## Directory Hierarchy

```
<repo-root>/
├── views/
│   ├── mental-models/          # Root-level mental model (cross-view synthesis)
│   │   └── mental-models.md
│   ├── api-module/
│   │   ├── regen.py            # Per-view regeneration script
│   │   ├── mental-models/
│   │   │   └── mental-models.md
│   │   └── src/main/java/api/  # Symlinks into source tree
│   │       ├── UserController.java -> ../../../../src/main/java/api/UserController.java
│   │       └── ...
│   └── core-lib/
│       ├── regen.py
│       ├── mental-models/
│       │   └── mental-models.md
│       └── src/main/java/util/ # Symlinks into source tree
│           └── ...
```

## Per-View `regen.py` Scripts

Each view gets its own `regen.py` script tailored to that view's file selection logic. Scripts are **project-specific artifacts** — not generic tooling — because the optimal file groupings depend on the repository's structure, conventions, and domain.

### Why Per-View Scripts?

Having one script per view (rather than one global script) enables **granular staleness detection**: when a view's `regen.py` changes, only that view's mental models (and root sections referencing that view) are flagged stale — other views are unaffected.

### Script Requirements

Every `regen.py` MUST:

1. **Use relative symlinks** — call `os.path.relpath(target, link_parent)` so views work inside Docker containers where the repo is mounted at a different path
2. **Create `mental-models/` directory** — `(VIEW_DIR / "mental-models").mkdir(exist_ok=True)`
3. **Be idempotent** — re-running the script recreates the view correctly (skip existing symlinks, handle moved/deleted files)
4. **Derive paths from the script's own location** — use `Path(__file__).resolve().parent` for the view directory and navigate up to the repo root

### Sample `regen.py`

```python
#!/usr/bin/env python3
"""Regenerate the api-module view."""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VIEW_DIR = Path(__file__).resolve().parent

def regenerate():
    (VIEW_DIR / "mental-models").mkdir(exist_ok=True)
    for pattern in ["src/main/java/api/**/*.java", "src/main/java/models/**/*.java"]:
        for path in REPO_ROOT.glob(pattern):
            link = VIEW_DIR / path.relative_to(REPO_ROOT)
            link.parent.mkdir(parents=True, exist_ok=True)
            if not link.exists():
                # IMPORTANT: Use relative symlinks so views work inside Docker
                # containers where the repo is mounted at a different path.
                rel_target = os.path.relpath(path, link.parent)
                link.symlink_to(rel_target)

if __name__ == "__main__":
    regenerate()
```

### What Makes Good View Boundaries?

When generating view scripts, consider:

- **Module boundaries** — group files that form a cohesive module (e.g., all API controllers + their models)
- **Layer boundaries** — separate infrastructure from domain logic
- **Feature boundaries** — group files related to a specific feature
- **Dependency direction** — files that depend on each other belong in the same view or a parent view
- **Size** — each view should be small enough for a local LLM to reason over (roughly 10-50 files)

### Fallback: Single Flat View

If a repository has no recognizable structure, produce a single flat "all-files" view as a fallback.

## When to Regenerate Views

Views should be regenerated:

1. **After a completed ticket that modified the repository's file structure** — files may have been added, moved, or deleted
2. **When the agent detects the view's file set is out of sync** — new files in the source tree that match the view's patterns but don't have symlinks yet
3. **When instructed to refresh** — a user or orchestrator explicitly requests regeneration

After regeneration, mental models for views whose file set changed are flagged stale by the chain of custody system (the metadata records the `regen.py` script hash — if it changed, all sections in that view are flagged for review).

## Running View Scripts

```bash
# Run a single view's script
python views/api-module/regen.py

# Run all views
for d in views/*/; do python "$d/regen.py"; done
```

## Relationship to Mental Models

Views provide the **file selection** layer. Mental models provide the **understanding** layer. The chain of custody system (see `multi_agent_ide_view_agents` skill) tracks which source files each mental model section references, using `git hash-object` to detect when those files change.

The `regen.py` script hash is also tracked — if the script itself changes, the view's file composition may have changed, so all mental model sections for that view are flagged for review.
