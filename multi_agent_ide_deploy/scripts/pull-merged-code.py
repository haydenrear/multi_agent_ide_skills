#!/usr/bin/env python3
"""
pull-merged-code.py — Pull main branch after merge across root and all submodules.

Pulls the main branch after a merge is complete across the root repository and
all submodules. Implements innermost-to-outermost processing order to ensure
consistent state after merge completion.

Usage:
  python pull-merged-code.py

Example:
  python pull-merged-code.py
"""
from __future__ import annotations

import argparse
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


def pull_main_in_repo(cwd: str) -> tuple[bool, str | None]:
    """
    Pull main branch in a single repo.
    Returns (success: bool, error_msg: str | None)
    """
    # Switch to main branch
    r = git(["switch", "main"], cwd=cwd, check=False)
    if r.returncode != 0:
        return False, f"Failed to switch to main branch: {r.stderr.strip()}"

    # Pull main branch
    r = git(["pull", "origin", "main"], cwd=cwd, check=False)
    if r.returncode != 0:
        return False, f"Failed to pull main branch: {r.stderr.strip()}"

    return True, None


def pull_main_in_submodules(repo_path: str) -> dict:
    """
    Pull main branch in all submodules in innermost-to-outermost order.
    Returns dict with 'pulled' and 'failed' lists.
    """
    pulled = []
    failed = []

    # Get all submodules
    submodules = get_submodules(repo_path)
    if not submodules:
        return {"pulled": [], "failed": []}

    # Order submodules innermost-first (deepest nested first)
    submodules = order_submodules_innermost_first(submodules)

    # Process each submodule
    for submodule_path in submodules:
        sub_cwd = str(Path(repo_path) / submodule_path)
        success_flag, error = pull_main_in_repo(sub_cwd)

        if success_flag:
            pulled.append(submodule_path)
        else:
            failed.append({"path": submodule_path, "error": error})

    return {"pulled": pulled, "failed": failed}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pull main branch after merge across root and all submodules"
    )

    args = parser.parse_args()

    # Get current working directory (root repo)
    repo_path = str(Path.cwd())

    # Verify it's a git repo
    r = git(["rev-parse", "--git-dir"], cwd=repo_path, check=False)
    if r.returncode != 0:
        return failure("Current directory is not a git repository")

    # Pull main in root repository
    success_flag, error = pull_main_in_repo(repo_path)
    if not success_flag:
        return failure(error)

    # Pull main in all submodules (innermost-to-outermost order)
    submodule_results = pull_main_in_submodules(repo_path)

    # Build output
    output = {
        "branch": "main",
        "root_pulled": True,
        "submodules_pulled": submodule_results["pulled"],
    }

    if submodule_results["failed"]:
        output["submodule_errors"] = submodule_results["failed"]
        # If any submodules failed, report overall failure but include partial results
        return failure(output)

    return success(output)


if __name__ == "__main__":
    sys.exit(main())
