#!/usr/bin/env python3
"""
clone_or_pull.py — Three-phase deploy preparation for multi_agent_ide.

Phase 1 — Clone/Sync:
  If <tmp_base>/tmp_repo.txt exists and the directory is valid,
  pull all repos to branch. Otherwise clone fresh.
  <tmp_base> is /private/tmp/multi_agent_ide_parent (default) or
  /private/tmp/multi_agent_ide_parent/<instance-id> (if --instance-id provided).

Phase 2 — Verification Gate:
  Check dirty files, detached HEADs, and SHA alignment.
  Returns structured JSON errors; exits non-zero on gate failure.

Phase 3 — Deploy:
  Provisions required directories and optionally invokes deploy_restart.py.

Instance-ID Support:
  The --instance-id flag enables parallel goal isolation by routing each goal
  to its own tmp repo directory. When omitted, script uses default single-instance mode.

Usage:
  python clone_or_pull.py [--repo-url URL] [--branch BRANCH] [--instance-id ID] [--dry-run] [--skip-deploy]
  python clone_or_pull.py --status [--instance-id ID]  # check tmp repo state for instance
  python clone_or_pull.py --instance-id goal-1 --branch feature-x  # clone feature-x to goal-1 instance
  python clone_or_pull.py  # clone main to default single-instance mode (backward compatible)

Environment:
  MULTI_AGENT_IDE_REPO_URL — default repo URL if --repo-url not provided
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# ── constants ─────────────────────────────────────────────────────────────────

DEFAULT_REPO_URL = "https://github.com/haydenrear/multi_agent_ide_parent.git"
TMP_BASE_DEFAULT = Path("/private/tmp/multi_agent_ide_parent")

# Script lives at <source_root>/skills/multi_agent_ide_skills/multi_agent_ide_deploy/scripts/
SOURCE_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent


# ── instance-id support ───────────────────────────────────────────────────────

def get_tmp_base(instance_id: str | None) -> Path:
    """Derive TMP_BASE based on instance_id.

    When instance_id is None, uses default single-instance path.
    When instance_id is provided, uses instance-specific path.
    """
    if instance_id is None:
        return TMP_BASE_DEFAULT
    return TMP_BASE_DEFAULT / instance_id


def get_tmp_repo_file(instance_id: str | None) -> Path:
    """Derive TMP_REPO_FILE based on instance_id."""
    tmp_base = get_tmp_base(instance_id)
    return tmp_base / "tmp_repo.txt"


# ── helpers ───────────────────────────────────────────────────────────────────

def run(cmd: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check)


def git(args: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return run(["git"] + args, cwd=cwd, check=check)


def read_tmp_repo(instance_id: str | None = None) -> Path | None:
    """Read tmp repo path from instance-specific tracking file."""
    tmp_repo_file = get_tmp_repo_file(instance_id)
    if not tmp_repo_file.exists():
        return None
    path_str = tmp_repo_file.read_text().strip()
    if not path_str:
        return None
    p = Path(path_str)
    return p if p.exists() and (p / ".git").exists() else None


def write_tmp_repo(path: Path, instance_id: str | None = None) -> None:
    """Write tmp repo path to instance-specific tracking file."""
    tmp_base = get_tmp_base(instance_id)
    tmp_base.mkdir(parents=True, exist_ok=True)
    tmp_repo_file = get_tmp_repo_file(instance_id)
    tmp_repo_file.write_text(str(path))


# ── phase 1: clone or sync ────────────────────────────────────────────────────

def phase1_clone(repo_url: str, branch: str, dry_run: bool, instance_id: str | None = None) -> dict:
    import re
    # derive directory name from repo url
    name = re.sub(r"\.git$", "", repo_url.rstrip("/").split("/")[-1])
    tmp_base = get_tmp_base(instance_id)
    target = tmp_base / name

    if dry_run:
        return {"phase": "clone", "dry_run": True, "target": str(target), "url": repo_url, "branch": branch, "instance_id": instance_id}

    tmp_base.mkdir(parents=True, exist_ok=True)
    result = run([
        "git", "clone", "--recurse-submodules", repo_url, str(target), "--branch", branch
    ], check=False)
    if result.returncode != 0:
        return {"phase": "clone", "ok": False, "error": result.stderr.strip()}

    # reset submodule working trees
    run(["git", "submodule", "foreach", "--recursive", "git reset --hard || true"],
        cwd=str(target), check=False)

    # switch each submodule to the branch checked out in the source repo
    branch_result = checkout_source_branches(SOURCE_ROOT, target)

    write_tmp_repo(target, instance_id)
    return {"phase": "clone", "ok": True, "path": str(target), "branches": branch_result, "instance_id": instance_id}


def phase1_sync(repo_path: Path, branch: str, dry_run: bool, instance_id: str | None = None) -> dict:
    if dry_run:
        return {"phase": "sync", "dry_run": True, "path": str(repo_path), "branch": branch, "instance_id": instance_id}

    errors = []
    cwd = str(repo_path)

    # switch root to specified branch
    r = git(["switch", branch], cwd=cwd, check=False)
    if r.returncode != 0:
        errors.append(f"root switch: {r.stderr.strip()}")

    r = git(["pull", "--ff-only", "origin", branch], cwd=cwd, check=False)
    if r.returncode != 0:
        errors.append(f"root pull: {r.stderr.strip()}")

    r = git(["submodule", "foreach", "--recursive",
             f"git switch {branch} || true"], cwd=cwd, check=False)
    if r.returncode != 0:
        errors.append(f"submodule switch: {r.stderr.strip()}")

    r = git(["submodule", "foreach", "--recursive",
             f"git pull --ff-only origin {branch} || true"], cwd=cwd, check=False)
    if r.returncode != 0:
        errors.append(f"submodule pull: {r.stderr.strip()}")

    git(["submodule", "foreach", "--recursive", "git reset --hard || true"],
        cwd=cwd, check=False)

    # switch each submodule to the branch checked out in the source repo
    branch_result = checkout_source_branches(SOURCE_ROOT, repo_path)

    if errors:
        return {"phase": "sync", "ok": False, "errors": errors, "path": str(repo_path), "branches": branch_result, "instance_id": instance_id}
    return {"phase": "sync", "ok": True, "path": str(repo_path), "branches": branch_result, "instance_id": instance_id}


# ── phase 2: verification gate ────────────────────────────────────────────────

def get_sha(cwd: str) -> str | None:
    r = run(["git", "rev-parse", "--short", "HEAD"], cwd=cwd, check=False)
    return r.stdout.strip() if r.returncode == 0 else None


def get_branch(cwd: str) -> str | None:
    """Return the current branch name, or None if detached HEAD."""
    r = run(["git", "symbolic-ref", "--short", "HEAD"], cwd=cwd, check=False)
    return r.stdout.strip() if r.returncode == 0 else None


def is_detached(cwd: str) -> bool:
    return get_branch(cwd) is None


def checkout_source_branches(source_root: Path, tmp_path: Path) -> dict:
    """For each submodule, read the branch checked out in the source repo and
    switch the corresponding submodule in the tmp clone to that branch."""
    r = run(["git", "submodule", "foreach", "--recursive", "--quiet", "echo $displaypath"],
            cwd=str(source_root), check=False)
    submodule_paths = [p.strip() for p in r.stdout.splitlines() if p.strip()]

    switched, failed = [], []
    for sub in submodule_paths:
        source_sub = source_root / sub
        tmp_sub = tmp_path / sub
        if not source_sub.exists() or not tmp_sub.exists():
            continue
        branch = get_branch(str(source_sub))
        if not branch:
            continue  # source is also detached — nothing to switch to
        r2 = run(["git", "switch", branch], cwd=str(tmp_sub), check=False)
        if r2.returncode == 0:
            switched.append(f"{sub}→{branch}")
        else:
            failed.append(f"{sub}: {r2.stderr.strip()}")

    return {"switched": switched, "failed": failed}


def has_dirty_files(cwd: str) -> bool:
    r = run(["git", "status", "--porcelain"], cwd=cwd, check=False)
    return bool(r.stdout.strip())


def phase2_gate(repo_path: Path) -> dict:
    cwd = str(repo_path)
    issues = []

    if is_detached(cwd):
        issues.append({"repo": "root", "issue": "detached HEAD"})

    if has_dirty_files(cwd):
        r = run(["git", "status", "--short"], cwd=cwd, check=False)
        issues.append({"repo": "root", "issue": "dirty working tree", "files": r.stdout.strip()})

    root_sha = get_sha(cwd)

    # check submodules
    r = run(["git", "submodule", "foreach", "--recursive", "--quiet",
             "echo $displaypath"], cwd=cwd, check=False)
    submodule_paths = [p.strip() for p in r.stdout.splitlines() if p.strip()]

    submodule_shas = {}
    for sub in submodule_paths:
        sub_cwd = str(repo_path / sub)
        if not Path(sub_cwd).exists():
            issues.append({"repo": sub, "issue": "directory missing"})
            continue
        if is_detached(sub_cwd):
            issues.append({"repo": sub, "issue": "detached HEAD"})
        if has_dirty_files(sub_cwd):
            issues.append({"repo": sub, "issue": "dirty working tree"})
        sha = get_sha(sub_cwd)
        if sha:
            submodule_shas[sub] = sha

    result = {
        "phase": "gate",
        "ok": len(issues) == 0,
        "root_sha": root_sha,
        "submodule_shas": submodule_shas,
        "path": str(repo_path),
    }
    if issues:
        result["issues"] = issues
    return result


# ── phase 3: provision ────────────────────────────────────────────────────────

def phase3_provision(repo_path: Path, dry_run: bool, instance_id: str | None = None) -> dict:
    bin_dir = repo_path / "multi_agent_ide_java_parent" / "multi_agent_ide" / "bin"

    if dry_run:
        return {"phase": "provision", "dry_run": True, "bin_dir": str(bin_dir), "instance_id": instance_id}

    bin_dir.mkdir(parents=True, exist_ok=True)
    write_tmp_repo(repo_path, instance_id)

    return {"phase": "provision", "ok": True, "bin_dir": str(bin_dir), "path": str(repo_path), "instance_id": instance_id}


# ── status check ─────────────────────────────────────────────────────────────

def status(instance_id: str | None = None) -> dict:
    """Check status of tmp repo for given instance_id."""
    repo = read_tmp_repo(instance_id)
    tmp_repo_file = get_tmp_repo_file(instance_id)
    if not repo:
        return {"status": "no_tmp_repo", "tmp_repo_file": str(tmp_repo_file), "instance_id": instance_id}
    gate = phase2_gate(repo)
    gate["status"] = "ok" if gate["ok"] else "gate_failed"
    gate["instance_id"] = instance_id
    return gate


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Clone or pull multi_agent_ide to /private/tmp")
    parser.add_argument("--repo-url", default=os.environ.get("MULTI_AGENT_IDE_REPO_URL", DEFAULT_REPO_URL),
                        help="Repository URL to clone (default: MULTI_AGENT_IDE_REPO_URL or GitHub URL)")
    parser.add_argument("--branch", default="main",
                        help="Branch to clone/sync to (default: main)")
    parser.add_argument("--instance-id", default=None,
                        help="Instance ID for parallel goal isolation (default: None = single-instance mode). When provided, uses /private/tmp/multi_agent_ide_parent/<instance-id>")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print actions without executing")
    parser.add_argument("--skip-deploy", action="store_true",
                        help="Stop after provisioning; do not invoke deploy_restart.py")
    parser.add_argument("--status", action="store_true",
                        help="Report current tmp repo state and exit")
    parser.add_argument("--force-clone", action="store_true",
                        help="Clone fresh even if a valid tmp repo exists")
    args = parser.parse_args()

    # Log instance-id for debugging
    if args.instance_id:
        sys.stderr.write(f"[clone_or_pull] Using instance-id: {args.instance_id}\n")
    else:
        sys.stderr.write("[clone_or_pull] Using default single-instance mode (no instance-id)\n")

    if args.status:
        print(json.dumps(status(args.instance_id), indent=2))
        return

    results = []

    # Phase 1
    existing = None if args.force_clone else read_tmp_repo(args.instance_id)
    if existing:
        r1 = phase1_sync(existing, args.branch, args.dry_run, args.instance_id)
        repo_path = existing
    else:
        r1 = phase1_clone(args.repo_url, args.branch, args.dry_run, args.instance_id)
        if not args.dry_run and not r1.get("ok"):
            print(json.dumps({"ok": False, "results": [r1]}, indent=2))
            sys.exit(1)
        repo_path = Path(r1.get("path", "")) if not args.dry_run else get_tmp_base(args.instance_id) / "dry-run"
    results.append(r1)

    if args.dry_run:
        results.append({"phase": "gate", "dry_run": True})
        results.append({"phase": "provision", "dry_run": True})
        print(json.dumps({"ok": True, "dry_run": True, "results": results, "instance_id": args.instance_id}, indent=2))
        return

    # Phase 2
    r2 = phase2_gate(repo_path)
    results.append(r2)
    if not r2["ok"]:
        print(json.dumps({"ok": False, "results": results}, indent=2))
        sys.exit(2)

    # Phase 3
    r3 = phase3_provision(repo_path, args.dry_run, args.instance_id)
    results.append(r3)

    output = {"ok": True, "results": results, "path": str(repo_path), "instance_id": args.instance_id}
    if args.skip_deploy:
        deploy_cmd = f"python {Path(__file__).parent}/deploy_restart.py --project-root {repo_path}"
        if args.instance_id:
            deploy_cmd += f" --instance-id {args.instance_id}"
        output["next_step"] = deploy_cmd
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
