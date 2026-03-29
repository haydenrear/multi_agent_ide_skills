#!/usr/bin/env python3
"""
error_search.py — Structured error search for multi_agent_ide runtime logs.

Uses error_patterns.csv (co-located) to search for known error types.
Two modes:

  1. Summary mode (default): For each pattern in the CSV, report:
     - count of matches
     - earliest and latest timestamp
     - description from CSV
     Sorted by most-recent-first so the most active errors appear at top.

  2. Detail mode (--type <pattern_name_or_index>): Print the last N matching
     lines for a specific error type.

Usage:
    python error_search.py                        # summary of all known errors
    python error_search.py --type "NODE_ERROR"    # last 5 matches for NODE_ERROR
    python error_search.py --type 3               # last 5 matches for pattern at row 3
    python error_search.py --type "NODE_ERROR" --limit 20   # last 20 matches
    python error_search.py --raw "some pattern"   # ad-hoc grep (not from CSV)
    python error_search.py --project-root /path   # override project root

Flags:
    --type <name|index>   Show detail for a specific error type (substring match on expression or description)
    --limit N             Max lines in detail mode (default 5)
    --raw <pattern>       Ad-hoc grep pattern (bypasses CSV)
    --project-root <p>    Override project root (default: reads from tmp_repo.txt)
    --log <path>          Override log file path
    --acp                 Search ACP error log instead of runtime log
    --csv <path>          Override error_patterns.csv path
"""
import argparse
import csv
import os
import re
import subprocess
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV = os.path.join(SCRIPT_DIR, "error_patterns.csv")
TMP_REPO_FILE = "/private/tmp/multi_agent_ide_parent/tmp_repo.txt"
RUNTIME_LOG = "multi-agent-ide.log"
ACP_LOG = "multi_agent_ide_java_parent/multi_agent_ide/claude-agent-acp-errs.log"

# Matches log timestamps like "20:13:15.041" or "2026-03-28 20:13:15.041"
TIMESTAMP_RE = re.compile(r"(\d{2}:\d{2}:\d{2})\.\d+")


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
    log_name = ACP_LOG if args.acp else RUNTIME_LOG
    if project_root:
        return os.path.join(project_root, log_name)
    return log_name


def load_patterns(csv_path):
    """Load error patterns from CSV. Returns list of (expression, description)."""
    patterns = []
    try:
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                expr = row.get("error_expression", "").strip().strip('"')
                desc = row.get("description", "").strip().strip('"')
                if expr:
                    patterns.append((expr, desc))
    except FileNotFoundError:
        print(f"ERROR: CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    return patterns


def grep_count_and_timestamps(pattern, log_path):
    """Run grep, return (count, first_timestamp, last_timestamp, last_lines)."""
    result = subprocess.run(
        ["grep", "-n", "-i", "-E", pattern, log_path],
        capture_output=True, text=True
    )
    lines = [l for l in result.stdout.strip().split("\n") if l]
    if not lines:
        return 0, None, None, []

    timestamps = []
    for line in lines:
        m = TIMESTAMP_RE.search(line)
        if m:
            timestamps.append(m.group(1))

    first_ts = timestamps[0] if timestamps else "?"
    last_ts = timestamps[-1] if timestamps else "?"
    return len(lines), first_ts, last_ts, lines


def summary_mode(patterns, log_path):
    """Print aggregate summary of all error patterns."""
    results = []
    for i, (expr, desc) in enumerate(patterns):
        count, first_ts, last_ts, _ = grep_count_and_timestamps(expr, log_path)
        if count > 0:
            results.append((count, first_ts, last_ts, expr, desc, i + 1))

    if not results:
        print("No known error patterns found in the log.")
        return

    # Sort by last timestamp descending (most recent first)
    results.sort(key=lambda r: r[2] if r[2] != "?" else "", reverse=True)

    print(f"{'#':>3}  {'Count':>6}  {'First':>8}  {'Latest':>8}  Description")
    print(f"{'─'*3}  {'─'*6}  {'─'*8}  {'─'*8}  {'─'*50}")
    for count, first_ts, last_ts, expr, desc, idx in results:
        # Truncate description to fit
        short_desc = desc[:60] + "..." if len(desc) > 60 else desc
        print(f"{idx:>3}  {count:>6}  {first_ts:>8}  {last_ts:>8}  {short_desc}")

    total = sum(r[0] for r in results)
    print(f"\n{total} total error matches across {len(results)} active patterns.")
    print(f"\nUse --type <#> or --type <substring> to see detail for a specific pattern.")


def detail_mode(patterns, log_path, type_query, limit):
    """Print last N matches for a specific error type."""
    # Try numeric index first
    try:
        idx = int(type_query) - 1
        if 0 <= idx < len(patterns):
            expr, desc = patterns[idx]
        else:
            print(f"ERROR: index {type_query} out of range (1-{len(patterns)})", file=sys.stderr)
            sys.exit(1)
    except ValueError:
        # Substring match on expression or description
        matches = [(e, d) for e, d in patterns if type_query.lower() in e.lower() or type_query.lower() in d.lower()]
        if not matches:
            print(f"ERROR: no pattern matching '{type_query}'", file=sys.stderr)
            print(f"Available patterns:", file=sys.stderr)
            for i, (e, d) in enumerate(patterns):
                print(f"  {i+1}. {e[:40]}  — {d[:50]}", file=sys.stderr)
            sys.exit(1)
        if len(matches) > 1:
            print(f"Multiple matches for '{type_query}':", file=sys.stderr)
            for e, d in matches:
                print(f"  {e[:40]}  — {d[:50]}", file=sys.stderr)
            print(f"Using first match.", file=sys.stderr)
        expr, desc = matches[0]

    count, first_ts, last_ts, lines = grep_count_and_timestamps(expr, log_path)

    print(f"Pattern: {expr}")
    print(f"Description: {desc}")
    print(f"Total matches: {count}")
    if count > 0:
        print(f"Time window: {first_ts} — {last_ts}")
    print()

    if not lines:
        print("(no matches)")
        return

    shown = lines[-limit:]
    omitted = len(lines) - len(shown)
    if omitted > 0:
        print(f"... ({omitted} earlier matches omitted, showing last {limit})")
    for line in shown:
        print(line)


def raw_mode(pattern, log_path, limit):
    """Ad-hoc grep, not from CSV."""
    result = subprocess.run(
        ["grep", "-n", "-i", "-E", pattern, log_path],
        capture_output=True, text=True
    )
    lines = [l for l in result.stdout.strip().split("\n") if l]
    if not lines:
        print(f"(no matches for: {pattern})")
        return
    shown = lines[-limit:]
    omitted = len(lines) - len(shown)
    if omitted > 0:
        print(f"... ({omitted} earlier matches omitted, showing last {limit})")
    for line in shown:
        print(line)
    print(f"\n{len(lines)} total match(es).")


def main():
    parser = argparse.ArgumentParser(description="Structured error search for multi_agent_ide logs")
    parser.add_argument("--type", dest="error_type", help="Error type (CSV row index or substring match)")
    parser.add_argument("--limit", type=int, default=5, help="Max lines in detail mode (default 5)")
    parser.add_argument("--raw", help="Ad-hoc grep pattern (bypasses CSV)")
    parser.add_argument("--project-root", help="Override project root")
    parser.add_argument("--log", help="Explicit log file path")
    parser.add_argument("--acp", action="store_true", help="Search ACP error log")
    parser.add_argument("--csv", default=DEFAULT_CSV, help="Path to error_patterns.csv")
    args = parser.parse_args()

    project_root = resolve_project_root(args)
    if not project_root:
        print("WARNING: could not resolve project root — using current directory", file=sys.stderr)
        project_root = "."

    log_path = resolve_log_path(args, project_root)
    if not os.path.exists(log_path):
        print(f"ERROR: log file not found: {log_path}", file=sys.stderr)
        print(f"  project_root resolved to: {project_root}", file=sys.stderr)
        sys.exit(1)

    print(f"Log: {log_path}")
    print()

    if args.raw:
        raw_mode(args.raw, log_path, args.limit)
        return

    patterns = load_patterns(args.csv)
    if not patterns:
        print("ERROR: no patterns loaded from CSV", file=sys.stderr)
        sys.exit(1)

    if args.error_type:
        detail_mode(patterns, log_path, args.error_type, args.limit)
    else:
        summary_mode(patterns, log_path)


if __name__ == "__main__":
    main()
