#!/usr/bin/env python3
"""
propagation_detail.py — Read propagation items with full payload detail.

Shows the most recent N propagation items for a node, with parsed JSON
payloads formatted for readability. Use when poll.py summary isn't enough.

Usage:
    python propagation_detail.py <nodeId>
    python propagation_detail.py <nodeId> --limit 5
    python propagation_detail.py <nodeId> --fields goal,agentResult,output
    python propagation_detail.py <nodeId> --raw        # full JSON, no filtering
"""
import argparse
import json
import sys
import urllib.request
import urllib.error

# Fields most useful for understanding agent decisions, in priority order
DEFAULT_FIELDS = [
    "goal",
    "delegationRationale",
    "output",
    "agentResult",
    "collectorDecision",
    "planningResults",
    "consolidatedOutput",
    "recommendations",
    "mergeError",
    "conflictFiles",
    "tickets",
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


def show_payload(pt, fields, raw):
    if not pt:
        print("  (empty propagatedText)")
        return
    try:
        d = json.loads(pt)
    except Exception:
        print(f"  (non-JSON): {pt[:300]}")
        return

    if raw:
        print(json.dumps(d, indent=2, default=str))
        return

    shown = False
    for f in fields:
        v = d.get(f)
        if v is None:
            continue
        shown = True
        if isinstance(v, (dict, list)):
            v_str = json.dumps(v, indent=2, default=str)
        else:
            v_str = str(v)
        # Indent multiline
        lines = v_str.splitlines()
        if len(lines) == 1:
            print(f"  {f}: {lines[0][:300]}")
        else:
            print(f"  {f}:")
            for line in lines[:20]:
                print(f"    {line}")
            if len(lines) > 20:
                print(f"    ... ({len(lines) - 20} more lines)")

    if not shown:
        active = [k for k, v in d.items() if v is not None]
        print(f"  (no priority fields present — active keys: {active[:10]})")


def main():
    parser = argparse.ArgumentParser(description="Propagation item detail viewer")
    parser.add_argument("node_id", help="Workflow nodeId (ak:...)")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--fields", default=",".join(DEFAULT_FIELDS),
                        help="Comma-separated fields to show (default: goal,output,agentResult,...)")
    parser.add_argument("--raw", action="store_true", help="Print full JSON without field filtering")
    parser.add_argument("--host", default="http://localhost:8080")
    args = parser.parse_args()

    fields = [f.strip() for f in args.fields.split(",")]
    result = post(args.host, "/api/propagations/items/by-node",
                  {"nodeId": args.node_id, "limit": args.limit})
    if not result:
        sys.exit(1)

    items = result.get("items", [])
    print(f"totalCount={result['totalCount']}  showing={len(items)}")

    for item in items:
        stage = item.get("stage", "?")
        layer = item.get("layerId", "").split("/")[-1]
        status = item.get("status", "?")
        created = item.get("createdAt", "?")
        summary = item.get("summaryText") or ""
        pt = item.get("propagatedText") or ""

        print(f"\n{'─'*60}")
        print(f"[{stage}] {layer}  status={status}  created={created[:19]}")
        if summary:
            print(f"  AI summary: {summary[:150]}")
        print(f"  payload ({len(pt)} chars):")
        show_payload(pt, fields, args.raw)


if __name__ == "__main__":
    main()
