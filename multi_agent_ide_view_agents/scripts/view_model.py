#!/usr/bin/env python3
"""Skill script: run view-model subcommands via uv with auto --repo resolution.

Resolves the repository root automatically from the mental model path,
injects --repo, and runs the CLI via uv from the Python parent workspace.

Usage:
    python view_model.py <subcommand> <path> [options...]
    python view_model.py update <path> --path '$.sections["Foo"]' --value-file /tmp/c.txt --package foo
    python view_model.py add-ref <path> --path '$.sections["Foo"]' --file path/to/File.java
    python view_model.py render <path> --write
    python view_model.py status <path>
    python view_model.py files <path>
    python view_model.py init <path>
    python view_model.py delete <path> --path '$.sections["Old"]'

All commands auto-resolve --repo from the path argument if not explicitly provided.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _resolve_repo_root(mental_model_path: str) -> Path:
    """Derive the repository root from the mental model path.

    Walks up from the given path looking for a 'views' directory,
    then returns its parent as the repo root.
    """
    p = Path(mental_model_path).resolve()
    current = p if p.is_dir() else p.parent
    while current != current.parent:
        if current.name == "views":
            return current.parent
        current = current.parent
    raise ValueError(f"Cannot determine repo root from path: {mental_model_path}")


def _find_uv_project() -> Path:
    """Find the view_agents_utils package for uv run.

    The view-model entry point is defined in view_agents_utils's pyproject.toml,
    not the workspace root — uv must target the package directly.
    """
    script_dir = Path(__file__).resolve().parent
    candidates = [
        script_dir.parent.parent.parent.parent / "multi_agent_ide_python_parent" / "packages" / "view_agents_utils",
        Path.cwd() / "multi_agent_ide_python_parent" / "packages" / "view_agents_utils",
    ]
    for candidate in candidates:
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise FileNotFoundError(
        "Cannot find view_agents_utils package. "
        "Expected at multi_agent_ide_python_parent/packages/view_agents_utils/"
    )


def run_view_model(subcommand: str, path: str, extra_args: list[str]) -> int:
    """Run a view-model subcommand with auto --repo resolution.

    Injects --repo automatically if not already present in extra_args.
    """
    repo_root = _resolve_repo_root(path)
    uv_project = _find_uv_project()

    # Auto-inject --repo if not explicitly provided
    if "--repo" not in extra_args:
        extra_args = ["--repo", str(repo_root)] + extra_args

    cmd = [
        "uv", "run", "--project", str(uv_project),
        "view-model", subcommand, path,
        *extra_args,
    ]
    result = subprocess.run(cmd)
    return result.returncode


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "Usage: view_model.py <subcommand> <path> [options...]\n"
            "\n"
            "Subcommands: init, update, delete, add-ref, add-ref-root, render, files, status\n"
            "\n"
            "The --repo flag is auto-resolved from the path argument.",
            file=sys.stderr,
        )
        sys.exit(1)

    subcommand = sys.argv[1]
    path = sys.argv[2]
    extra_args = sys.argv[3:]

    sys.exit(run_view_model(subcommand, path, extra_args))


if __name__ == "__main__":
    main()
