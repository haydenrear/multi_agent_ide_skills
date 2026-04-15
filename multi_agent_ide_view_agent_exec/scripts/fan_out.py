#!/usr/bin/env python3
"""Skill script: two-phase fan-out orchestration via ACP.

Phase 1: Detect view directories, launch one query_view.py subprocess per view in parallel.
Phase 2: Launch query_root.py for synthesis.
Returns consolidated JSON.

Usage:
    python fan_out.py --repo /path/to/repo "query"
    python fan_out.py --repo /path/to/repo --artifact-key ak:01KJ... "query"
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent


def _discover_views(repo: str) -> list[str]:
    """Discover view directories under views/."""
    views_dir = Path(repo) / "views"
    if not views_dir.exists():
        return []
    views = []
    for d in sorted(views_dir.iterdir()):
        if d.is_dir() and d.name != "mental-models" and (d / "regen.py").exists():
            views.append(d.name)
    return views


def _run_view_query(
    repo: str,
    view_name: str,
    artifact_key: str | None,
    query: str,
    permission_fifo_dir: str | None = None,
    conversation_fifo_dir: str | None = None,
    model: str = "claude-haiku-4-5",
) -> dict:
    """Run query_view.py for a single view and return parsed JSON."""
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "query_view.py"),
        "--repo", repo,
        "--view", view_name,
    ]
    if artifact_key:
        cmd.extend(["--artifact-key", artifact_key])
    if permission_fifo_dir:
        cmd.extend(["--permission-fifo-dir", permission_fifo_dir])
    if conversation_fifo_dir:
        cmd.extend(["--conversation-fifo-dir", conversation_fifo_dir])
    cmd.extend(["--model", model])
    cmd.append(query)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        return {
            "view_name": view_name,
            "mode": "view",
            "query": query,
            "response": "",
            "mental_model_updated": False,
            "error": result.stderr.strip() or f"Exit code {result.returncode}",
        }
    except Exception as e:
        return {
            "view_name": view_name,
            "mode": "view",
            "query": query,
            "response": "",
            "mental_model_updated": False,
            "error": str(e),
        }


def _run_root_query(
    repo: str,
    artifact_key: str | None,
    query: str,
    permission_fifo_dir: str | None = None,
    view_responses_file: str | None = None,
    conversation_fifo_dir: str | None = None,
    model: str = "claude-haiku-4-5",
) -> dict:
    """Run query_root.py and return parsed JSON."""
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "query_root.py"),
        "--repo", repo,
    ]
    if artifact_key:
        cmd.extend(["--artifact-key", artifact_key])
    if permission_fifo_dir:
        cmd.extend(["--permission-fifo-dir", permission_fifo_dir])
    if view_responses_file:
        cmd.extend(["--view-responses-file", view_responses_file])
    if conversation_fifo_dir:
        cmd.extend(["--conversation-fifo-dir", conversation_fifo_dir])
    cmd.extend(["--model", model])
    cmd.append(query)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        return {
            "view_name": "root",
            "mode": "root",
            "query": query,
            "response": "",
            "mental_model_updated": False,
            "error": result.stderr.strip() or f"Exit code {result.returncode}",
        }
    except Exception as e:
        return {
            "view_name": "root",
            "mode": "root",
            "query": query,
            "response": "",
            "mental_model_updated": False,
            "error": str(e),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Two-phase fan-out orchestration via ACP")
    parser.add_argument("query", help="The query to process")
    parser.add_argument("--repo", required=True, help="Path to the repository")
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

    views = _discover_views(args.repo)

    if not views:
        print(json.dumps({
            "phase_1_views": [],
            "phase_2_root": None,
            "error": "No views found",
        }, indent=2))
        sys.exit(0)

    # Phase 1: Parallel per-view queries
    view_results = []
    with ThreadPoolExecutor(max_workers=len(views)) as executor:
        futures = {
            executor.submit(
                _run_view_query,
                args.repo, v,
                args.artifact_key, args.query,
                args.permission_fifo_dir,
                args.conversation_fifo_dir,
                args.model,
            ): v
            for v in views
        }
        for future in as_completed(futures):
            view_results.append(future.result())

    # Sort by view name for deterministic output
    view_results.sort(key=lambda r: r.get("view_name", ""))

    # Phase 2: Root synthesis — pass Phase 1 results via temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", prefix="view-responses-", delete=False,
    ) as tmp:
        json.dump(view_results, tmp, indent=2)
        tmp_path = tmp.name

    try:
        root_result = _run_root_query(
            args.repo,
            args.artifact_key, args.query,
            args.permission_fifo_dir,
            view_responses_file=tmp_path,
            conversation_fifo_dir=args.conversation_fifo_dir,
            model=args.model,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    # Consolidated output
    output = {
        "phase_1_views": view_results,
        "phase_2_root": root_result,
        "views_queried": len(views),
        "views_succeeded": sum(1 for r in view_results if r.get("error") is None),
        "views_failed": sum(1 for r in view_results if r.get("error") is not None),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
