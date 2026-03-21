#!/usr/bin/env python3
"""
permissions.py — Inspect and resolve pending tool permissions.

Shows each pending permission with the full tool name and raw input so you
can decide whether to allow or reject before acting. Optionally resolves all
as ALLOW_ALWAYS after displaying them.

The first permission in a new session may appear before the ToolCallEvent is
flushed by the ACP stream buffer. This script retries the detail fetch for up
to --detail-timeout seconds. If tool info still isn't available, it prints
what is known and proceeds (blind approve if --resolve is set).

Usage:
    python permissions.py                           # list only, no resolve
    python permissions.py --resolve                 # show then resolve all as ALLOW_ALWAYS
    python permissions.py --resolve --dry-run       # show what would be resolved
    python permissions.py --resolve --option REJECT_ONCE
    python permissions.py --detail-timeout 10       # wait up to 10s for tool info (default 6)
    python permissions.py --host http://localhost:8080
"""
import argparse
import json
import sys
import time
import urllib.request
import urllib.error


def get(host, path):
    try:
        with urllib.request.urlopen(f"{host}{path}") as r:
            return json.load(r)
    except urllib.error.URLError as e:
        print(f"ERROR GET {path}: {e}", file=sys.stderr)
        return None


def post_json(host, path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{host}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.URLError as e:
        print(f"ERROR POST {path}: {e}", file=sys.stderr)
        return None


def fetch_detail_with_retry(host, rid, timeout_secs):
    """Retry /detail until toolCalls is non-empty or timeout expires.

    The first permission in a new node often arrives before the ToolCallEvent
    is flushed from the ACP stream buffer. Retrying for a few seconds usually
    gives the buffer time to catch up.
    """
    deadline = time.monotonic() + timeout_secs
    detail = None
    while time.monotonic() < deadline:
        detail = get(host, f"/api/permissions/detail?id={rid}")
        if detail and detail.get("toolCalls"):
            return detail, False  # (detail, blind)
        time.sleep(1)
    return detail, True  # timed out — blind approve may be needed


def show_tool_calls(tool_calls):
    for tc in tool_calls:
        tool = tc.get("title", "unknown")
        kind = tc.get("kind", "")
        status = tc.get("status", "")
        raw_in = tc.get("rawInput")
        raw_out = tc.get("rawOutput")
        print(f"tool      : {tool}  (kind={kind} status={status})")
        if raw_in is not None:
            input_str = json.dumps(raw_in, indent=2) if isinstance(raw_in, dict) else str(raw_in)
            print("input     :")
            for line in input_str[:600].splitlines():
                print(f"  {line}")
        if raw_out is not None:
            out_str = json.dumps(raw_out, indent=2) if isinstance(raw_out, dict) else str(raw_out)
            print(f"output    : {out_str[:200]}")


def main():
    parser = argparse.ArgumentParser(description="Inspect and resolve permissions")
    parser.add_argument("--resolve", action="store_true",
                        help="Resolve all displayed permissions as ALLOW_ALWAYS after inspection")
    parser.add_argument("--dry-run", action="store_true",
                        help="With --resolve: print what would be resolved but don't send")
    parser.add_argument("--option", default="ALLOW_ALWAYS",
                        choices=["ALLOW_ALWAYS", "ALLOW_ONCE", "REJECT_ONCE", "REJECT_ALWAYS"],
                        help="Resolution option (default: ALLOW_ALWAYS)")
    parser.add_argument("--note", default="",
                        help="Note sent to the AI agent when rejecting (REJECT_ONCE/REJECT_ALWAYS). "
                             "Explains why the tool call was denied so the agent can adjust.")
    parser.add_argument("--detail-timeout", type=int, default=6,
                        help="Seconds to wait for tool call info before blind-approving (default: 6)")
    parser.add_argument("--host", default="http://localhost:8080")
    args = parser.parse_args()

    perms = get(args.host, "/api/permissions/pending") or []
    print(f"Pending permissions: {len(perms)}")

    if not perms:
        print("  (none)")
        return

    to_resolve = []

    for p in perms:
        rid = p["requestId"]
        origin = p.get("originNodeId", "?")
        node = p.get("nodeId", "?")
        print(f"\n{'─'*60}")
        print(f"requestId : {rid}")
        print(f"originNode: {origin}")
        print(f"node      : {node}")

        detail, blind = fetch_detail_with_retry(args.host, rid, args.detail_timeout)
        if detail:
            tool_calls = detail.get("toolCalls") or []
            if tool_calls:
                show_tool_calls(tool_calls)
            else:
                # ToolCallEvent not yet flushed by ACP buffer — show permissions object
                print(f"  [tool info unavailable after {args.detail_timeout}s — ACP buffer not yet flushed]")
                print(f"permissions: {json.dumps(detail.get('permissions', {}))[:400]}")
                if blind and args.resolve:
                    print("  → blind-approving (tool info unavailable)")
        else:
            print("  (could not fetch detail)")

        options = p.get("permissions", [])
        option_names = [o.get("kind") for o in (options if isinstance(options, list) else [])]
        print(f"options   : {option_names}")
        print(f"  → python permissions.py --resolve                   (ALLOW_ALWAYS all)")
        print(f"  → python permissions.py --resolve --option REJECT_ONCE")
        to_resolve.append(rid)

    if args.resolve:
        print(f"\n{'═'*60}")
        if args.dry_run:
            print(f"[DRY RUN] Would resolve {len(to_resolve)} permission(s) as {args.option}")
            for rid in to_resolve:
                print(f"  {rid}")
        else:
            print(f"Resolving {len(to_resolve)} permission(s) as {args.option}...")
            for rid in to_resolve:
                body = {"id": rid, "optionType": args.option, "note": args.note}
                result = post_json(args.host, "/api/permissions/resolve", body)
                status = result.get("status", "?") if result else "ERROR"
                print(f"  {rid} → {status}")


if __name__ == "__main__":
    main()
