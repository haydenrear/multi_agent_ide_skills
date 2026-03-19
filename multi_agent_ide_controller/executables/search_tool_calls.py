#!/usr/bin/env python3
"""
search_tool_calls.py — Search TOOL_CALL events in the workflow event stream.

Fetches all events for a node scope, filters to TOOL_CALL events, and optionally
searches summaries for a pattern (tool name, file path, etc.). Useful for detecting
file write attempts by read-only agents (discovery, planning).

Usage:
    python search_tool_calls.py <nodeId>
    python search_tool_calls.py <nodeId> --pattern "create_new_file"
    python search_tool_calls.py <nodeId> --pattern "Write|replace_text|create_new"
    python search_tool_calls.py <nodeId> --pattern "BranchState" --detail
    python search_tool_calls.py <nodeId> --write-only   # shortcut for write-like tools
"""
import argparse
import json
import re
import sys
import urllib.request
import urllib.error

# Tools that indicate write operations — used with --write-only
WRITE_TOOL_PATTERNS = [
    r"create_new_file",
    r"replace_text_in_file",
    r"Write\b",
    r"Edit\b",
    r"NotebookEdit",
    r"build_project",
    r"execute_terminal_command",
    r"execute_run_configuration",
]


def post(host, path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{host}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.URLError as e:
        print(f"ERROR: {path} — {e}", file=sys.stderr)
        return None


def fetch_all_events(host, node_id, event_type=None):
    """Fetch all events for a node scope, paginating with cursor."""
    all_items = []
    cursor = None
    while True:
        body = {"nodeId": node_id, "limit": 500, "truncate": 500, "sort": "asc"}
        if cursor:
            body["cursor"] = cursor
        result = post(host, "/api/ui/nodes/events", body)
        if not result:
            break
        items = result.get("items", [])
        if event_type:
            items = [i for i in items if i.get("eventType") == event_type]
        all_items.extend(items)

        meta = result.get("meta") or result
        next_cursor = meta.get("nextCursor") if isinstance(meta, dict) else result.get("nextCursor")
        if not next_cursor:
            break
        cursor = next_cursor
    return all_items


def fetch_event_detail(host, node_id, event_id):
    """Fetch full detail for a single event."""
    return post(host, "/api/ui/nodes/events/detail", {
        "nodeId": node_id,
        "eventId": event_id,
        "pretty": True,
        "maxFieldLength": -1,
    })


def main():
    parser = argparse.ArgumentParser(description="Search tool call events in the workflow event stream")
    parser.add_argument("node_id", help="Workflow nodeId (ak:...) — searches this node and all descendants")
    parser.add_argument("--pattern", "-p", help="Regex pattern to match in event summary (case-insensitive)")
    parser.add_argument("--write-only", "-w", action="store_true",
                        help="Shortcut: search for write-like tool calls (create_new_file, replace_text, Write, Edit, etc.)")
    parser.add_argument("--detail", "-d", action="store_true",
                        help="Fetch and show full event detail for each match")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max number of matches to show (0 = all)")
    parser.add_argument("--host", default="http://localhost:8080")
    args = parser.parse_args()

    # Build pattern
    pattern = args.pattern
    if args.write_only:
        pattern = "|".join(WRITE_TOOL_PATTERNS)
    regex = re.compile(pattern, re.IGNORECASE) if pattern else None

    print(f"Fetching TOOL_CALL events for {args.node_id}...")
    tool_calls = fetch_all_events(args.host, args.node_id, event_type="TOOL_CALL")
    print(f"Total TOOL_CALL events: {len(tool_calls)}")

    if regex:
        matches = [tc for tc in tool_calls if regex.search(tc.get("summary", ""))]
        print(f"Matches for /{pattern}/i: {len(matches)}")
    else:
        matches = tool_calls

    if args.limit > 0:
        matches = matches[:args.limit]

    for i, tc in enumerate(matches, 1):
        eid = tc.get("eventId", "?")
        nid = tc.get("nodeId", "?")
        ts = (tc.get("timestamp") or "")[:19]
        summary = tc.get("summary", "")
        # Show short nodeId suffix for readability
        nid_short = "..." + nid[-20:] if len(nid) > 25 else nid
        print(f"\n{'─'*70}")
        print(f"#{i}  eventId={eid[:12]}...  node={nid_short}  time={ts}")
        print(f"  {summary[:500]}")

        if args.detail:
            detail = fetch_event_detail(args.host, args.node_id, eid)
            if detail and detail.get("formattedDetail"):
                print(f"  DETAIL:")
                for line in detail["formattedDetail"].splitlines()[:40]:
                    print(f"    {line}")
                lines = detail["formattedDetail"].splitlines()
                if len(lines) > 40:
                    print(f"    ... ({len(lines) - 40} more lines)")

    if not matches:
        print("\nNo matching tool calls found.")
    else:
        print(f"\n{'─'*70}")
        print(f"Found {len(matches)} matching tool call(s).")


if __name__ == "__main__":
    main()
