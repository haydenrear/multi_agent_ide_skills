---
name: multi_agent_ide_view_generation
description: Instructional skill for generating and maintaining stale-aware, symlink-based repository views. Views are concept-centric mental-model projections over code, not package mirrors or file-by-file summaries. They support progressive disclosure by surfacing conceptual drift only where underlying source artifacts have changed.
---

Use this skill when you need to generate, maintain, or regenerate **repository views** — symlink-based directory structures that externalize and preserve mental models of a system across files, modules, packages, skills, and repositories.

# Core Doctrine

This skill does **not** generate arbitrary documentation.

It does **not** optimize for package mirroring, per-file summaries, or structural coverage of a repository.

It **does** optimize for the maintainer's actual pain point:

> preserve the mental models they rely on, attach those models to the source artifacts that realize them, and surface staleness only when those models may no longer match reality.

A view is therefore **not** a folder digest. It is a **staleness-aware cognitive projection** over a live codebase.

The unit of organization is **not** the package, module, or directory tree.  
The unit of organization is the **mental model of a capability, workflow, process, interface contract, or cross-cutting concept**.

## What This Skill Is For

Use this skill to build views for things like:

- Request or event lifecycles
- API → CLI → skill or SDK integration flows
- Validation, deployment, or migration workflows
- Routing and orchestration frameworks
- Cross-cutting interface contracts
- Failure, retry, or recovery paths
- Shared engineering intuitions embodied across multiple packages
- Capabilities implemented across multiple repositories
- Framework behaviors that do not align with a single package boundary

Do **not** use this skill to produce:

- Generic repository documentation
- Package copies under `views/`
- Per-file summaries with no cross-cutting insight
- Line-by-line explanation artifacts
- "What exists in this folder?" style outputs

If the generated output is mostly copying package layout and summarizing each file independently, the skill has failed.

# What Are Views?

A **view** is a directory under `views/` at the repository root containing:

1. **Symbolic links** pointing back into the source tree using relative paths
2. A **`regen.py`** script that recreates the symlink structure for that conceptual view
3. A **`mental-models/`** subdirectory containing model files and metadata for the concept the view preserves
4. Optionally, metadata that links the view to parent or child views in a progressive-disclosure hierarchy

Views exist to reduce rediscovery cost. They let an agent or maintainer inspect only the conceptual area that matters, and only descend into more detail when some underlying source artifact has made the model stale.

## The Important Distinction

Traditional docs answer:

> What code is here?

Views answer:

> What understanding do I rely on here, and has it gone stale?

That is the purpose of this skill.

# Progressive Disclosure and Staleness

Views participate in a hierarchy.

A root view contains high-level mental models that reference child views.  
Child views contain narrower mental models grounded in specific source artifacts via symlinks.

When a source artifact changes:

- the affected child view may become stale
- only the mental model sections grounded in that artifact should be considered suspect
- parent views should surface that staleness without forcing full re-expansion of unrelated areas
- maintainers should only descend into the stale child when needed

This is **progressive disclosure of conceptual drift**.

The goal is not just file change detection. The goal is to transform code changes into **conceptual change signals**.

# Initialization and Lifecycle

## Initializing the View Root

The root mental model lives at `views/mental-models/`. It references child views and provides cross-view synthesis. Initialize it like any other view:

```bash
view-model init views/mental-models --repo $REPO
```

## Initializing a New View

The full onboarding sequence for a new view:

```bash
REPO=/path/to/repo
VIEW=views/my-view

# 1. Create the view directory
mkdir -p $VIEW

# 2. Write regen.py (see "Per-View regen.py Scripts" below)

# 3. Bootstrap metadata — creates .metadata/mental-model-content.json, empty mental-models.md, HEAD
view-model init $VIEW --repo $REPO

# 4. Write section content (does NOT flip HEAD — sections remain STALE)
view-model update $VIEW \
  --path '$.sections["My Section"]' \
  --value-file /tmp/section_content.txt \
  --package 'my-section' \
  --repo $REPO

# 5. Add source file references (flips HEAD via atomic_commit_view — makes sections CURRENT)
view-model add-ref $VIEW \
  --path '$.sections["My Section"]' \
  --file 'path/to/SourceFile.java' \
  --repo $REPO

# 6. Regenerate symlinks
python $VIEW/regen.py

# 7. Render markdown
view-model render $VIEW --write --repo $REPO
```

**Critical:** Step 5 (`add-ref`) is the only command that flips HEAD. If you skip it, sections stay STALE forever.

## Package References in Views

Each mental model **section** maps to a **package name**. This package name:

1. Becomes a **directory** inside the view (e.g., `views/acp-module/acp-chat-model-session/`)
2. Groups **symlinks** to all source files referenced in that section
3. Is stored in `mental-model-content.json` as `sections["Section Name"].package`
4. Is rendered in markdown with staleness annotations

The package name is set during `view-model update` with the `--package` flag. Choose names that reflect the **concept**, not the source package path:

```bash
# Good — concept-centered
--package 'goal-lifecycle'
--package 'acp-chat-model-session'
--package 'event-artifact-system'

# Bad — mirrors source package path
--package 'com-hayden-acp-cdc-ai-acp'
--package 'src-main-java-api'
```

The regen.py script's `SECTION_FILES` list must use these same package names as directory groupings so that symlinks land in the correct section directories.

# Repository Hierarchy

```text
<repo-root>/
├── views/
│   ├── mental-models/                  # Root-level synthesis and cross-view models
│   │   ├── mental-models.md
│   │   └── .metadata/
│   │       ├── mental-model-content.json
│   │       └── HEAD -> <metadata-id>.json
│   ├── api-cli-skill-contract/
│   │   ├── regen.py
│   │   ├── mental-models/
│   │   │   ├── mental-models.md
│   │   │   └── .metadata/
│   │   │       ├── mental-model-content.json
│   │   │       └── HEAD -> <metadata-id>.json
│   │   ├── goal-lifecycle/             # Section package directory
│   │   │   └── GoalService.java -> ../../../../src/.../GoalService.java
│   │   └── event-flow/
│   │       └── Events.java -> ../../../../src/.../Events.java
│   └── render_all.py                   # Batch render convenience script
```

Do not assume a view corresponds to a single package or subtree. A single view may intentionally gather files from several directories or repositories if they jointly realize one capability.

# Per-View `regen.py` Scripts

Each view gets its own `regen.py` script.

These scripts are **project-specific conceptual artifacts**, not generic tooling. The file selection logic must reflect the repository's actual architecture, naming, conventions, and cross-cutting workflows.

## Why Per-View Scripts?

A per-view script enables:

- View-local regeneration
- View-local staleness detection (the script's git hash is tracked in metadata)
- Incremental maintenance
- Clear mapping from conceptual unit to artifact selection logic

If a view's `regen.py` changes, that is evidence the conceptual grouping itself may have changed. The view should therefore be flagged stale, and parent references to that view should also be reviewed.

## Script Requirements

Every `regen.py` MUST:

1. **Use relative symlinks** — `os.path.relpath(target, link_parent)` so views work in containers and different mount points
2. **Create `mental-models/` if missing** — `(VIEW_DIR / "mental-models").mkdir(parents=True, exist_ok=True)`
3. **Derive paths from the script location** — `Path(__file__).resolve().parent` for VIEW_DIR, navigate up to REPO_ROOT
4. **Be idempotent** — re-running must produce the same correct result
5. **Express conceptual grouping clearly** — the SECTION_FILES list should make the concept legible
6. **Clean up stale symlinks** — remove dangling symlinks from previous runs before recreating
7. **Avoid package cloning** — include only files materially needed for the view
8. **Allow cross-module selection** — the view boundary is conceptual, not structural

## Script Pattern

```python
#!/usr/bin/env python3
"""Regenerate the <view-name> view."""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VIEW_DIR = Path(__file__).resolve().parent

# Files grouped by mental-model section package name
SECTION_FILES = [
    ("section-package-name", "path/to/source/file.java"),
    ("section-package-name", "path/to/another/file.kt"),
    ("other-section",       "different/module/file.py"),
]

def _cleanup_stale_symlinks(view_dir: Path):
    """Remove all symlinks under the view directory (except in mental-models/)."""
    for item in sorted(view_dir.rglob("*")):
        if item.is_symlink() and "mental-models" not in item.parts:
            item.unlink()
    for item in sorted(view_dir.rglob("*"), reverse=True):
        if item.is_dir() and "mental-models" not in str(item.relative_to(view_dir)):
            try:
                item.rmdir()
            except OSError:
                pass

def regenerate():
    (VIEW_DIR / "mental-models").mkdir(exist_ok=True)
    _cleanup_stale_symlinks(VIEW_DIR)
    for section_dir, rel_path in SECTION_FILES:
        source = REPO_ROOT / rel_path
        if not source.exists():
            print(f"  WARN: {rel_path} does not exist, skipping")
            continue
        link_dir = VIEW_DIR / section_dir
        link = link_dir / source.name
        link_dir.mkdir(parents=True, exist_ok=True)
        if not link.exists():
            rel_target = os.path.relpath(source, link.parent)
            link.symlink_to(rel_target)

if __name__ == "__main__":
    regenerate()
```

# Updating, Refreshing, and Rendering Views

For the full CLI reference and workflow details, see the **`multi_agent_ide_view_agents`** skill (`SKILL.md`).

The standard workflow is:

```
1. update content  →  2. add-ref (flips HEAD)  →  3. regen.py (symlinks)  →  4. render (markdown)
```

Key commands (all via `uv run --project multi_agent_ide_python_parent/packages/view_agents_utils`):

| Command | Purpose |
|---------|---------|
| `view-model update` | Set content/package in mental-model-content.json |
| `view-model add-ref` | Add source file reference; **only command that flips HEAD** |
| `view-model add-ref-root` | Add child view reference to root section |
| `view-model render` | Render mental-models.md from content JSON |
| `view-model status` | Report CURRENT/STALE per section |
| `view-model files` | List curated references per section |
| `view-custody search` | Traverse the metadata chain of custody |

### Batch Operations

```bash
# Render all views
python views/render_all.py
# or
uv run --project multi_agent_ide_python_parent view-model render --all --repo .

# Regenerate all symlinks
find views -mindepth 1 -maxdepth 1 -type d -exec test -f "{}/regen.py" \; -print | while read -r d; do
  python "$d/regen.py"
done
```

# What Makes a Good View Boundary?

Good view boundaries follow **maintenance relevance** and **conceptual locality**, not just filesystem locality.

Prefer boundaries based on:

- A single capability or user-visible behavior
- A workflow that spans multiple implementation areas
- A cross-cutting contract or integration surface
- A framework or reusable orchestration pattern
- A failure mode or recovery mechanism
- A set of files that must usually change together conceptually

Use these heuristics:

- Group files that jointly realize one concept
- Keep the view small enough for focused reasoning (roughly 10-50 files)
- Include source artifacts from multiple modules when necessary
- Avoid swallowing whole packages unless the package itself is truly the concept
- Prefer the minimum artifact set that preserves the mental model

> Package mirroring preserves implementation locality.  
> View generation must preserve conceptual locality.

# What Makes a Bad View

These are failure patterns:

- Copying an entire package into a view without a concept-centered reason
- Producing file-by-file summaries with no interaction model
- Grouping by path because it is easy rather than because it reflects a behavior
- Creating views that cannot answer why the included files belong together
- Creating views that surface too much raw detail at the root
- Requiring the user to maintain large specs manually to recover the intended grouping

# Mental Model Types

A view's mental model may represent any of the following:

- **Process Model** — how a capability happens end to end
- **Workflow Model** — ordered stages, handoffs, and transitions
- **Interaction Model** — how components communicate
- **Contract Model** — cross-boundary assumptions or interfaces
- **Framework Model** — a reusable pattern or architecture
- **Invariant Model** — what must remain true
- **Failure Model** — how the system breaks and recovers
- **Concept Model** — an engineering intuition embodied across the code
- **Cross-Repo Capability Model** — one behavior realized in several repositories

When unsure, prefer a **process**, **workflow**, or **contract** model over a structural package summary.

# How to Identify the Right Concept

Before writing `regen.py`, identify the view's conceptual unit. Ask:

- What capability, process, workflow, or contract is being preserved?
- What mental model would a maintainer want to notice if it went stale?
- Which artifacts materially participate in realizing that concept?
- Which artifacts are merely nearby and should be excluded?
- What parent view should surface this concept if it changes?

The primary question is **not** "What files are in scope?" but rather **"What concept is this view preserving, and which artifacts materially realize it?"**

# Mental Models Inside a View

A view's `mental-models/` directory should explain:

- What concept the view preserves
- Why these artifacts belong together
- What the process or workflow is
- What invariants matter
- What external dependencies or child views matter
- What failures or drift modes are expected
- What evidence links claims back to source artifacts
- What should be checked first when stale

A good mental model should let a maintainer answer quickly:

- What behavior is being modeled?
- Where does it start and end?
- Which artifacts realize it?
- What role does each artifact play?
- What invalidates this model?
- What should I inspect first?

Do not turn the mental model into file-local summaries stitched together.

# Relationship to Parent and Child Views

A root view should not duplicate every child view's details. Instead:

- Reference the child concept
- Summarize why that child matters
- Mark the child stale when its underlying artifacts or regeneration logic drift
- Let the user descend only when necessary

Child views should:

- Hold the narrower conceptual model
- Link directly to the source artifacts
- Provide stronger evidence and finer-grained staleness

This enables hierarchical cognitive compression.

# Staleness Rules

A view should be considered stale when any of the following occur:

1. A source artifact referenced by the view has changed
2. A source artifact previously matched by the view no longer exists
3. A newly relevant artifact should now belong in the view
4. The `regen.py` selection logic changed (tracked via view_script_hash)
5. A parent view's assumptions about the child no longer match the child model
6. Metadata or chain-of-custody evidence no longer matches the current snapshot

Staleness surfaces at the **lowest affected conceptual layer first**, then propagates upward.

# Source Locations for Questions and Issues

| What | Where |
|------|-------|
| View CLI tools and metadata operations | `multi_agent_ide_python_parent/packages/view_agents_utils/` |
| View agent runners (ACP integration) | `multi_agent_ide_python_parent/packages/view_agent_exec/` |
| View management skill (CLI reference) | `skills/multi_agent_ide_skills/multi_agent_ide_view_agents/SKILL.md` |
| View agent exec skill (query/fan-out) | `skills/multi_agent_ide_skills/multi_agent_ide_view_agent_exec/SKILL.md` |
| This skill (generation/ideology) | `skills/multi_agent_ide_skills/multi_agent_ide_view_generation/SKILL.md` |
| Metadata models | `view_agents_utils/src/view_agents_utils/models/metadata.py` |
| Content models | `view_agents_utils/src/view_agents_utils/models/mental_model_content.py` |
| Staleness detection | `view_agents_utils/src/view_agents_utils/custody/staleness.py` |
| Chain-of-custody search | `view_agents_utils/src/view_agents_utils/custody/search.py` |
| Existing views | `views/` at the repository root |

# Agent Guidance

When using this skill, the agent must behave as follows:

- Think in terms of conceptual units, not package trees
- Optimize for rediscovery reduction
- Prefer cross-cutting mental models over generic summaries
- Treat staleness as a first-class signal
- Assume maintainers want to know what understanding may have drifted
- Avoid requiring large manually maintained specs
- Encode the conceptual doctrine into the generated artifacts so the user does not have to restate it every time

# Non-Negotiable Constraints

Never do the following unless the user explicitly asks for it:

- Mirror an entire package because it is easy
- Generate one summary per file as the main output
- Treat structural adjacency as sufficient reason for inclusion
- Produce documentation divorced from staleness tracking
- Require slash commands, hand-maintained spec forests, or repetitive restatement of the same ideology

# Success Criteria

This skill succeeds when the generated views:

- Preserve actual maintainer mental models
- Surface conceptual drift instead of raw file churn
- Reduce the need to rediscover cross-boundary dependencies
- Make root views feel like cognitive dashboards
- Make child views feel like precise, evidence-backed conceptual snapshots
- Remain grounded in live source artifacts through symlinks and metadata
- Can be reused without the user having to re-explain the doctrine every time
