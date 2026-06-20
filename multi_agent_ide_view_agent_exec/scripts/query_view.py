#!/usr/bin/env python3
"""Skill script: query a single view via uv + ACP.

Resolves the uv workspace automatically and runs the view-agent CLI.

Usage:
    python query_view.py --repo /path/to/repo --view <view-name> "query"
    python query_view.py --repo /path/to/repo --view api-layer --artifact-key ak:01KJ... "query"
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _find_uv_project() -> Path:
    """Find the view_agent_exec package for uv run.

    The view-agent entry point is defined in view_agent_exec's pyproject.toml,
    not the workspace root — uv must target the package directly.
    """
    script_dir = Path(__file__).resolve().parent
    candidates = [
        script_dir.parent.parent.parent.parent / "multi_agent_ide_python_parent" / "packages" / "view_agent_exec",
        Path.cwd() / "multi_agent_ide_python_parent" / "packages" / "view_agent_exec",
    ]
    for candidate in candidates:
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise FileNotFoundError(
        "Cannot find view_agent_exec package. "
        "Expected at multi_agent_ide_python_parent/packages/view_agent_exec/"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Query a single view via ACP")
    parser.add_argument("query", help="The query to process")
    parser.add_argument("--repo", required=True, help="Path to the repository")
    parser.add_argument("--view", required=True, help="View name (e.g. api-layer)")
    parser.add_argument("--artifact-key", default=None,
                        help="Parent artifact key for tracing")
    parser.add_argument("--permission-fifo-dir", default=None,
                        help="Directory with permission FIFOs for interactive approval. "
                             "Launch this script as a background process and poll the FIFO asynchronously.")
    parser.add_argument("--conversation-fifo-dir", default=None,
                        help="Directory with conversation FIFOs for multi-turn control. "
                             "Launch this script as a background process and poll the FIFO asynchronously.")
    parser.add_argument("--model", default="claude-haiku-4-5",
                        help="Model for the ACP session (default: claude-haiku-4-5)")
    args = parser.parse_args()

    uv_project = _find_uv_project()
    view_path = f"{args.repo}/views/{args.view}"

    cmd = [
        "uv", "run", "--project", str(uv_project),
        "view-agent", "query",
        "--view", view_path,
        "--repo", args.repo,
    ]
    if args.artifact_key:
        cmd.extend(["--artifact-key", args.artifact_key])
    if args.permission_fifo_dir:
        cmd.extend(["--permission-fifo-dir", args.permission_fifo_dir])
    if args.conversation_fifo_dir:
        cmd.extend(["--conversation-fifo-dir", args.conversation_fifo_dir])
    cmd.extend(["--model", args.model])
    cmd.append(args.query)

    sys.exit(subprocess.run(cmd).returncode)


if __name__ == "__main__":
    main()
