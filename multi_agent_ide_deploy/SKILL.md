---
name: multi_agent_ide_deploy
description: Deploy skill for multi_agent_ide — clone or pull to /private/tmp, run verification gate, deploy with health check.
---

Use this skill when you need to clone, sync, or restart the `multi_agent_ide` application for a test or debug session.

> **CRITICAL: Never run `deploy_restart.py` from the source checkout** (`~/IdeaProjects/multi_agent_ide_parent` or similar). Always deploy from the tmp repo (`/private/tmp/multi_agent_ide_parent/multi_agent_ide_parent`). The deploy flow is: push changes from source → pull in tmp repo → deploy from tmp repo.

## Tmp repo persistence
- The deploy script saves the `--project-root` path to `/private/tmp/multi_agent_ide_parent/tmp_repo.txt` on every successful deploy.
- On subsequent runs, read this file to find the existing tmp repo instead of cloning a new one.
- If `/private/tmp/multi_agent_ide_parent/tmp_repo.txt` is missing or empty, `deploy_restart.py` will **exit with an error** — run `clone_or_pull.py` first to clone and write this file.
- To sync changes into the existing tmp repo, push from your source repo then pull in the tmp repo. Only clone fresh if the tmp repo is missing or corrupted.

## Script: `scripts/clone_or_pull.py`

Three-phase deploy preparation:

**Phase 1 — Clone/Sync**: Detects if `/private/tmp/multi_agent_ide_parent/tmp_repo.txt` exists. If yes, syncs all repos to the specified branch (default: `main`). If no, clones fresh from the specified branch.

**Phase 2 — Verification Gate**: Validates dirty files, detached HEADs, SHA alignment. Returns structured JSON errors; exits non-zero on gate failure.

**Phase 3 — Provision**: Creates required executor cwd (`multi_agent_ide_java_parent/multi_agent_ide/bin`) and persists the tmp repo path.

### Usage
```bash
# Full flow: clone/sync + gate + provision (defaults to main branch)
python scripts/clone_or_pull.py

# Clone/sync from a specific branch
python scripts/clone_or_pull.py --branch develop
python scripts/clone_or_pull.py --branch feature/xyz

# Status check only (no changes)
python scripts/clone_or_pull.py --status

# Force fresh clone even if tmp repo exists
python scripts/clone_or_pull.py --force-clone

# Clone/sync + gate + provision, then print deploy command (don't deploy)
python scripts/clone_or_pull.py --skip-deploy

# Use custom repo URL
python scripts/clone_or_pull.py --repo-url <url>

# Dry run (validates args, no network calls)
python scripts/clone_or_pull.py --dry-run
```

### Environment
- `MULTI_AGENT_IDE_REPO_URL` — override default GitHub URL

### Branch support
By default, `clone_or_pull.py` operates on the `main` branch for backward compatibility. To work with other branches, use the `--branch` flag:

```bash
# Clone from develop branch
python scripts/clone_or_pull.py --branch develop

# Sync existing tmp repo to feature branch
python scripts/clone_or_pull.py --branch feature/xyz

# Explicitly specify main (same as no --branch)
python scripts/clone_or_pull.py --branch main
```

The script will:
1. Clone/checkout the specified branch in the root repository
2. Automatically switch each submodule to the branch checked out in the source repository (via `checkout_source_branches()`)
3. Verify all repos are clean and properly synced

This enables parallel execution on non-main branches for testing, feature development, and multi-branch workflows.

### Gate failures
If Phase 2 fails, the script exits with code `2` and prints JSON like:
```json
{
  "ok": false,
  "results": [
    {"phase": "gate", "ok": false, "issues": [{"repo": "root", "issue": "dirty working tree", "files": "M somefile.java"}]}
  ]
}
```
Fix the reported issues before retrying. Common causes:
- Uncommitted changes in submodules — commit and push first
- Detached HEAD — `git switch main` in the affected submodule
- SHA mismatch — ensure you pushed all changes from source repo before syncing
- **Submodule pointer not committed** — if a submodule (e.g. `skills`) shows "modified content" or "new commits" in the gate, the *parent* of that submodule has not yet committed and pushed the updated pointer. This is a two-level problem for nested submodules: `multi_agent_ide_skills` inside `skills` inside the root. Fix order:
  1. `cd skills && git add multi_agent_ide_skills && git commit -m "Update pointer" && git push origin main`
  2. `cd .. && git add skills && git commit -m "Update skills submodule pointer" && git push origin main`
  Then re-run `clone_or_pull.py`.

## Script: `scripts/deploy_restart.py`

Restarts the application on port 8080 and waits for `/actuator/health` to return `UP`.

### Usage
```bash
python scripts/deploy_restart.py [--project-root <path>] [--profile claude|claudellama|codex] [--wait-seconds 180] [--port 8080]
```

### Options
- `--project-root` — path to the cloned repo root. **Defaults to the path stored in `tmp_repo.txt`**. If `tmp_repo.txt` is missing or points to a non-existent directory, the script exits with an error telling you to run `clone_or_pull.py` first.
- `--profile` — Spring profile. Default: `claude`. Use `claudellama` for local Ollama/LLaMA.
- `--wait-seconds` — health check wait timeout in seconds (default 180)
- `--port` — application port (default 8080)
- `--dry-run` — validate without executing

### Profiles
- `claudellama` — local Ollama/LLaMA; script runs `ollama serve` in background before boot
- `claude` — Anthropic Claude (default)
- `codex` — OpenAI Codex

### Log files
- **Build/Gradle**: `<project-root>/build-log.log` — build output only
- **Application runtime**: `<project-root>/multi-agent-ide.log` — workflow events, errors (check this for runtime issues)
- **ACP/LLM errors**: `<project-root>/multi_agent_ide_java_parent/multi_agent_ide/claude-agent-acp-errs.log`

### Important notes
- **Always deploy from the tmp repo**, not from your source checkout. Run `clone_or_pull.py` first — it writes `tmp_repo.txt` and `deploy_restart.py` reads it automatically.
- The `multi_agent_ide_python_parent` submodule does not exist on GitHub — ignore its clone failure.
- External `PYTHON`/`BINARY` filter executors use `filter.bins` as subprocess cwd. For tmp deployments this resolves to `<tmp-repo>/multi_agent_ide_java_parent/multi_agent_ide/bin`. Ensure this directory exists before deploying.

## Typical deploy flow

```bash
# 1. Push changes from source repo
git submodule foreach --recursive 'git add . && git commit -m "preparing" || true'
git submodule foreach --recursive 'git push origin main || true'
git add . && git commit -m "preparing" && git push origin main

# 2. Clone/sync tmp repo and run verification gate
python skills/multi_agent_ide_deploy/scripts/clone_or_pull.py

# 3. Deploy (reads tmp_repo.txt automatically — no --project-root needed)
python skills/multi_agent_ide_deploy/scripts/deploy_restart.py --profile claudellama
```

Or use the `clone_or_pull.py` script which handles all three phases and prints the next deploy command when run with `--skip-deploy`.

## Branch support
The deploy flow now supports arbitrary branches (not just `main`). Use the `--branch` flag with `clone_or_pull.py` to deploy from other branches:

```bash
python scripts/clone_or_pull.py --branch feature/xyz
python scripts/deploy_restart.py
```

By default (without `--branch`), the script operates on `main` for backward compatibility. All repositories and submodules are synced to the specified branch automatically.

### Branch deployment troubleshooting
If the application fails to clone/worktree-branch after deploy, re-run the pre-deploy verification gate first. Detached HEAD or stale submodule SHAs are the most common cause of clone/branch errors. When working with non-main branches, ensure:
1. All repositories have the target branch created and pushed
2. Submodule pointers are committed with the correct branch checkouts
3. The verification gate passes before deploying

---

## Reusable scripts (`scripts/`)

**Before writing inline bash/shell one-offs for deploy operations, check `scripts/` first.**

| Script | Purpose |
|--------|---------|
| `scripts/clone_or_pull.py` | Three-phase deploy prep: clone/sync → verification gate → provision |
| `scripts/deploy_restart.py` | Deploy and restart the application with health check |
| `scripts/create-feature-branch.py` | Create and push a feature branch across root + all submodules |
| `scripts/sync-feature-branch.py` | Sync (pull) a feature branch across root + all submodules |
| `scripts/merge-feature-to-main.py` | Merge a feature branch into main across root + all submodules |
| `scripts/pull-merged-code.py` | Pull latest main after merge, across root + all submodules |

### Workflow
1. **Before automating any deploy step** (cloning, syncing, health checking), check if a script already handles it.
2. **If a matching script exists**, use it. If it can be improved (additional flags, better error output), update it.
3. **If no match exists**, write a new script to `scripts/` — it should be self-contained, accept CLI args, and print structured output.

These scripts are the accumulation of deployment knowledge across sessions. Each improvement makes future deploys faster and more reliable.

### Branch management scripts

For parallel execution on feature branches, use these helper scripts. They manage branch state across the root repository and all submodules automatically:

**Create a feature branch:**
```bash
python scripts/create-feature-branch.py --branch feature/ticket-001
# Creates and pushes feature/ticket-001 in root + all submodules
```

**Sync a feature branch (pull latest):**
```bash
python scripts/sync-feature-branch.py --branch feature/ticket-001
# Pulls latest in root + all submodules, switches to branch first
```

**Merge feature branch into main:**
```bash
python scripts/merge-feature-to-main.py --branch feature/ticket-001
# Merges feature/ticket-001 into main in root + all submodules
```

**Pull main after merge:**
```bash
python scripts/pull-merged-code.py
# Switches all repos to main and pulls latest (after merge-feature-to-main.py)
```

See `standard_workflow.md` in `multi_agent_ide_controller` for full parallel execution workflow documentation including branch creation, multi-branch coordination, and troubleshooting.

---

## Merge-back workflow orchestration

The merge-back workflow enables end-of-ticket merge-back operations for parallel execution. When a goal (ticket) is complete, the feature branch is merged back into main, and all changes are propagated through submodule pointers.

### Complete merge-back workflow

**Step 1: Verify feature branch state**
```bash
# Ensure all changes are committed and pushed on the feature branch
python scripts/sync-feature-branch.py --branch feature/ticket-001
# Verifies all repos are clean and up-to-date on the feature branch
```

**Step 2: Merge feature branch into main**
```bash
# Merge across root + all 19 submodules, auto-update submodule pointers
python scripts/merge-feature-to-main.py --branch feature/ticket-001
# Exit code: 0 = success, 1 = merge errors, 2 = merge conflicts
```

If merge returns exit code 2 (conflicts), see "Handling merge conflicts" below.

**Step 3: Pull merged code into tmp repo**
```bash
# Switch to main and pull latest in root + all submodules
python scripts/pull-merged-code.py
# Prepares tmp_repo for next goal or deployment
```

**Step 4: Optionally delete feature branch**
```bash
# Clean up feature branch across root + submodules
git submodule foreach --recursive 'git branch -d feature/ticket-001 || true'
git branch -d feature/ticket-001
git submodule foreach --recursive 'git push origin --delete feature/ticket-001 || true'
git push origin --delete feature/ticket-001
```

### Return value format

All merge-back scripts return structured JSON:

**merge-feature-to-main.py return:**
```json
{
  "ok": true,
  "branch": "feature/ticket-001",
  "merged": ["root", "buildSrc", "persistence", ...],
  "merge_conflicts": [],
  "already_on_main": [],
  "errors": null,
  "merge_commits": {
    "root": "abc123def456",
    "buildSrc": "def456ghi789",
    ...
  }
}
```

**pull-merged-code.py return:**
```json
{
  "ok": true,
  "pulled": ["root", "buildSrc", ...],
  "pull_errors": null,
  "branch_checkout_errors": null,
  "clean_state": true
}
```

---

## Integration guide: Controller merge-back orchestration

Controllers and orchestrators use the merge-back scripts to automate end-of-ticket operations. Integration flow:

### 1. After ticket agent completes goal
When a ticket goal finishes (all agents done, changes committed to feature branch), invoke merge-back:

```bash
# From orchestrator or controller script
BRANCH="feature/ticket-001"
INSTANCE_ID="goal-1"

# Merge to main
python scripts/merge-feature-to-main.py --branch $BRANCH
if [ $? -ne 0 ]; then
  echo "Merge failed or conflicts detected"
  # See "Handling merge conflicts" section below
  exit 1
fi

# Pull merged code into instance tmp repo
python scripts/pull-merged-code.py --instance-id $INSTANCE_ID
if [ $? -ne 0 ]; then
  echo "Pull failed"
  # See "Recovery procedures" section below
  exit 1
fi
```

### 2. Validate merge success
Check return JSON for:
- `"ok": true` — merge and pull both succeeded
- `"merged"` list matches expected repos
- `"merge_conflicts": null` — no conflicts
- `"clean_state": true` — all repos clean after pull

### 3. Next steps
After successful merge-back:
- Delete feature branch (optional cleanup)
- Update goal status to MERGED
- Proceed to next goal or complete workflow

### 4. Multi-goal coordination
When multiple goals are merging concurrently:
- Each goal operates on its own instance-id (separate tmp repos)
- Merge-back operations serialize through main branch (git naturally serializes pushes)
- If push conflict occurs (concurrent pushes), script fails with clear error
- See "Handling push conflicts" below for recovery

---

## Error handling and recovery procedures

### Merge conflicts during merge-feature-to-main.py

**Symptom:** Script returns exit code 2 with merge_conflicts list:
```json
{
  "ok": false,
  "merge_conflicts": ["root", "buildSrc"],
  ...
}
```

**Recovery:**

1. **Inspect conflicts:**
```bash
# Find conflicted files
cd /path/to/repo/root
git status
# Or in affected submodule
cd /path/to/repo/buildSrc
git status
```

2. **Resolve conflicts:**
```bash
# Edit conflicted files to resolve
# (git shows conflict markers like <<<<<<<, =======, >>>>>>>)
nano src/main/java/ConflictedFile.java

# Stage resolved files
git add src/main/java/ConflictedFile.java

# Complete merge
git commit -m "Resolve merge conflicts"

# Push to main
git push origin main
```

3. **Retry merge:**
```bash
# Re-run merge script (it will skip already-merged repos)
python scripts/merge-feature-to-main.py --branch feature/ticket-001
```

### Push conflicts (concurrent merges)

**Symptom:** Script returns exit code 1 with push_error:
```json
{
  "ok": false,
  "errors": [
    {"repo": "root", "push_error": "rejected ... (non-fast-forward)"}
  ]
}
```

**Cause:** Another goal merged and pushed to main while this goal was merging.

**Recovery:**

1. **Pull latest main:**
```bash
cd /path/to/repo/root
git fetch origin
git rebase origin/main
# Or git merge origin/main
```

2. **Resolve any new conflicts (if rebase conflicts occur):**
```bash
# Repeat conflict resolution for rebased commits
git add <files>
git rebase --continue
```

3. **Push resolved changes:**
```bash
git push origin main
```

4. **Propagate to submodules:**
```bash
# Update submodule pointers in parent
git add .
git commit -m "Update submodule pointers after rebase"
git push origin main
```

5. **Retry:**
```bash
python scripts/merge-feature-to-main.py --branch feature/ticket-001
```

### Pull failures after merge

**Symptom:** pull-merged-code.py returns exit code 1 with pull_errors:
```json
{
  "ok": false,
  "pull_errors": [{"repo": "root", "error": "..."}],
  ...
}
```

**Common causes:**
- Remote main branch is ahead of local (another goal just merged)
- Merge conflicts in pull (rare, indicates merge-to-main incompleteness)
- Network error

**Recovery:**

1. **Check current branch state:**
```bash
git status
git log --oneline -5
```

2. **If branch not on main, switch:**
```bash
git checkout main
```

3. **Fetch and rebase/merge:**
```bash
git fetch origin
git merge origin/main
```

4. **Retry pull script:**
```bash
python scripts/pull-merged-code.py --instance-id goal-1
```

### Submodule pointer corruption

**Symptom:** After merge-back, submodule pointers in parent don't match actual submodule commits.
Detection: `git status` shows submodule as "modified content" but nothing changed locally.

**Recovery:**

1. **Verify state in submodule:**
```bash
cd buildSrc
git log --oneline -1  # Check current commit
git branch -v  # Verify on correct branch
```

2. **Update pointer in parent:**
```bash
cd ..  # Back to root
git add buildSrc
git commit -m "Fix submodule pointer"
git push origin main
```

3. **Re-verify:**
```bash
git status  # Should show clean
```

4. **Propagate to tmp repos:**
```bash
python scripts/pull-merged-code.py --instance-id goal-1
```

### Rollback (undo merge-back)

If merge-back needs to be completely undone (rare):

1. **Reset root to pre-merge commit:**
```bash
# Find pre-merge commit
git log --oneline | grep "Merge"
git reset --hard <commit-before-merge>
git push origin main --force-with-lease
```

2. **Reset all submodules:**
```bash
git submodule foreach 'git reset --hard <commit-before-merge> && git push origin main --force-with-lease || true'
```

3. **Re-create feature branch from main:**
```bash
git checkout -b feature/ticket-001
```

**CAUTION: Force push is destructive. Use only if absolutely necessary and coordinate with other agents/goals.**

### Diagnostic commands

Verify merge-back state:
```bash
# Check all repos on main
git branch && git submodule foreach --recursive git branch

# Verify clean state
git status && git submodule foreach --recursive git status

# View recent merges
git log --oneline --merges -10

# Compare submodule pointers with actual commits
git submodule foreach 'echo "=== $name ===" && git log --oneline -1'
```
