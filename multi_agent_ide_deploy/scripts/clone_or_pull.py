#!/usr/bin/env python3
"""
clone_or_pull.py — Three-phase deploy preparation for multi_agent_ide.

Phase 1 — Clone/Sync:
  If /private/tmp/multi_agent_ide_parent/tmp_repo.txt exists and the directory is valid,
  pull all repos to main. Otherwise clone fresh.

Phase 2 — Verification Gate:
  Check dirty files, detached HEADs, and SHA alignment.
  Returns structured JSON errors; exits non-zero on gate failure.

Phase 3 — Deploy:
  Provisions required directories and optionally invokes deploy_restart.py.

Usage:
  python clone_or_pull.py [--repo-url URL] [--branch BRANCH] [--dry-run] [--skip-deploy]
  python clone_or_pull.py --status   # check current tmp repo state only

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

DEFAULT_REPO_URL = "git@github.com:haydenrear/multi_agent_ide_parent.git"
TMP_BASE = Path("/private/tmp/multi_agent_ide_parent")
TMP_REPO_FILE = TMP_BASE / "tmp_repo.txt"

# Script lives at <source_root>/skills/multi_agent_ide_skills/multi_agent_ide_deploy/scripts/
SOURCE_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent


# ── helpers ───────────────────────────────────────────────────────────────────

def run(cmd: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check)


def git(args: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return run(["git"] + args, cwd=cwd, check=check)


def read_tmp_repo() -> Path | None:
    if not TMP_REPO_FILE.exists():
        return None
    path_str = TMP_REPO_FILE.read_text().strip()
    if not path_str:
        return None
    p = Path(path_str)
    return p if p.exists() and (p / ".git").exists() else None


def write_tmp_repo(path: Path) -> None:
    TMP_BASE.mkdir(parents=True, exist_ok=True)
    TMP_REPO_FILE.write_text(str(path))


# ── phase 1: clone or sync ────────────────────────────────────────────────────

def phase1_clone(repo_url: str, branch: str, dry_run: bool) -> dict:
    import re
    # derive directory name from repo url
    name = re.sub(r"\.git$", "", repo_url.rstrip("/").split("/")[-1])
    target = TMP_BASE / name

    if dry_run:
        return {"phase": "clone", "dry_run": True, "target": str(target), "url": repo_url, "branch": branch}

    TMP_BASE.mkdir(parents=True, exist_ok=True)
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

    write_tmp_repo(target)
    return {"phase": "clone", "ok": True, "path": str(target), "branches": branch_result}


def phase1_sync(repo_path: Path, branch: str, dry_run: bool) -> dict:
    if dry_run:
        return {"phase": "sync", "dry_run": True, "path": str(repo_path), "branch": branch}

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
        return {"phase": "sync", "ok": False, "errors": errors, "path": str(repo_path), "branches": branch_result}
    return {"phase": "sync", "ok": True, "path": str(repo_path), "branches": branch_result}


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


# ── phase 2b: pre-deploy SHA comparison (source vs tmp) ──────────────────────

def get_all_submodule_shas(root: Path) -> dict[str, str]:
    """Return {relative_path: short_sha} for root + all recursive submodules."""
    shas = {}
    root_sha = get_sha(str(root))
    if root_sha:
        shas["."] = root_sha

    r = run(["git", "submodule", "foreach", "--recursive", "--quiet",
             "echo $displaypath"], cwd=str(root), check=False)
    for line in r.stdout.splitlines():
        sub = line.strip()
        if not sub:
            continue
        sub_path = root / sub
        if sub_path.exists():
            sha = get_sha(str(sub_path))
            if sha:
                shas[sub] = sha
    return shas


def _normalize_sha(sha1: str | None, sha2: str | None) -> tuple[str | None, str | None]:
    """Truncate both SHAs to the shorter length so repos with different object counts compare equal."""
    if sha1 and sha2:
        min_len = min(len(sha1), len(sha2))
        return sha1[:min_len], sha2[:min_len]
    return sha1, sha2


def phase2b_pre_deploy_verify(source_root: Path, tmp_path: Path) -> dict:
    """Compare SHAs between source repo and tmp repo for all submodules.
    Returns {"pre_deploy": true} if all match, or {"pre_deploy": false, "mismatches": [...]}."""
    source_shas = get_all_submodule_shas(source_root)
    tmp_shas = get_all_submodule_shas(tmp_path)

    mismatches = []
    all_keys = sorted(set(source_shas.keys()) | set(tmp_shas.keys()))
    for key in all_keys:
        src, tmp = _normalize_sha(source_shas.get(key), tmp_shas.get(key))
        if src != tmp:
            entry = {"repo": key}
            if src:
                entry["source"] = src
            else:
                entry["source"] = None
                entry["note"] = "missing in source"
            if tmp:
                entry["tmp"] = tmp
            else:
                entry["tmp"] = None
                entry["note"] = "missing in tmp"
            mismatches.append(entry)

    if not mismatches:
        return {"phase": "pre_deploy", "pre_deploy": True}
    return {"phase": "pre_deploy", "pre_deploy": False, "mismatches": mismatches}


# ── phase 3: provision ────────────────────────────────────────────────────────

def phase3_provision(repo_path: Path, dry_run: bool) -> dict:
    bin_dir = repo_path / "multi_agent_ide_java_parent" / "multi_agent_ide" / "bin"

    if dry_run:
        return {"phase": "provision", "dry_run": True, "bin_dir": str(bin_dir)}

    bin_dir.mkdir(parents=True, exist_ok=True)
    write_tmp_repo(repo_path)

    return {"phase": "provision", "ok": True, "bin_dir": str(bin_dir), "path": str(repo_path)}


# ── status check ─────────────────────────────────────────────────────────────

def status() -> dict:
    repo = read_tmp_repo()
    if not repo:
        return {"status": "no_tmp_repo", "tmp_repo_file": str(TMP_REPO_FILE)}
    gate = phase2_gate(repo)
    gate["status"] = "ok" if gate["ok"] else "gate_failed"
    return gate


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Clone or pull multi_agent_ide to /private/tmp")
    parser.add_argument("--repo-url", default=os.environ.get("MULTI_AGENT_IDE_REPO_URL", DEFAULT_REPO_URL),
                        help="Repository URL to clone (default: MULTI_AGENT_IDE_REPO_URL or GitHub URL)")
    parser.add_argument("--branch", default="main",
                        help="Branch to clone/sync to (default: main)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print actions without executing")
    parser.add_argument("--skip-deploy", action="store_true",
                        help="Stop after provisioning; do not invoke deploy_restart.py")
    parser.add_argument("--status", action="store_true",
                        help="Report current tmp repo state and exit")
    parser.add_argument("--force-clone", action="store_true",
                        help="Clone fresh even if a valid tmp repo exists")
    args = parser.parse_args()

    if args.status:
        print(json.dumps(status(), indent=2))
        return

    results = []

    # Phase 1
    existing = None if args.force_clone else read_tmp_repo()
    if existing:
        r1 = phase1_sync(existing, args.branch, args.dry_run)
        repo_path = existing
    else:
        r1 = phase1_clone(args.repo_url, args.branch, args.dry_run)
        if not args.dry_run and not r1.get("ok"):
            print(json.dumps({"ok": False, "results": [r1]}, indent=2))
            sys.exit(1)
        repo_path = Path(r1.get("path", "")) if not args.dry_run else TMP_BASE / "dry-run"
    results.append(r1)

    if args.dry_run:
        results.append({"phase": "gate", "dry_run": True})
        results.append({"phase": "pre_deploy", "dry_run": True})
        results.append({"phase": "provision", "dry_run": True})
        print(json.dumps({"ok": True, "dry_run": True, "results": results}, indent=2))
        return

    # Phase 2
    r2 = phase2_gate(repo_path)
    results.append(r2)
    if not r2["ok"]:
        print(json.dumps({"ok": False, "results": results}, indent=2))
        sys.exit(2)

    # Phase 2b — pre-deploy SHA verification (source vs tmp)
    r2b = phase2b_pre_deploy_verify(SOURCE_ROOT, repo_path)
    results.append(r2b)
    if not r2b["pre_deploy"]:
        print(json.dumps({"ok": False, "results": results}, indent=2))
        sys.exit(2)

    # Phase 3
    r3 = phase3_provision(repo_path, args.dry_run)
    results.append(r3)

    output = {"ok": True, "results": results, "path": str(repo_path)}
    if args.skip_deploy:
        output["next_step"] = f"python {Path(__file__).parent}/deploy_restart.py --project-root {repo_path}"
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
