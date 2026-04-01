#!/usr/bin/env python3
"""
create-feature-branch.py — Create and push a feature branch across root + all submodules.

Creates a new feature branch in the root repository and all submodules,
then pushes to remote. Useful for starting parallel feature development.

Usage:
  python create-feature-branch.py --branch feature/ticket-001
  python create-feature-branch.py --branch feature/xyz --dry-run

Returns JSON with:
  {
    "ok": true,
    "branch": "feature/ticket-001",
    "created": ["root", "buildSrc", "persistence", ...],
    "already_exist": [],
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


def create_feature_branch(root_path: Path, branch: str, dry_run: bool = False) -> dict:
    """Create feature branch in root and all submodules."""
    created = []
    already_exist = []
    errors = []

    # Root repository
    if dry_run:
        created.append("root")
    else:
        # Check if branch already exists locally
        check_result = git(["rev-parse", "--verify", branch], cwd=str(root_path), check=False)
        if check_result.returncode == 0:
            already_exist.append("root")
        else:
            # Create branch from main
            result = git(["checkout", "-b", branch], cwd=str(root_path), check=False)
            if result.returncode != 0:
                errors.append({"repo": "root", "error": result.stderr.strip()})
            else:
                # Push to remote
                push_result = git(["push", "-u", "origin", branch], cwd=str(root_path), check=False)
                if push_result.returncode != 0:
                    errors.append({"repo": "root", "push_error": push_result.stderr.strip()})
                    # Clean up local branch if push failed
                    git(["checkout", "main"], cwd=str(root_path), check=False)
                    git(["branch", "-D", branch], cwd=str(root_path), check=False)
                else:
                    created.append("root")

    # Submodules
    submodules = get_submodules(root_path)
    for submodule_path in submodules:
        submodule_full_path = root_path / submodule_path
        if not submodule_full_path.exists():
            continue

        if dry_run:
            created.append(submodule_path)
        else:
            # Check if branch already exists
            check_result = git(["rev-parse", "--verify", branch], cwd=str(submodule_full_path), check=False)
            if check_result.returncode == 0:
                already_exist.append(submodule_path)
            else:
                # Create and push branch
                result = git(["checkout", "-b", branch], cwd=str(submodule_full_path), check=False)
                if result.returncode != 0:
                    errors.append({"repo": submodule_path, "error": result.stderr.strip()})
                else:
                    push_result = git(["push", "-u", "origin", branch], cwd=str(submodule_full_path), check=False)
                    if push_result.returncode != 0:
                        errors.append({"repo": submodule_path, "push_error": push_result.stderr.strip()})
                        git(["checkout", "main"], cwd=str(submodule_full_path), check=False)
                        git(["branch", "-D", branch], cwd=str(submodule_full_path), check=False)
                    else:
                        created.append(submodule_path)

    return {
        "ok": len(errors) == 0,
        "branch": branch,
        "dry_run": dry_run,
        "created": created,
        "already_exist": already_exist,
        "errors": errors if errors else None
    }


def main():
    """Parse args and create feature branch."""
    parser = argparse.ArgumentParser(description="Create feature branch across root + submodules")
    parser.add_argument("--branch", required=True, help="Branch name (e.g. feature/ticket-001)")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no changes)")
    args = parser.parse_args()

    # Find repo root (script is at <root>/skills/multi_agent_ide_skills/multi_agent_ide_deploy/scripts/)
    # In worktree: /worktrees/ID/skills/multi_agent_ide_skills/multi_agent_ide_deploy/scripts
    # Need to go up 4 levels to reach /worktrees/ID
    script_dir = Path(__file__).resolve().parent
    root_path = script_dir.parent.parent.parent.parent

    if not (root_path / ".git").exists():
        print(json.dumps({"ok": False, "error": f"Not a git repo: {root_path}"}), file=sys.stderr)
        sys.exit(1)

    result = create_feature_branch(root_path, args.branch, args.dry_run)
    print(json.dumps(result))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
