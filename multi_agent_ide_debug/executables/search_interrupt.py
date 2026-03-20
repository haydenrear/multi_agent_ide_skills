#!/usr/bin/env python3
"""
search_interrupt.py — Trace interrupt lifecycle in the runtime log.

Searches for the full interrupt flow: publish → agent review → resolve → feedback return.
Helps diagnose WAITING_REVIEW stalls where interrupt resolution doesn't propagate back.

Usage:
    python search_interrupt.py                          # all interrupt events
    python search_interrupt.py --node ak:01KM...        # interrupt events for a specific run
    python search_interrupt.py --phase publish           # only publish events
    python search_interrupt.py --phase resolve           # only resolve events
    python search_interrupt.py --phase feedback          # only feedback handling
    python search_interrupt.py --phase review            # only AI review agent calls
    python search_interrupt.py --phase template          # template rendering (review_resolution)
    python search_interrupt.py --phase error             # errors near interrupt handling
    python search_interrupt.py --context 5               # show N lines of context around matches

Phases trace the InterruptService flow:
  publish   → publishInterrupt / awaitInterruptBlocking
  resolve   → resolveInterrupt / RESOLVED / resolution
  feedback  → "Handling feedback" / "Resolved feedback" / "After feedback handled"
  review    → runInterruptAgentReview / ReviewAgentResult / REVIEW_AGENT
  template  → review_resolution / TEMPLATE_REVIEW_RESOLUTION
  error     → ERROR/Exception within 5 lines of interrupt-related log entries
"""
import argparse
import os
import subprocess
import sys

TMP_REPO_FILE = "/private/tmp/multi_agent_ide_parent/tmp_repo.txt"
RUNTIME_LOG = "multi-agent-ide.log"

PHASE_PATTERNS = {
    "publish": r"publishInterrupt|awaitInterrupt|INTERRUPT_REQUESTED|interrupt.*publish",
    "resolve": r"resolveInterrupt|RESOLVED.*interrupt|interrupt.*resolv|InterruptResolution|resumeNodeId",
    "feedback": r"Handling feedback from AI|Resolved feedback|After feedback handled|interruptFeedback",
    "review": r"runInterruptAgentReview|ReviewAgentResult|REVIEW_AGENT|review.*agent.*result|agent.*review",
    "template": r"review_resolution|REVIEW_RESOLUTION|TEMPLATE_REVIEW_RESOLUTION|workflow/review",
    "error": r"ERROR.*interrupt|Exception.*interrupt|interrupt.*error|interrupt.*fail|interrupt.*null",
}

# Combined pattern for all phases
ALL_PATTERN = "|".join(PHASE_PATTERNS.values())


def resolve_project_root(args):
    if args.project_root:
        return args.project_root
    try:
        with open(TMP_REPO_FILE) as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def grep_log(pattern, log_path, limit, node_filter=None, context_lines=0):
    flags = ["-n", "-i"]
    if context_lines > 0:
        flags.extend(["-C", str(context_lines)])
    result = subprocess.run(
        ["grep"] + flags + ["-E", pattern, log_path],
        capture_output=True, text=True
    )
    lines = [l for l in result.stdout.strip().split("\n") if l]
    if node_filter:
        lines = [l for l in lines if node_filter in l or l.startswith("--")]
    if not lines:
        print("(no matches)")
        return
    shown = lines[-limit:]
    omitted = len(lines) - len(shown)
    if omitted > 0:
        print(f"... ({omitted} earlier matches omitted, showing last {limit})")
    for line in shown:
        print(line)
    print(f"\n{len(lines)} total match(es).")


def main():
    parser = argparse.ArgumentParser(description="Trace interrupt lifecycle in logs")
    parser.add_argument("--node", help="Filter to a specific nodeId / run ID")
    parser.add_argument("--phase", choices=list(PHASE_PATTERNS.keys()),
                        help="Show only a specific phase of the interrupt flow")
    parser.add_argument("--context", "-C", type=int, default=0,
                        help="Show N lines of context around each match")
    parser.add_argument("--limit", type=int, default=80, help="Max lines to show")
    parser.add_argument("--log", help="Explicit log file path")
    parser.add_argument("--project-root", help="Override project root")
    args = parser.parse_args()

    project_root = resolve_project_root(args)
    if not project_root:
        print("WARNING: could not resolve project root", file=sys.stderr)
        project_root = "."

    log_path = args.log or os.path.join(project_root, RUNTIME_LOG)
    if not os.path.exists(log_path):
        print(f"ERROR: log file not found: {log_path}", file=sys.stderr)
        sys.exit(1)

    pattern = PHASE_PATTERNS.get(args.phase, ALL_PATTERN) if args.phase else ALL_PATTERN

    print(f"Log: {log_path}")
    print(f"Phase: {args.phase or 'all'}")
    if args.node:
        print(f"Node filter: {args.node}")
    print(f"Pattern: {pattern!r}")
    print()

    grep_log(pattern, log_path, args.limit, args.node, args.context)


if __name__ == "__main__":
    main()
