#!/usr/bin/env python3
"""Skill script: run view-custody search via uv with auto --repo resolution.

Resolves the repository root automatically from the mental model path,
and runs view-custody search via uv from the Python parent workspace.

Usage:
    python search_custody.py <path> [options...]
    python search_custody.py views/my-view --path '$.sections["Foo"]'
    python search_custody.py views/my-view --file path/to/File.java
    python search_custody.py views/my-view --date-range '2026-01-01..2026-04-01'
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _resolve_repo_root(mental_model_path: str) -> Path:
    """Derive the repository root from the mental model path."""
    p = Path(mental_model_path).resolve()
    current = p if p.is_dir() else p.parent
    while current != current.parent:
        if current.name == "views":
            return current.parent
        current = current.parent
    raise ValueError(f"Cannot determine repo root from path: {mental_model_path}")


def _find_uv_project() -> Path:
    """Find the multi_agent_ide_python_parent workspace for uv run."""
    script_dir = Path(__file__).resolve().parent
    candidates = [
        script_dir.parent.parent.parent.parent / "multi_agent_ide_python_parent",
        Path.cwd() / "multi_agent_ide_python_parent",
    ]
    for candidate in candidates:
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise FileNotFoundError(
        "Cannot find multi_agent_ide_python_parent workspace. "
        "Run from the repo root or set UV_PROJECT env var."
    )


def run_search(path: str, extra_args: list[str]) -> int:
    """Run view-custody search with auto --repo resolution."""
    uv_project = _find_uv_project()

    cmd = [
        "uv", "run", "--project", str(uv_project),
        "view-custody", "search", path,
        *extra_args,
    ]
    result = subprocess.run(cmd)
    return result.returncode


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: search_custody.py <path> [options...]\n"
            "\n"
            "Options: --path, --file, --child-view, --child-path,\n"
            "         --hash-range, --date-range, --max-depth, --format",
            file=sys.stderr,
        )
        sys.exit(1)

    path = sys.argv[1]
    extra_args = sys.argv[2:]

    sys.exit(run_search(path, extra_args))


if __name__ == "__main__":
    main()
