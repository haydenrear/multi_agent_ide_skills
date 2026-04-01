#!/usr/bin/env python3
"""
sync-feature-branch.py — Sync feature branches across root and all submodules.

Syncs (pulls) feature branches across the root repository and all submodules
using git submodule foreach --recursive. Implements innermost-to-outermost
processing order to ensure consistent state.

Usage:
  python sync-feature-branch.py --branch BRANCH_NAME

Example:
  python sync-feature-branch.py --branch feature/my-feature
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent))

from _result import failure, success


# ── constants ─────────────────────────────────────────────────────────────────

SCRIPTS_DIR = Path(__file__).resolve().parent


# ── helpers ───────────────────────────────────────────────────────────────────

def run(cmd: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check)


def git(args: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return run(["git"] + args, cwd=cwd, check=check)


def validate_branch_name(branch: str) -> str | None:
    """Validate branch name format. Returns error message if invalid, None if valid."""
    if not branch or not branch.strip():
        return "Branch name cannot be empty"

    # Check for valid git branch name (no spaces, valid characters)
    if not re.match(r'^[a-zA-Z0-9/_\-\.]+$', branch):
        return f"Invalid branch name: {branch}. Use only alphanumeric, /, -, _, and . characters"

    return None


def get_submodules(cwd: str) -> list[str]:
    """Get list of all submodules (paths) via git submodule foreach --recursive."""
    r = git(["submodule", "foreach", "--recursive", "--quiet", "echo $displaypath"],
            cwd=cwd, check=False)
    if r.returncode != 0:
        return []
    return [p.strip() for p in r.stdout.splitlines() if p.strip()]


def get_submodule_depth(submodule_path: str) -> int:
    """Return the nesting depth of a submodule path (number of slashes)."""
    return submodule_path.count('/')


def order_submodules_innermost_first(submodules: list[str]) -> list[str]:
    """
    Order submodules so that deepest nested are first, then progressively shallower.
    This ensures consistent processing state.
    """
    # Sort by depth descending (deepest first)
    return sorted(submodules, key=get_submodule_depth, reverse=True)


def sync_branch_in_repo(cwd: str, branch: str) -> tuple[bool, str | None]:
    """
    Sync/pull a branch in a single repo.
    Handles case where branch may not exist locally yet (creates tracking from remote if needed).
    Returns (success: bool, error_msg: str | None)
    """
    # Try to switch to the branch (if it exists locally)
    r = git(["switch", branch], cwd=cwd, check=False)
    if r.returncode != 0:
        # Branch doesn't exist locally, try to create it tracking from remote
        r = git(["switch", "-c", branch, f"--track=origin/{branch}"], cwd=cwd, check=False)
        if r.returncode != 0:
            return False, f"Failed to switch to or create tracking branch {branch}: {r.stderr.strip()}"

    # Pull the branch
    r = git(["pull", "origin", branch], cwd=cwd, check=False)
    if r.returncode != 0:
        return False, f"Failed to pull branch {branch}: {r.stderr.strip()}"

    return True, None


def sync_branches_in_submodules(repo_path: str, branch: str) -> dict:
    """
    Sync branches in all submodules in innermost-to-outermost order.
    Returns dict with 'synced' and 'failed' lists.
    """
    synced = []
    failed = []

    # Get all submodules
    submodules = get_submodules(repo_path)
    if not submodules:
        return {"synced": [], "failed": []}

    # Order submodules innermost-first (deepest nested first)
    submodules = order_submodules_innermost_first(submodules)

    # Process each submodule
    for submodule_path in submodules:
        sub_cwd = str(Path(repo_path) / submodule_path)
        success_flag, error = sync_branch_in_repo(sub_cwd, branch)

        if success_flag:
            synced.append(submodule_path)
        else:
            failed.append({"path": submodule_path, "error": error})

    return {"synced": synced, "failed": failed}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync feature branches across root and all submodules"
    )
    parser.add_argument("--branch", required=True,
                        help="Feature branch name to sync (e.g., feature/my-feature)")

    args = parser.parse_args()

    # Validate branch name
    validation_error = validate_branch_name(args.branch)
    if validation_error:
        return failure(validation_error)

    # Get current working directory (root repo)
    repo_path = str(Path.cwd())

    # Verify it's a git repo
    r = git(["rev-parse", "--git-dir"], cwd=repo_path, check=False)
    if r.returncode != 0:
        return failure("Current directory is not a git repository")

    # Sync branch in root repository
    success_flag, error = sync_branch_in_repo(repo_path, args.branch)
    if not success_flag:
        return failure(error)

    # Sync branches in all submodules (innermost-to-outermost order)
    submodule_results = sync_branches_in_submodules(repo_path, args.branch)

    # Build output
    output = {
        "branch": args.branch,
        "root_synced": True,
        "submodules_synced": submodule_results["synced"],
    }

    if submodule_results["failed"]:
        output["submodule_errors"] = submodule_results["failed"]
        # If any submodules failed, report overall failure but include partial results
        return failure(output)

    return success(output)


if __name__ == "__main__":
    sys.exit(main())
