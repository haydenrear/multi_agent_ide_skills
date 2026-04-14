#!/usr/bin/env python3
"""Skill script: query a single view via uv or Docker fallback.

If the uv workspace exists at /home/python_parent/sources (i.e. we are inside
a container that was built with ``uv sync``), run the CLI via ``uv run``.
Otherwise fall back to launching a Docker container.

Usage:
    python query_view.py --repo /path/to/repo --view <view-name> --model <model> "query"
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

DOCKER_IMAGE = "localhost:5001/view-agent-exec"
CONTAINER_REPO = "/repo"
UV_PROJECT = Path("/home/python_parent/sources")


def _run_uv(args: argparse.Namespace) -> int:
    """Run view-agent query via uv from the synced workspace."""
    view_path = f"{args.repo}/views/{args.view}"
    cmd = [
        "uv", "run", "--project", str(UV_PROJECT),
        "view-agent", "query",
        "--view", view_path,
        "--model", args.model,
        "--timeout", str(args.timeout),
        "--repo", args.repo,
        args.query,
    ]
    return subprocess.run(cmd).returncode


def _run_docker(args: argparse.Namespace) -> int:
    """Run view-agent query inside the Docker container."""
    view_path = f"{CONTAINER_REPO}/views/{args.view}"
    mm_dir = f"{args.repo}/views/{args.view}/mental-models"
    container_mm_dir = f"{CONTAINER_REPO}/views/{args.view}/mental-models"

    docker_cmd = [
        "docker", "run", "--rm",
        "-v", f"{args.repo}:{CONTAINER_REPO}:ro",
        "-v", f"{mm_dir}:{container_mm_dir}:rw",
        "-v", "/var/run/docker.sock:/var/run/docker.sock",
        DOCKER_IMAGE,
        "query",
        "--view", view_path,
        "--model", args.model,
        "--timeout", str(args.timeout),
        "--repo", CONTAINER_REPO,
        args.query,
    ]

    return subprocess.run(docker_cmd).returncode


def main() -> None:
    parser = argparse.ArgumentParser(description="Query a single view via Docker")
    parser.add_argument("query", help="The query to process")
    parser.add_argument("--repo", required=True, help="Path to the repository")
    parser.add_argument("--view", required=True, help="View name (e.g. api-module)")
    parser.add_argument("--model", required=True, help="Ollama model name")
    parser.add_argument("--timeout", type=int, default=120, help="Query timeout")
    args = parser.parse_args()

    if UV_PROJECT.exists():
        sys.exit(_run_uv(args))
    else:
        sys.exit(_run_docker(args))


if __name__ == "__main__":
    main()
