#!/usr/bin/env python3
"""Skill script: two-phase fan-out orchestration.

Phase 1: Detect view directories, launch one query_view.py subprocess per view in parallel.
Phase 2: Launch query_root.py for synthesis.
Returns consolidated JSON.

Usage:
    python fan_out.py --repo /path/to/repo --model <model> --timeout 120 "query"
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
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
    model: str,
    query: str,
    timeout: int,
) -> dict:
    """Run query_view.py for a single view and return parsed JSON."""
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "query_view.py"),
        "--repo", repo,
        "--view", view_name,
        "--model", model,
        "--timeout", str(timeout),
        query,
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout + 30,
        )
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
    except subprocess.TimeoutExpired:
        return {
            "view_name": view_name,
            "mode": "view",
            "query": query,
            "response": "",
            "mental_model_updated": False,
            "error": f"Timeout after {timeout}s",
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


def _run_root_query(repo: str, model: str, query: str, timeout: int) -> dict:
    """Run query_root.py and return parsed JSON."""
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "query_root.py"),
        "--repo", repo,
        "--model", model,
        "--timeout", str(timeout),
        query,
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout + 30,
        )
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
    except subprocess.TimeoutExpired:
        return {
            "view_name": "root",
            "mode": "root",
            "query": query,
            "response": "",
            "mental_model_updated": False,
            "error": f"Timeout after {timeout}s",
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
    parser = argparse.ArgumentParser(description="Two-phase fan-out orchestration")
    parser.add_argument("query", help="The query to process")
    parser.add_argument("--repo", required=True, help="Path to the repository")
    parser.add_argument("--model", required=True, help="Ollama model name")
    parser.add_argument("--timeout", type=int, default=120, help="Per-view timeout")
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
                _run_view_query, args.repo, v, args.model, args.query, args.timeout,
            ): v
            for v in views
        }
        for future in as_completed(futures):
            view_results.append(future.result())

    # Sort by view name for deterministic output
    view_results.sort(key=lambda r: r.get("view_name", ""))

    # Phase 2: Root synthesis
    root_result = _run_root_query(args.repo, args.model, args.query, args.timeout)

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
