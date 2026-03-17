#!/usr/bin/env python3
"""
search_log.py — Structured log search for multi_agent_ide runtime and build logs.

Wraps the common grep patterns used during controller and debug sessions so they
never need to be re-derived as inline commands.

Usage:
    python search_log.py errors            # recent errors/exceptions (default: last 50 matches)
    python search_log.py node ak:01KK...   # events for a specific nodeId
    python search_log.py goal              # goal/node completion events
    python search_log.py permission        # permission/interrupt events
    python search_log.py propagation       # propagation events (incl. overflow errors)
    python search_log.py acp               # ACP/LLM call failures (reads acp-errs log)
    python search_log.py overflow          # DB column overflow errors
    python search_log.py <pattern>         # arbitrary case-insensitive grep pattern

Flags:
    --log <path>        Override the default log path
    --limit N           Max lines to show (default 50)
    --project-root <p>  Override project root (default: reads from tmp_repo.txt)
    --build             Search the Gradle build log instead of the runtime log
    --follow            Tail the log live (Ctrl-C to stop; ignores --limit)
"""
import argparse
import os
import subprocess
import sys

TMP_REPO_FILE = "/private/tmp/multi_agent_ide_parent/tmp_repo.txt"

RUNTIME_LOG = "multi-agent-ide.log"
BUILD_LOG = "build-log.log"
ACP_LOG = "multi_agent_ide_java_parent/multi_agent_ide/claude-agent-acp-errs.log"

PRESETS = {
    "errors":      r"ERROR|Exception|failed|FAILED",
    "goal":        r"GOAL_COMPLETED|NODE_COMPLETED|NODE_ERROR|goal.*complet",
    "permission":  r"PERMISSION_REQUESTED|INTERRUPT_REQUESTED|NODE_REVIEW|resolv.*permission",
    "propagation": r"Propagation|PROPAGATION|prop-event|prop-item",
    "overflow":    r"value too long|character varying|DataIntegrityViolationException|summaryText|propagated_text",
    "acp":         r"ERROR|failed|timeout|credit|rate.limit",
}


def resolve_project_root(args):
    if args.project_root:
        return args.project_root
    try:
        with open(TMP_REPO_FILE) as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def resolve_log_path(args, project_root):
    if args.log:
        return args.log
    if args.build:
        if project_root:
            return os.path.join(project_root, BUILD_LOG)
        return BUILD_LOG
    if project_root:
        return os.path.join(project_root, RUNTIME_LOG)
    return RUNTIME_LOG


def grep_log(pattern, log_path, limit, case_insensitive=True):
    flags = ["-n"]
    if case_insensitive:
        flags.append("-i")
    result = subprocess.run(
        ["grep"] + flags + ["-E", pattern, log_path],
        capture_output=True, text=True
    )
    lines = [l for l in result.stdout.strip().split("\n") if l]
    if not lines:
        print(f"(no matches for pattern: {pattern!r})")
        return
    shown = lines[-limit:]
    omitted = len(lines) - len(shown)
    if omitted > 0:
        print(f"... ({omitted} earlier matches omitted, showing last {limit})")
    for line in shown:
        print(line)
    print(f"\n{len(lines)} total match(es).")


def tail_log(log_path):
    try:
        subprocess.run(["tail", "-f", log_path])
    except KeyboardInterrupt:
        pass


def main():
    parser = argparse.ArgumentParser(description="Search multi_agent_ide logs")
    parser.add_argument("query", nargs="?", default="errors",
                        help="Preset name or grep pattern (default: errors)")
    parser.add_argument("node_id", nargs="?", default=None,
                        help="NodeId for 'node' preset")
    parser.add_argument("--log", help="Explicit log file path")
    parser.add_argument("--limit", type=int, default=50, help="Max lines to show")
    parser.add_argument("--project-root", help="Override project root")
    parser.add_argument("--build", action="store_true", help="Search build log")
    parser.add_argument("--follow", action="store_true", help="Tail log live")
    args = parser.parse_args()

    project_root = resolve_project_root(args)
    if not project_root:
        print("WARNING: could not resolve project root — using current directory", file=sys.stderr)
        project_root = "."

    # Determine log path and pattern
    query = args.query.lower()

    if query == "acp":
        log_path = args.log or os.path.join(project_root, ACP_LOG)
        pattern = PRESETS["acp"]
    else:
        log_path = resolve_log_path(args, project_root)
        if query == "node":
            node_id = args.node_id
            if not node_id:
                parser.error("'node' preset requires a nodeId argument: search_log.py node ak:01KK...")
            pattern = node_id
        elif query in PRESETS:
            pattern = PRESETS[query]
        else:
            # treat as raw pattern
            pattern = args.query

    if not os.path.exists(log_path):
        print(f"ERROR: log file not found: {log_path}", file=sys.stderr)
        print(f"  project_root resolved to: {project_root}", file=sys.stderr)
        sys.exit(1)

    print(f"Log: {log_path}")
    print(f"Pattern: {pattern!r}")
    print()

    if args.follow:
        tail_log(log_path)
    else:
        grep_log(pattern, log_path, args.limit)


if __name__ == "__main__":
    main()
