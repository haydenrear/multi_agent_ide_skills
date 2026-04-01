#!/usr/bin/env python3
"""
merge-from-worktree.py — Merge worktree changes into tmp repo with conflict-aware handling.

Accepts --worktree-path (from GoalCompletedEvent.worktreePath) and merges the
worktree-derived branch into the tmp repo current branch. For each submodule:
  1. Fetch from worktree submodule remote
  2. Merge into current branch
  3. Report conflicts but continue merging non-conflicting submodules
  4. Push submodules innermost-first, then root

Usage:
  python merge-from-worktree.py --worktree-path /path/to/worktree [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent))

from _result import failure, success

# ── constants ─────────────────────────────────────────────────────────────────

TMP_BASE = Path("/private/tmp/multi_agent_ide_parent")
TMP_REPO_FILE = TMP_BASE / "tmp_repo.txt"


# ── helpers ───────────────────────────────────────────────────────────────────

def run(cmd: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check)


def git(args: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return run(["git"] + args, cwd=cwd, check=check)


def read_tmp_repo() -> Path | None:
    """Read tmp repo path from tmp_repo.txt"""
    if not TMP_REPO_FILE.exists():
        return None
    path_str = TMP_REPO_FILE.read_text().strip()
    if not path_str:
        return None
    p = Path(path_str)
    return p if p.exists() and (p / ".git").exists() else None


def get_submodules(repo_path: Path) -> list[str]:
    """Get list of all submodules in order (for innermost-to-outermost processing)"""
    r = run(["git", "submodule", "foreach", "--recursive", "--quiet", "echo $displaypath"],
            cwd=str(repo_path), check=False)
    if r.returncode != 0:
        return []
    submodules = [p.strip() for p in r.stdout.splitlines() if p.strip()]
    # Sort by depth (deepest first) for innermost-to-outermost ordering
    return sorted(submodules, key=lambda p: p.count('/'), reverse=True)


def get_current_branch(cwd: str) -> str | None:
    """Get current branch name, or None if detached"""
    r = run(["git", "symbolic-ref", "--short", "HEAD"], cwd=cwd, check=False)
    return r.stdout.strip() if r.returncode == 0 else None


def merge_and_check_conflicts(worktree_path: Path, repo_path: Path, dry_run: bool) -> dict:
    """
    Merge worktree branch into tmp repo with conflict detection.
    Returns dict with ok status, conflicts list, and merge results.
    """
    results = {
        "merged": [],
        "conflicts": [],
        "errors": [],
    }

    tmp_cwd = str(repo_path)
    current_branch = get_current_branch(tmp_cwd)

    # Get worktree branch name
    worktree_branch = get_current_branch(str(worktree_path))
    if not worktree_branch:
        results["errors"].append("Worktree is in detached HEAD state")
        return results

    if not current_branch:
        results["errors"].append("Tmp repo is in detached HEAD state")
        return results

    # First, merge root repo itself
    if not dry_run:
        fetch_result = git(
            ["fetch", str(worktree_path), worktree_branch],
            cwd=tmp_cwd,
            check=False
        )

        if fetch_result.returncode != 0:
            results["errors"].append(f"root: fetch failed: {fetch_result.stderr.strip()}")
        else:
            merge_result = git(
                ["merge", "--no-commit", "FETCH_HEAD"],
                cwd=tmp_cwd,
                check=False
            )

            if merge_result.returncode != 0:
                status_result = git(["status", "--porcelain"], cwd=tmp_cwd, check=False)
                if "UU" in status_result.stdout or "AA" in status_result.stdout:
                    results["conflicts"].append("root: merge conflict detected")
                    git(["merge", "--abort"], cwd=tmp_cwd, check=False)
                else:
                    results["errors"].append(f"root: merge failed: {merge_result.stderr.strip()}")
                    git(["merge", "--abort"], cwd=tmp_cwd, check=False)
            else:
                commit_result = git(
                    ["commit", "-m", f"Merge worktree branch {worktree_branch}"],
                    cwd=tmp_cwd,
                    check=False
                )
                if commit_result.returncode == 0:
                    results["merged"].append("root: merged successfully")
                else:
                    results["merged"].append("root: merge committed (already up-to-date or fast-forward)")
    else:
        results["merged"].append("root: [DRY-RUN] would fetch from worktree and merge")

    # Process all submodules
    submodules = get_submodules(repo_path)

    for sub in submodules:
        sub_tmp_path = repo_path / sub
        sub_worktree_path = worktree_path / sub

        if not sub_tmp_path.exists() or not sub_worktree_path.exists():
            results["errors"].append(f"{sub}: paths do not exist in both repos")
            continue

        if dry_run:
            results["merged"].append(f"{sub}: [DRY-RUN] would fetch from {sub_worktree_path} and merge")
            continue

        # Add worktree remote and fetch
        sub_tmp_cwd = str(sub_tmp_path)
        fetch_result = git(
            ["fetch", str(sub_worktree_path), worktree_branch],
            cwd=sub_tmp_cwd,
            check=False
        )

        if fetch_result.returncode != 0:
            results["errors"].append(f"{sub}: fetch failed: {fetch_result.stderr.strip()}")
            continue

        # Attempt merge (continue on conflicts)
        merge_result = git(
            ["merge", "--no-commit", "FETCH_HEAD"],
            cwd=sub_tmp_cwd,
            check=False
        )

        if merge_result.returncode != 0:
            # Check if it's a conflict
            status_result = git(["status", "--porcelain"], cwd=sub_tmp_cwd, check=False)
            if "UU" in status_result.stdout or "AA" in status_result.stdout:
                # Merge conflict detected
                results["conflicts"].append(f"{sub}: merge conflict detected")
                # Abort the merge to leave repo clean
                git(["merge", "--abort"], cwd=sub_tmp_cwd, check=False)
            else:
                results["errors"].append(f"{sub}: merge failed: {merge_result.stderr.strip()}")
                git(["merge", "--abort"], cwd=sub_tmp_cwd, check=False)
        else:
            # Merge succeeded, commit it
            commit_result = git(
                ["commit", "-m", f"Merge worktree branch {worktree_branch}"],
                cwd=sub_tmp_cwd,
                check=False
            )
            if commit_result.returncode == 0:
                results["merged"].append(f"{sub}: merged successfully")
            else:
                results["merged"].append(f"{sub}: merge committed (already up-to-date or fast-forward)")

    return results


def push_innermost_first(repo_path: Path, dry_run: bool) -> dict:
    """
    Push all changes in innermost-to-outermost order.
    Returns dict with push results.
    """
    results = {
        "pushed": [],
        "errors": [],
    }

    # Get submodules in innermost-to-outermost order
    submodules = get_submodules(repo_path)

    # Push submodules first (innermost to outermost)
    for sub in submodules:
        sub_path = repo_path / sub
        if not sub_path.exists():
            continue

        sub_cwd = str(sub_path)
        branch = get_current_branch(sub_cwd)

        if not branch:
            results["errors"].append(f"{sub}: detached HEAD, skipping push")
            continue

        if dry_run:
            results["pushed"].append(f"{sub}: [DRY-RUN] would push to origin {branch}")
            continue

        push_result = git(
            ["push", "origin", branch],
            cwd=sub_cwd,
            check=False
        )

        if push_result.returncode != 0:
            results["errors"].append(f"{sub}: push failed: {push_result.stderr.strip()}")
        else:
            results["pushed"].append(f"{sub}: pushed")

    # Push root last
    root_cwd = str(repo_path)
    root_branch = get_current_branch(root_cwd)

    if root_branch:
        if dry_run:
            results["pushed"].append(f"root: [DRY-RUN] would push to origin {root_branch}")
        else:
            push_result = git(
                ["push", "origin", root_branch],
                cwd=root_cwd,
                check=False
            )

            if push_result.returncode != 0:
                results["errors"].append(f"root: push failed: {push_result.stderr.strip()}")
            else:
                results["pushed"].append("root: pushed")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Merge worktree changes into tmp repo with conflict-aware handling"
    )
    parser.add_argument(
        "--worktree-path",
        required=True,
        help="Path to the worktree containing the merged changes"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview merge sequence without executing git commands"
    )

    args = parser.parse_args()

    # Validate worktree path
    worktree_path = Path(args.worktree_path)
    if not worktree_path.exists() or not (worktree_path / ".git").exists():
        return failure(f"Invalid worktree path: {args.worktree_path}")

    # Read tmp repo path
    tmp_repo = read_tmp_repo()
    if not tmp_repo:
        return failure("Cannot read tmp repo path from /private/tmp/multi_agent_ide_parent/tmp_repo.txt")

    # Merge and check conflicts
    merge_results = merge_and_check_conflicts(worktree_path, tmp_repo, args.dry_run)

    # If there are conflicts, report them but continue
    has_conflicts = len(merge_results["conflicts"]) > 0
    has_errors = len(merge_results["errors"]) > 0

    if args.dry_run:
        # In dry-run mode, just return the merge plan
        data = {
            "worktree_path": str(worktree_path),
            "tmp_repo_path": str(tmp_repo),
            "dry_run": True,
            "merge_plan": merge_results,
        }
        return success(data)

    # If there are errors, return failure but include all results (merged, errors, conflicts)
    if has_errors:
        return failure({
            "worktree_path": str(worktree_path),
            "tmp_repo_path": str(tmp_repo),
            "merge": merge_results,
        })

    # Push successfully-merged submodules (conflicting ones were aborted, so won't push stale state)
    push_results = push_innermost_first(tmp_repo, args.dry_run)

    data = {
        "worktree_path": str(worktree_path),
        "tmp_repo_path": str(tmp_repo),
        "merge": merge_results,
        "push": push_results,
    }

    if has_conflicts:
        data["status"] = "merged_with_conflicts"

    # Fail if push had errors, otherwise success (even with merge conflicts — they were reported and aborted)
    if push_results["errors"]:
        return failure(data)

    return success(data)


if __name__ == "__main__":
    sys.exit(main())
