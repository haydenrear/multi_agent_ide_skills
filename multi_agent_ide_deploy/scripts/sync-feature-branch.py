#!/usr/bin/env python3
"""
sync-feature-branch.py — Sync (pull) a feature branch across root + all submodules.

Switches to specified branch and pulls latest changes in root and all submodules.
Useful for staying up-to-date while working on a feature branch.

Usage:
  python sync-feature-branch.py --branch feature/ticket-001
  python sync-feature-branch.py --branch feature/xyz --dry-run

Returns JSON with:
  {
    "ok": true,
    "branch": "feature/ticket-001",
    "synced": ["root", "buildSrc", ...],
    "branch_not_found": [],
    "errors": []
  }
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run shell command and return result."""
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check)


def git(args: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run git command and return result."""
    return run(["git"] + args, cwd=cwd, check=check)


def get_submodules(root_path: Path) -> list[str]:
    """Get list of submodule paths from .gitmodules."""
    gitmodules = root_path / ".gitmodules"
    if not gitmodules.exists():
        return []

    submodules = []
    with open(gitmodules) as f:
        for line in f:
            if line.strip().startswith("path = "):
                submodule_path = line.split("=", 1)[1].strip()
                submodules.append(submodule_path)
    return submodules


def sync_feature_branch(root_path: Path, branch: str, dry_run: bool = False) -> dict:
    """Sync feature branch in root and all submodules."""
    synced = []
    branch_not_found = []
    errors = []

    # Root repository
    if dry_run:
        synced.append("root")
    else:
        # Try to checkout branch
        checkout_result = git(["checkout", branch], cwd=str(root_path), check=False)
        if checkout_result.returncode != 0:
            branch_not_found.append("root")
        else:
            # Pull latest
            pull_result = git(["pull", "origin", branch], cwd=str(root_path), check=False)
            if pull_result.returncode != 0:
                errors.append({"repo": "root", "error": pull_result.stderr.strip()})
            else:
                synced.append("root")

    # Submodules
    submodules = get_submodules(root_path)
    for submodule_path in submodules:
        submodule_full_path = root_path / submodule_path
        if not submodule_full_path.exists():
            continue

        if dry_run:
            synced.append(submodule_path)
        else:
            # Try to checkout branch
            checkout_result = git(["checkout", branch], cwd=str(submodule_full_path), check=False)
            if checkout_result.returncode != 0:
                branch_not_found.append(submodule_path)
            else:
                # Pull latest
                pull_result = git(["pull", "origin", branch], cwd=str(submodule_full_path), check=False)
                if pull_result.returncode != 0:
                    errors.append({"repo": submodule_path, "error": pull_result.stderr.strip()})
                else:
                    synced.append(submodule_path)

    return {
        "ok": len(errors) == 0,
        "branch": branch,
        "dry_run": dry_run,
        "synced": synced,
        "branch_not_found": branch_not_found,
        "errors": errors if errors else None
    }


def main():
    """Parse args and sync feature branch."""
    parser = argparse.ArgumentParser(description="Sync feature branch across root + submodules")
    parser.add_argument("--branch", required=True, help="Branch name (e.g. feature/ticket-001)")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no changes)")
    args = parser.parse_args()

    # Find repo root (4 parents up from scripts/ to reach worktree root)
    script_dir = Path(__file__).resolve().parent
    root_path = script_dir.parent.parent.parent.parent

    if not (root_path / ".git").exists():
        print(json.dumps({"ok": False, "error": f"Not a git repo: {root_path}"}), file=sys.stderr)
        sys.exit(1)

    result = sync_feature_branch(root_path, args.branch, args.dry_run)
    print(json.dumps(result))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
