#!/usr/bin/env python3
"""
create-feature-branch.py — Create feature branches across root and all submodules.

Creates and checks out feature branches across the root repository and all submodules
using git submodule foreach --recursive. Implements innermost-to-outermost commit/push
ordering to ensure parent repositories include all submodule updates.

Usage:
  python create-feature-branch.py --branch BRANCH_NAME [--dry-run]

Example:
  python create-feature-branch.py --branch feature/my-feature
  python create-feature-branch.py --branch feature/my-feature --dry-run
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
    This ensures parent repositories include all submodule updates when committing.
    """
    # Sort by depth descending (deepest first)
    return sorted(submodules, key=get_submodule_depth, reverse=True)


def create_branch_in_repo(cwd: str, branch: str, dry_run: bool) -> tuple[bool, str | None]:
    """
    Create/checkout a branch in a single repo.
    Returns (success: bool, error_msg: str | None)
    """
    if dry_run:
        return True, None

    # Try to create branch (may already exist)
    r = git(["branch", branch], cwd=cwd, check=False)
    if r.returncode != 0 and "already exists" not in r.stderr:
        # Branch creation failed for non-existence reason
        pass

    # Switch to the branch
    r = git(["switch", branch], cwd=cwd, check=False)
    if r.returncode != 0:
        return False, f"Failed to switch to branch {branch}: {r.stderr.strip()}"

    return True, None


def create_branches_in_submodules(repo_path: str, branch: str, dry_run: bool) -> dict:
    """
    Create branches in all submodules.
    Returns dict with 'created' and 'failed' lists.
    """
    created = []
    failed = []

    # Get all submodules
    submodules = get_submodules(repo_path)
    if not submodules:
        return {"created": [], "failed": []}

    # Process each submodule
    for submodule_path in submodules:
        sub_cwd = str(Path(repo_path) / submodule_path)
        success_flag, error = create_branch_in_repo(sub_cwd, branch, dry_run)

        if success_flag:
            created.append(submodule_path)
        else:
            failed.append({"path": submodule_path, "error": error})

    return {"created": created, "failed": failed}


def commit_and_push(repo_path: str, branch: str, dry_run: bool) -> dict:
    """
    Commit and push branches in innermost-to-outermost order.

    Order:
    1. Process submodules in innermost-to-outermost order (deepest first)
    2. Then process the root repository

    Returns dict with 'committed', 'pushed', and 'errors' lists.
    """
    committed = []
    pushed = []
    errors = []

    submodules = get_submodules(repo_path)
    submodules = order_submodules_innermost_first(submodules)

    # Commit and push submodules
    for submodule_path in submodules:
        sub_cwd = str(Path(repo_path) / submodule_path)

        if dry_run:
            committed.append(submodule_path)
            pushed.append(submodule_path)
            continue

        # Add any changes
        r = git(["add", "-A"], cwd=sub_cwd, check=False)

        # Commit (may have nothing to commit)
        r = git(["commit", "-m", f"Create branch {branch}"], cwd=sub_cwd, check=False)
        if r.returncode == 0 or "nothing to commit" in r.stdout.lower():
            committed.append(submodule_path)
        else:
            errors.append({"path": submodule_path, "phase": "commit", "error": r.stderr.strip()})

        # Push
        r = git(["push", "-u", "origin", branch], cwd=sub_cwd, check=False)
        if r.returncode == 0:
            pushed.append(submodule_path)
        else:
            # Push might fail if branch doesn't exist on remote yet, which is OK
            errors.append({"path": submodule_path, "phase": "push", "error": r.stderr.strip()})

    # Commit and push root repository
    if dry_run:
        committed.append("root")
        pushed.append("root")
    else:
        # Add any changes
        r = git(["add", "-A"], cwd=repo_path, check=False)

        # Commit
        r = git(["commit", "-m", f"Create branch {branch}"], cwd=repo_path, check=False)
        if r.returncode == 0 or "nothing to commit" in r.stdout.lower():
            committed.append("root")
        else:
            errors.append({"path": "root", "phase": "commit", "error": r.stderr.strip()})

        # Push
        r = git(["push", "-u", "origin", branch], cwd=repo_path, check=False)
        if r.returncode == 0:
            pushed.append("root")
        else:
            errors.append({"path": "root", "phase": "push", "error": r.stderr.strip()})

    return {
        "committed": committed,
        "pushed": pushed,
        "errors": errors if errors else None
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create feature branches across root and all submodules"
    )
    parser.add_argument("--branch", required=True,
                        help="Feature branch name to create (e.g., feature/my-feature)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview actions without executing")

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

    # Create branch in root repository
    success_flag, error = create_branch_in_repo(repo_path, args.branch, args.dry_run)
    if not success_flag:
        return failure(error)

    # Create branches in all submodules
    submodule_results = create_branches_in_submodules(repo_path, args.branch, args.dry_run)

    # Commit and push in innermost-to-outermost order
    commit_results = commit_and_push(repo_path, args.branch, args.dry_run)

    # Build output
    output = {
        "branch": args.branch,
        "dry_run": args.dry_run,
        "submodules_created": submodule_results["created"],
        "root_created": "root",
        "committed": commit_results["committed"],
        "pushed": commit_results["pushed"],
    }

    if submodule_results["failed"]:
        output["submodule_errors"] = submodule_results["failed"]

    if commit_results["errors"]:
        output["commit_push_errors"] = commit_results["errors"]

    return success(output)


if __name__ == "__main__":
    sys.exit(main())
