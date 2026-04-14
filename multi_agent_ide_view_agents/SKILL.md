---
name: multi_agent_ide_view_agents
description: CLI tools and helper scripts for managing mental model views — content updates, reference tracking, rendering, and chain-of-custody search.
---

Use this skill to interact with mental models and their chain of custody. The CLI is provided by the `view_agents_utils` Python package, invoked via `uv run` from the `multi_agent_ide_python_parent` workspace.

## Quick Reference

| Command | Purpose | Writes? |
|---------|---------|---------|
| `view-model init` | Bootstrap metadata for a new view | Yes |
| `view-model update` | Set content/package in mental-model-content.json via JSONPath | Yes |
| `view-model add-ref` | Add a source file reference to a view section | Yes |
| `view-model add-ref-root` | Add a child view reference to a root section | Yes |
| `view-model delete` | Remove a section or field via JSONPath | Yes |
| `view-model render` | Render mental-models.md from content JSON | Yes |
| `view-model files` | List curated references per section | No |
| `view-model status` | Report CURRENT/STALE per section | No |
| `view-custody search` | Traverse the metadata chain of custody | No |

## Invocation

All commands run via `uv run` from the Python parent workspace:

```bash
uv run --project multi_agent_ide_python_parent \
  view-model <command> <PATH> [options...]
```

The `<PATH>` argument is flexible — it accepts:
- A view directory: `views/api-layer`
- A mental-models directory: `views/api-layer/mental-models`
- A file inside mental-models/: `views/api-layer/mental-models/mental-models.md`

The tool resolves the mental-models directory automatically.

### Helper Scripts

The `scripts/` directory provides two convenience wrappers that auto-resolve `--repo` and handle `uv run` invocation:

| Script | Wraps |
|--------|-------|
| `scripts/view_model.py` | `view-model` commands with auto `--repo` resolution |
| `scripts/search_custody.py` | `view-custody search` with auto `--repo` resolution |

## Command Reference

### `view-model init`

Bootstrap metadata for a new view. Creates `.metadata/mental-model-content.json`, empty `mental-models.md`, and HEAD metadata. Idempotent.

```bash
view-model init views/my-view --repo /path/to/repo
```

### `view-model update`

Set a value in `mental-model-content.json` at a JSONPath. This is the primary command for writing/updating section content.

```bash
view-model update <PATH> \
  --path '<jsonpath>' \
  --value '<content>'          # short inline content
  --package '<package-name>'   # optional, for section targets only
```

**Flags:**
- `--path` (required): JSONPath expression targeting what to set
- `--value`: Inline value (for short content)
- `--value-file`: Read value from a file (for long content — avoids shell escaping)
- `--value-stdin`: Read value from stdin
- `--package`: Package name (only when targeting a section node, not a `.content` leaf)

Only one of `--value`, `--value-file`, or `--value-stdin` is allowed.

**JSONPath examples:**
```
$.view_name                                         → the view name
$.sections["Goal Lifecycle"]                        → a section node (sets content + package)
$.sections["Goal Lifecycle"].content                → section body text only
$.sections["Goal Lifecycle"].package                → section package only
$.sections["Goal Lifecycle"].subsections["Bootstrap"]  → a subsection
$.sections["New Section"]                           → create a new section
```

**For long content, use `--value-file`:**
```bash
# Write content to a temp file first
cat > /tmp/content.txt << 'CONTENT_EOF'
The full section content goes here.
Multiple paragraphs, markdown formatting, etc.
CONTENT_EOF

view-model update views/my-view \
  --path '$.sections["My Section"]' \
  --value-file /tmp/content.txt \
  --package 'my-section' \
  --repo /path/to/repo
```

### `view-model add-ref`

Add a source file reference to a view-level section. **This is the only command that flips HEAD** (via `atomic_commit_view`).

```bash
view-model add-ref <PATH> \
  --path '$.sections["REST Controllers"]' \
  --file 'multi_agent_ide_java_parent/multi_agent_ide/src/main/java/.../MyFile.java' \
  --repo /path/to/repo
```

**Flags:**
- `--path` (required): JSONPath of the target section
- `--file` (required): Source file path, relative to repo root
- `--line-span`: Optional `start_line:line_count` for partial file reference
- `--repo`: Repository root (default: `/repo`)

### `view-model add-ref-root`

Add a child view reference to a root-level section.

```bash
view-model add-ref-root views/mental-models \
  --path '$.sections["The 14 Views"]' \
  --child-view 'api-layer' \
  --child-path '$.sections["REST Controllers"]' \
  --repo /path/to/repo
```

**Flags:**
- `--path` (required): JSONPath of the target section
- `--child-view` (required): Child view name
- `--child-path` (required, repeatable): Child section JSONPath to reference
- `--repo`: Repository root (default: `/repo`)

### `view-model delete`

Remove a section or field via JSONPath. Prints the deleted content to stdout for recovery.

```bash
view-model delete views/my-view \
  --path '$.sections["Obsolete Section"]'
```

### `view-model render`

Render `mental-model-content.json` as markdown or JSON.

```bash
# Full render (writes to mental-models.md)
view-model render views/my-view --repo /path/to/repo --write

# Render a single section to stdout
view-model render views/my-view \
  --path '$.sections["Goal Lifecycle"]' \
  --repo /path/to/repo

# JSON output
view-model render views/my-view --format json --repo /path/to/repo
```

**Flags:**
- `--format`: `markdown` (default) or `json`
- `--path`: JSONPath to target a specific section (prints to stdout)
- `--write / --no-write`: Write to file (default: yes for full, no for targeted)
- `--include-refs / --no-refs`: Include file reference counts (default: yes)
- `--repo`: Repository root (default: `/repo`)

### `view-model files`

List curated references per section.

```bash
view-model files views/my-view --repo /path/to/repo
view-model files views/my-view --path '$.sections["REST Controllers"]' --format json --repo /path/to/repo
```

### `view-model status`

Report CURRENT/STALE status per section without rendering full content.

```bash
view-model status views/my-view --repo /path/to/repo
view-model status views/my-view --format json --repo /path/to/repo
```

### `view-custody search`

Traverse the metadata chain of custody.

```bash
view-custody search views/my-view \
  --path '$.sections["REST Controllers"]' \
  --repo /path/to/repo

# Filter by source file
view-custody search views/my-view \
  --file 'path/to/SomeFile.java'

# Filter by date range
view-custody search views/my-view \
  --date-range '2026-01-01..2026-04-01'
```

**Flags:**
- `--path`: Filter to a specific section JSONPath
- `--file`: Filter by source file path
- `--child-view`: Filter by child view name (root-level)
- `--child-path`: Filter by child section JSONPath within a child view
- `--hash-range`: Filter by content-hash range `from..to`
- `--date-range`: Filter by date range `YYYY-MM-DD..YYYY-MM-DD`
- `--max-depth`: Maximum chain depth
- `--format`: `text` or `json` (default: `json`)

## Standard Workflow

The correct sequence for updating a view is:

```
1. update content  →  2. add-ref (flips HEAD)  →  3. regen.py (symlinks)  →  4. render (markdown)
```

Concretely:

```bash
REPO=/path/to/repo
VIEW=views/my-view

# 1. Update section content
view-model update $VIEW \
  --path '$.sections["My Section"]' \
  --value-file /tmp/content.txt \
  --package 'my-section' \
  --repo $REPO

# 2. Add source file references (flips HEAD — makes sections CURRENT)
view-model add-ref $VIEW \
  --path '$.sections["My Section"]' \
  --file 'path/to/SourceFile.java' \
  --repo $REPO

# 3. Regenerate symlinks
python $VIEW/regen.py

# 4. Render markdown
view-model render $VIEW --write --repo $REPO
```

**If you skip step 2**, sections will remain STALE because only `add-ref` calls `atomic_commit_view()` which flips HEAD.

## Tips and Tricks

### Always pass `--repo` explicitly

The default `--repo` is `/repo` (a Docker container path). When running locally, always pass the actual repo root:

```bash
--repo /Users/you/IdeaProjects/multi_agent_ide_parent
```

### Use `--value-file` for long content, never `--value`

Shell escaping for multiline content with quotes, backticks, and special characters is extremely fragile. Always write content to a temp file first:

```bash
cat > /tmp/my_content.txt << 'EOF'
Your content here with **markdown**, `backticks`, and "quotes".
EOF

view-model update ... --value-file /tmp/my_content.txt
```

Make sure the temp file contains **actual newlines**, not literal `\n` escape sequences. The `Write` tool creates real newlines naturally; shell `echo -e` or Python `print()` also work. But string concatenation with `\n` literals will store escaped characters.

### `update` does NOT flip HEAD — `add-ref` does

After `update`, sections show as STALE until you run `add-ref` (or `add-ref-root` for root views). This is by design: `update` modifies the content JSON, while `add-ref` creates a new metadata commit via `atomic_commit_view()`.

If you only need to update content (no new refs), you can run `add-ref` with an already-tracked file to flip HEAD without adding a duplicate.

### JSON metadata files are chmod 444

The `.metadata/mental-model-content.json` and metadata JSON files are set read-only (444) after writes to prevent accidental edits. The CLI's `write_content_json()` function unlocks before overwriting. If you need to edit manually, `chmod 644` first.

### CliRunner works where Bash CLI may not

When called from Claude Code's `Bash` tool, the CLI can sometimes fail silently (especially with permission-locked files or incorrect paths). Using Click's `CliRunner` in a Python script is more reliable for programmatic use because it runs in-process.

### The `--path` flag is JSONPath, not a section heading

The `--path` flag on `add-ref`, `update`, `delete`, `files`, and `search` is a **JSONPath expression**, not a plain section name. Always use the full JSONPath syntax:

```
--path '$.sections["Section Name"]'           # correct
--path 'Section Name'                         # WRONG — will fail silently or error
```

### Batch rendering with `render_all.py`

To render all views at once:

```bash
python views/render_all.py
```

This iterates all VIEW_NAMES and calls `render_cmd` for each.

### Onboarding a new view

```bash
# 1. Create the view directory and regen.py
mkdir -p views/my-view

# 2. Write regen.py with SECTION_FILES

# 3. Initialize metadata
view-model init views/my-view --repo $REPO

# 4. Update content for each section
view-model update views/my-view \
  --path '$.sections["Section Name"]' \
  --value-file /tmp/section_content.txt \
  --package 'section-name' \
  --repo $REPO

# 5. Add source file refs (flips HEAD)
view-model add-ref views/my-view \
  --path '$.sections["Section Name"]' \
  --file 'path/to/file.java' \
  --repo $REPO

# 6. Regenerate symlinks
python views/my-view/regen.py

# 7. Render
view-model render views/my-view --write --repo $REPO

# 8. Add to render_all.py VIEW_NAMES list
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 5 | Referenced file or path not found |
| 6 | Duplicate section path (legacy) |
| 7 | Scope mismatch (view vs root command) |
