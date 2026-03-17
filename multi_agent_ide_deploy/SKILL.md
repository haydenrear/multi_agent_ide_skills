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

**Phase 1 — Clone/Sync**: Detects if `/private/tmp/multi_agent_ide_parent/tmp_repo.txt` exists. If yes, syncs all repos to `main`. If no, clones fresh.

**Phase 2 — Verification Gate**: Validates dirty files, detached HEADs, SHA alignment. Returns structured JSON errors; exits non-zero on gate failure.

**Phase 3 — Provision**: Creates required executor cwd (`multi_agent_ide_java_parent/multi_agent_ide/bin`) and persists the tmp repo path.

### Usage
```bash
# Full flow: clone/sync + gate + provision
python scripts/clone_or_pull.py

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

## Only deploy from `main`
Do not use other branches unless explicitly asked. When pushing and pulling, always operate on `main` for all repositories and submodules.

If the application fails to clone/worktree-branch after deploy, re-run the pre-deploy verification gate first. Detached HEAD or stale submodule SHAs are the most common cause of clone/branch errors.

---

## Reusable scripts (`scripts/`)

**Before writing inline bash/shell one-offs for deploy operations, check `scripts/` first.**

| Script | Purpose |
|--------|---------|
| `scripts/clone_or_pull.py` | Three-phase deploy prep: clone/sync → verification gate → provision |
| `scripts/deploy_restart.py` | Deploy and restart the application with health check |

### Workflow
1. **Before automating any deploy step** (cloning, syncing, health checking), check if a script already handles it.
2. **If a matching script exists**, use it. If it can be improved (additional flags, better error output), update it.
3. **If no match exists**, write a new script to `scripts/` — it should be self-contained, accept CLI args, and print structured output.

These scripts are the accumulation of deployment knowledge across sessions. Each improvement makes future deploys faster and more reliable.
