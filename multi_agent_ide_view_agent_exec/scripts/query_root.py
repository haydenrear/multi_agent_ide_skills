#!/usr/bin/env python3
"""Skill script: run root-mode cross-view synthesis via uv + ACP.

Resolves the uv workspace automatically and runs the view-agent CLI
in root mode.

Usage:
    python query_root.py --repo /path/to/repo "query"
    python query_root.py --repo /path/to/repo --artifact-key ak:01KJ... "query"
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Root-mode cross-view synthesis via ACP")
    parser.add_argument("query", help="The query to process")
    parser.add_argument("--repo", required=True, help="Path to the repository")
    parser.add_argument("--artifact-key", default=None,
                        help="Parent artifact key for tracing")
    parser.add_argument("--permission-fifo-dir", default=None,
                        help="Directory with permission FIFOs for interactive approval. "
                             "Launch this script as a background process and poll the FIFO asynchronously.")
    parser.add_argument("--view-responses-file", default=None,
                        help="JSON file with per-view responses from Phase 1")
    parser.add_argument("--conversation-fifo-dir", default=None,
                        help="Directory with conversation FIFOs for multi-turn control. "
                             "Launch this script as a background process and poll the FIFO asynchronously.")
    parser.add_argument("--model", default="claude-haiku-4-5",
                        help="Model for the ACP session (default: claude-haiku-4-5)")
    args = parser.parse_args()

    uv_project = _find_uv_project()
    views_path = f"{args.repo}/views"

    cmd = [
        "uv", "run", "--project", str(uv_project),
        "view-agent", "query",
        "--view", views_path,
        "--mode", "root",
        "--repo", args.repo,
    ]
    if args.artifact_key:
        cmd.extend(["--artifact-key", args.artifact_key])
    if args.permission_fifo_dir:
        cmd.extend(["--permission-fifo-dir", args.permission_fifo_dir])
    if args.view_responses_file:
        cmd.extend(["--view-responses-file", args.view_responses_file])
    if args.conversation_fifo_dir:
        cmd.extend(["--conversation-fifo-dir", args.conversation_fifo_dir])
    cmd.extend(["--model", args.model])
    cmd.append(args.query)

    sys.exit(subprocess.run(cmd).returncode)


if __name__ == "__main__":
    main()
