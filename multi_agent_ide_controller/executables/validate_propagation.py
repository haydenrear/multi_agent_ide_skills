#!/usr/bin/env python3
"""
validate_propagation.py — Validate that propagation items contain the Propagation record structure.

Checks that each propagatedText field is a valid JSON object with both
`llmOutput` and `propagationRequest` keys (the Propagation record format).
Prints a summary with PASS/FAIL per item and an overall result.

Usage:
    python validate_propagation.py <nodeId>
    python validate_propagation.py <nodeId> --limit 10
    python validate_propagation.py <nodeId> --host http://localhost:8080
    python validate_propagation.py <nodeId> --raw     # dump full propagatedText for each item
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
        body_text = e.read().decode(errors="replace")
        print(f"ERROR {e.code}: {path} — {body_text[:200]}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"ERROR: {path} — {e}", file=sys.stderr)
        return None


def validate_item(item, raw=False):
    item_id = item.get("itemId", item.get("id", "?"))
    layer = item.get("layerId", "").split("/")[-1]
    stage = item.get("stage", "?")
    status = item.get("status", "?")
    pt = item.get("propagatedText")

    prefix = f"  itemId={item_id}  layer={layer}  stage={stage}  status={status}"

    if not pt:
        print(f"{prefix}")
        print(f"    FAIL — propagatedText is null/empty")
        return False

    if raw:
        print(f"{prefix}")
        print(f"    RAW: {pt[:500]}")

    try:
        d = json.loads(pt)
    except Exception as e:
        print(f"{prefix}")
        print(f"    FAIL — propagatedText is not valid JSON: {e}")
        return False

    has_llm = "llmOutput" in d
    has_req = "propagationRequest" in d

    if has_llm and has_req:
        llm_val = str(d.get("llmOutput", ""))[:120]
        req_val = d.get("propagationRequest", "")
        req_parsed = False
        req_keys = []
        if req_val:
            try:
                req_obj = json.loads(req_val)
                req_parsed = True
                req_keys = [k for k, v in req_obj.items() if v is not None][:6]
            except Exception:
                pass
        print(f"{prefix}")
        print(f"    PASS — llmOutput: {llm_val}")
        print(f"    {'propagationRequest: valid JSON, fields=' + str(req_keys) if req_parsed else 'propagationRequest: (not JSON) ' + req_val[:80]}")
        return True
    else:
        missing = []
        if not has_llm:
            missing.append("llmOutput")
        if not has_req:
            missing.append("propagationRequest")
        keys = list(d.keys())[:8]
        print(f"{prefix}")
        print(f"    FAIL — missing fields: {missing}  found keys: {keys}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Validate Propagation record structure in propagatedText")
    parser.add_argument("node_id", help="Workflow nodeId (ak:...)")
    parser.add_argument("--host", default="http://localhost:8080", help="App base URL")
    parser.add_argument("--limit", type=int, default=20, help="Items to fetch (default 20)")
    parser.add_argument("--raw", action="store_true", help="Dump full propagatedText per item")
    args = parser.parse_args()

    result = post(args.host, "/api/propagations/items/by-node",
                  {"nodeId": args.node_id, "limit": args.limit})
    if result is None:
        print("Failed to fetch propagation items.", file=sys.stderr)
        sys.exit(1)

    items = result.get("items", [])
    total = result.get("totalCount", 0)
    print(f"totalCount={total}  fetched={len(items)}\n")

    if not items:
        print("No items found.")
        return

    passed = 0
    failed = 0
    for item in items:
        ok = validate_item(item, raw=args.raw)
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\nResult: {passed} PASS / {failed} FAIL out of {len(items)} items")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
