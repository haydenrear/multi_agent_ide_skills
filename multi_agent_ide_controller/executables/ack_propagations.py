#!/usr/bin/env python3
"""
ack_propagations.py — Acknowledge all pending propagation items for a node.

Fetches all PENDING items for the given nodeId and resolves each with ACKNOWLEDGED.
Prints the count and itemId for each resolved item.

Usage:
    python ack_propagations.py <nodeId>
    python ack_propagations.py <nodeId> --host http://localhost:8080
    python ack_propagations.py <nodeId> --dry-run   # list without resolving
    python ack_propagations.py <nodeId> --limit 20  # fetch up to N items (default 50)
"""
import argparse
import json
import sys
import urllib.request
import urllib.error


def post(host, path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{host}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"ERROR {e.code}: {path} — {body[:200]}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"ERROR: {path} — {e}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description="Acknowledge all pending propagation items")
    parser.add_argument("node_id", help="Workflow nodeId (ak:...)")
    parser.add_argument("--host", default="http://localhost:8080", help="App base URL")
    parser.add_argument("--dry-run", action="store_true", help="List items without resolving")
    parser.add_argument("--limit", type=int, default=50, help="Max items to fetch (default 50)")
    args = parser.parse_args()

    host = args.host
    node_id = args.node_id

    result = post(host, "/api/propagations/items/by-node",
                  {"nodeId": node_id, "limit": args.limit})
    if result is None:
        print("Failed to fetch propagation items.", file=sys.stderr)
        sys.exit(1)

    items = result.get("items", [])
    total = result.get("totalCount", 0)
    pending = [i for i in items if i.get("status", "").upper() == "PENDING"]

    print(f"totalCount={total}  fetched={len(items)}  pending={len(pending)}")

    if not pending:
        print("Nothing to acknowledge.")
        return

    if args.dry_run:
        for item in pending:
            item_id = item.get("itemId", item.get("id", "?"))
            layer = item.get("layerId", "").split("/")[-1]
            stage = item.get("stage", "?")
            print(f"  [DRY-RUN] would ack  itemId={item_id}  layer={layer}  stage={stage}")
        return

    acked = 0
    for item in pending:
        item_id = item.get("itemId", item.get("id"))
        if not item_id:
            print("  SKIP — no itemId", file=sys.stderr)
            continue
        layer = item.get("layerId", "").split("/")[-1]
        stage = item.get("stage", "?")
        res = post(host, f"/api/propagations/items/{item_id}/resolve",
                   {"resolutionType": "ACKNOWLEDGED"})
        if res is not None:
            print(f"  ACK  itemId={item_id}  layer={layer}  stage={stage}")
            acked += 1
        else:
            print(f"  FAIL itemId={item_id}  layer={layer}  stage={stage}", file=sys.stderr)

    print(f"\nAcknowledged {acked}/{len(pending)} items.")


if __name__ == "__main__":
    main()
