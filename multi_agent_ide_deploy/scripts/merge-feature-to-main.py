#!/usr/bin/env python3
"""
merge-feature-to-main.py — Merge feature branch into main across root + all submodules.

Merges specified feature branch into main in root and all submodules,
then pushes to remote. Updates submodule pointers in parent repo.
Critical for end-of-ticket merge-back operations.

Usage:
  python merge-feature-to-main.py --branch feature/ticket-001
  python merge-feature-to-main.py --branch feature/xyz --dry-run

Returns JSON with:
  {
    "ok": true,
    "branch": "feature/ticket-001",
    "merged": ["root", "buildSrc", ...],
    "merge_conflicts": [],
    "already_on_main": [],
    "errors": [],
    "merge_commits": {"root": "abc123def", "buildSrc": "def456ghi", ...}
  }

Exit code: 0 on success, 1 on errors, 2 on merge conflicts.
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


def get_current_commit(repo_path: Path) -> str | None:
    """Get current HEAD commit hash."""
    result = git(["rev-parse", "HEAD"], cwd=str(repo_path), check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def merge_feature_branch(root_path: Path, branch: str, dry_run: bool = False) -> dict:
    """Merge feature branch into main in root and all submodules."""
    merged = []
    merge_conflicts = []
    already_on_main = []
    errors = []
    merge_commits = {}

    # Root repository
    if dry_run:
        merged.append("root")
    else:
        # Check current branch
        current = git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=str(root_path), check=False)
        if current.returncode == 0 and current.stdout.strip() == "main":
            already_on_main.append("root")
        else:
            # Checkout main
            checkout_result = git(["checkout", "main"], cwd=str(root_path), check=False)
            if checkout_result.returncode != 0:
                errors.append({"repo": "root", "error": f"Failed to checkout main: {checkout_result.stderr.strip()}"})
            else:
                # Merge branch with --no-ff for explicit merge commit
                merge_result = git(["merge", "--no-ff", "-m", f"Merge {branch} into main", branch],
                                   cwd=str(root_path), check=False)
                if merge_result.returncode != 0:
                    if "CONFLICT" in merge_result.stderr or "conflict" in merge_result.stdout:
                        merge_conflicts.append("root")
                        # Abort merge
                        git(["merge", "--abort"], cwd=str(root_path), check=False)
                    else:
                        errors.append({"repo": "root", "error": merge_result.stderr.strip()})
                else:
                    # Get merge commit hash
                    commit = get_current_commit(root_path)
                    if commit:
                        merge_commits["root"] = commit
                    # Push to remote
                    push_result = git(["push", "origin", "main"], cwd=str(root_path), check=False)
                    if push_result.returncode != 0:
                        errors.append({"repo": "root", "push_error": push_result.stderr.strip()})
                    else:
                        merged.append("root")

    # Submodules
    submodules = get_submodules(root_path)
    for submodule_path in submodules:
        submodule_full_path = root_path / submodule_path
        if not submodule_full_path.exists():
            continue

        if dry_run:
            merged.append(submodule_path)
        else:
            # Check current branch
            current = git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=str(submodule_full_path), check=False)
            if current.returncode == 0 and current.stdout.strip() == "main":
                already_on_main.append(submodule_path)
            else:
                # Checkout main
                checkout_result = git(["checkout", "main"], cwd=str(submodule_full_path), check=False)
                if checkout_result.returncode != 0:
                    errors.append({"repo": submodule_path, "error": f"Failed to checkout main: {checkout_result.stderr.strip()}"})
                else:
                    # Merge branch
                    merge_result = git(["merge", "--no-ff", "-m", f"Merge {branch} into main", branch],
                                       cwd=str(submodule_full_path), check=False)
                    if merge_result.returncode != 0:
                        if "CONFLICT" in merge_result.stderr or "conflict" in merge_result.stdout:
                            merge_conflicts.append(submodule_path)
                            git(["merge", "--abort"], cwd=str(submodule_full_path), check=False)
                        else:
                            errors.append({"repo": submodule_path, "error": merge_result.stderr.strip()})
                    else:
                        # Get merge commit hash
                        commit = get_current_commit(submodule_full_path)
                        if commit:
                            merge_commits[submodule_path] = commit
                        # Push to remote
                        push_result = git(["push", "origin", "main"], cwd=str(submodule_full_path), check=False)
                        if push_result.returncode != 0:
                            errors.append({"repo": submodule_path, "push_error": push_result.stderr.strip()})
                        else:
                            merged.append(submodule_path)

    # Update submodule pointers in parent (if root merged successfully)
    if "root" in merged and not merge_conflicts and not errors:
        # Stage all submodule pointer updates
        git(["add", "."], cwd=str(root_path), check=False)
        # Check if there are changes to commit
        status = git(["status", "--porcelain"], cwd=str(root_path), check=False)
        if status.stdout.strip():
            # Commit submodule pointer updates
            commit_result = git(["commit", "-m", "Update submodule pointers after merge"], cwd=str(root_path), check=False)
            if commit_result.returncode == 0:
                # Push parent
                git(["push", "origin", "main"], cwd=str(root_path), check=False)

    return {
        "ok": len(errors) == 0 and len(merge_conflicts) == 0,
        "branch": branch,
        "dry_run": dry_run,
        "merged": merged,
        "merge_conflicts": merge_conflicts if merge_conflicts else None,
        "already_on_main": already_on_main if already_on_main else None,
        "errors": errors if errors else None,
        "merge_commits": merge_commits if merge_commits else None
    }


def main():
    """Parse args and merge feature branch."""
    parser = argparse.ArgumentParser(description="Merge feature branch into main across root + submodules")
    parser.add_argument("--branch", required=True, help="Branch name to merge (e.g. feature/ticket-001)")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no changes)")
    args = parser.parse_args()

    # Find repo root (4 parents up from scripts/ to reach worktree root)
    script_dir = Path(__file__).resolve().parent
    root_path = script_dir.parent.parent.parent.parent

    if not (root_path / ".git").exists():
        print(json.dumps({"ok": False, "error": f"Not a git repo: {root_path}"}), file=sys.stderr)
        sys.exit(1)

    result = merge_feature_branch(root_path, args.branch, args.dry_run)
    print(json.dumps(result))

    # Exit code: 0 = success, 1 = errors, 2 = merge conflicts
    if result.get("merge_conflicts"):
        sys.exit(2)
    elif not result["ok"]:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
