#!/usr/bin/env python3
"""
pull-merged-code.py — Pull main after merge-back across root + all submodules.

Switches all repos to main and pulls latest. Run after merge-feature-to-main.py
to ensure all repos are up-to-date with merged changes. Useful for syncing
tmp_repo after merge-back completes.

Usage:
  python pull-merged-code.py
  python pull-merged-code.py --dry-run
  python pull-merged-code.py --instance-id goal-1

Returns JSON with:
  {
    "ok": true,
    "pulled": ["root", "buildSrc", ...],
    "pull_errors": [],
    "branch_checkout_errors": [],
    "clean_state": true
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


def is_clean(repo_path: Path) -> bool:
    """Check if repo is clean (no dirty files, no conflicts)."""
    # Check for dirty working tree
    status = git(["status", "--porcelain"], cwd=str(repo_path), check=False)
    if status.stdout.strip():
        return False
    # Check for merge conflicts
    result = git(["ls-files", "--unmerged"], cwd=str(repo_path), check=False)
    return len(result.stdout.strip()) == 0


def pull_merged_code(root_path: Path, dry_run: bool = False) -> dict:
    """Pull main in root and all submodules."""
    pulled = []
    pull_errors = []
    branch_checkout_errors = []
    clean_state = True

    # Root repository
    if dry_run:
        pulled.append("root")
    else:
        # Checkout main
        checkout_result = git(["checkout", "main"], cwd=str(root_path), check=False)
        if checkout_result.returncode != 0:
            branch_checkout_errors.append({"repo": "root", "error": checkout_result.stderr.strip()})
            clean_state = False
        else:
            # Pull latest
            pull_result = git(["pull", "origin", "main"], cwd=str(root_path), check=False)
            if pull_result.returncode != 0:
                pull_errors.append({"repo": "root", "error": pull_result.stderr.strip()})
                clean_state = False
            else:
                pulled.append("root")

            # Check for unmerged files
            if not is_clean(root_path):
                pull_errors.append({"repo": "root", "error": "Working tree has conflicts or uncommitted changes"})
                clean_state = False

    # Submodules
    submodules = get_submodules(root_path)
    for submodule_path in submodules:
        submodule_full_path = root_path / submodule_path
        if not submodule_full_path.exists():
            continue

        if dry_run:
            pulled.append(submodule_path)
        else:
            # Checkout main
            checkout_result = git(["checkout", "main"], cwd=str(submodule_full_path), check=False)
            if checkout_result.returncode != 0:
                branch_checkout_errors.append({"repo": submodule_path, "error": checkout_result.stderr.strip()})
                clean_state = False
            else:
                # Pull latest
                pull_result = git(["pull", "origin", "main"], cwd=str(submodule_full_path), check=False)
                if pull_result.returncode != 0:
                    pull_errors.append({"repo": submodule_path, "error": pull_result.stderr.strip()})
                    clean_state = False
                else:
                    pulled.append(submodule_path)

                # Check for unmerged files
                if not is_clean(submodule_full_path):
                    pull_errors.append({"repo": submodule_path, "error": "Working tree has conflicts or uncommitted changes"})
                    clean_state = False

    return {
        "ok": len(pull_errors) == 0 and len(branch_checkout_errors) == 0,
        "dry_run": dry_run,
        "pulled": pulled,
        "pull_errors": pull_errors if pull_errors else None,
        "branch_checkout_errors": branch_checkout_errors if branch_checkout_errors else None,
        "clean_state": clean_state
    }


def main():
    """Parse args and pull merged code."""
    parser = argparse.ArgumentParser(description="Pull main after merge-back across root + submodules")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no changes)")
    parser.add_argument("--instance-id", default=None, help="Instance ID (for documentation, no effect on operation)")
    args = parser.parse_args()

    # Find repo root (4 parents up from scripts/ to reach worktree root)
    script_dir = Path(__file__).resolve().parent
    root_path = script_dir.parent.parent.parent.parent

    if not (root_path / ".git").exists():
        print(json.dumps({"ok": False, "error": f"Not a git repo: {root_path}"}), file=sys.stderr)
        sys.exit(1)

    result = pull_merged_code(root_path, args.dry_run)
    if args.instance_id:
        result["instance_id"] = args.instance_id
    print(json.dumps(result))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
