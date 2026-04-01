#!/usr/bin/env python3
"""
merge-feature-to-main.py — Merge feature branches into main with conflict detection.

Merges feature branches into main across the root repository and all submodules.
Implements conflict detection and reporting (continue non-conflicting merges).
Supports --dry-run flag to preview merge sequence without executing.
Implements innermost-to-outermost commit/push ordering.

Usage:
  python merge-feature-to-main.py --branch BRANCH_NAME [--dry-run]

Example:
  python merge-feature-to-main.py --branch feature/my-feature
  python merge-feature-to-main.py --branch feature/my-feature --dry-run
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
    This ensures that parent-level commits include all submodule updates.
    """
    # Sort by depth descending (deepest first)
    return sorted(submodules, key=get_submodule_depth, reverse=True)


def merge_branch_in_repo(cwd: str, branch: str, target_branch: str = "main") -> tuple[bool, str | None]:
    """
    Merge a branch into the target branch in a single repo.
    Returns (success: bool, error_msg: str | None)
    Detects merge conflicts and returns error message if conflicts exist.
    """
    # Switch to target branch
    r = git(["switch", target_branch], cwd=cwd, check=False)
    if r.returncode != 0:
        return False, f"Failed to switch to {target_branch}: {r.stderr.strip()}"

    # Attempt merge
    r = git(["merge", branch], cwd=cwd, check=False)
    if r.returncode != 0:
        # Check if it's a merge conflict
        status_r = git(["status"], cwd=cwd, check=False)
        if "both added" in status_r.stdout or "both modified" in status_r.stdout or "conflict" in status_r.stdout.lower():
            # Abort the merge and report conflict
            git(["merge", "--abort"], cwd=cwd, check=False)
            return False, f"Merge conflict detected when merging {branch} into {target_branch}"
        else:
            return False, f"Failed to merge {branch} into {target_branch}: {r.stderr.strip()}"

    return True, None


def merge_branches_in_submodules(repo_path: str, branch: str, target_branch: str = "main", dry_run: bool = False) -> dict:
    """
    Merge branches in all submodules in innermost-to-outermost order.
    Returns dict with 'merged', 'conflicts', and 'errors' lists.
    If dry_run is True, only reports what would be done without executing.
    """
    merged = []
    conflicts = []
    errors = []

    # Get all submodules
    submodules = get_submodules(repo_path)

    # Order submodules innermost-first (deepest nested first)
    submodules = order_submodules_innermost_first(submodules)

    # Process each submodule
    for submodule_path in submodules:
        if dry_run:
            merged.append(submodule_path)
        else:
            sub_cwd = str(Path(repo_path) / submodule_path)
            success_flag, error = merge_branch_in_repo(sub_cwd, branch, target_branch)

            if success_flag:
                merged.append(submodule_path)
            else:
                if "conflict" in error.lower():
                    conflicts.append({"path": submodule_path, "error": error})
                else:
                    errors.append({"path": submodule_path, "error": error})

    return {
        "merged": merged,
        "conflicts": conflicts,
        "errors": errors
    }


def commit_and_push_changes(repo_path: str, submodules: list[str], dry_run: bool = False) -> tuple[bool, str | None]:
    """
    Commit and push changes in innermost-to-outermost order.
    Returns (success: bool, error_msg: str | None)
    If dry_run is True, only reports what would be done.
    """
    # Order submodules innermost-first for commit/push
    ordered_submodules = order_submodules_innermost_first(submodules)

    # Commit and push each submodule (innermost-first)
    for submodule_path in ordered_submodules:
        sub_cwd = str(Path(repo_path) / submodule_path)

        if dry_run:
            continue

        # Check if there are changes to commit
        status_r = git(["status", "--porcelain"], cwd=sub_cwd, check=False)
        if status_r.stdout.strip():
            # Commit the merge
            r = git(["commit", "-m", "Merge changes into main"], cwd=sub_cwd, check=False)
            if r.returncode != 0:
                return False, f"Failed to commit in {submodule_path}: {r.stderr.strip()}"

            # Push the branch
            r = git(["push", "origin", "main"], cwd=sub_cwd, check=False)
            if r.returncode != 0:
                return False, f"Failed to push from {submodule_path}: {r.stderr.strip()}"

    # Commit and push root repository (last)
    if dry_run:
        return True, None

    # Check if there are changes in root
    status_r = git(["status", "--porcelain"], cwd=repo_path, check=False)
    if status_r.stdout.strip():
        # Commit the merge
        r = git(["commit", "-m", "Merge changes into main"], cwd=repo_path, check=False)
        if r.returncode != 0:
            return False, f"Failed to commit in root repository: {r.stderr.strip()}"

        # Push the branch
        r = git(["push", "origin", "main"], cwd=repo_path, check=False)
        if r.returncode != 0:
            return False, f"Failed to push from root repository: {r.stderr.strip()}"

    return True, None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge feature branches into main with conflict detection"
    )
    parser.add_argument("--branch", required=True,
                        help="Feature branch name to merge (e.g., feature/my-feature)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview merge sequence without executing git commands")

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

    # Merge branch in root repository
    if args.dry_run:
        root_merged = True
        root_error = None
    else:
        root_merged, root_error = merge_branch_in_repo(repo_path, args.branch)
        if not root_merged:
            return failure({"error": root_error, "location": "root"})

    # Merge branches in all submodules (innermost-to-outermost order)
    submodule_results = merge_branches_in_submodules(repo_path, args.branch, dry_run=args.dry_run)

    # Check for conflicts or errors
    if submodule_results["conflicts"] or submodule_results["errors"]:
        output = {
            "branch": args.branch,
            "root_merged": root_merged,
            "submodules_merged": submodule_results["merged"],
            "conflicts": submodule_results["conflicts"],
            "errors": submodule_results["errors"],
            "dry_run": args.dry_run
        }
        return failure(output)

    # Commit and push changes
    if not args.dry_run:
        all_merged = [args.branch] if root_merged else []
        all_merged.extend(submodule_results["merged"])
        push_success, push_error = commit_and_push_changes(repo_path, all_merged, dry_run=args.dry_run)
        if not push_success:
            return failure(push_error)

    # Build output
    output = {
        "branch": args.branch,
        "root_merged": root_merged,
        "submodules_merged": submodule_results["merged"],
        "dry_run": args.dry_run
    }

    return success(output)


if __name__ == "__main__":
    sys.exit(main())
