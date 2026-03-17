#!/usr/bin/env python3
"""
poll.py — Combined one-shot status view for a running workflow.

Shows: workflow graph shape + propagation items (latest N) + pending permissions.
Use this as the primary polling command during a controller session.

Usage:
    python poll.py <nodeId>
    python poll.py <nodeId> --limit 3
    python poll.py <nodeId> --host http://localhost:8080
"""
import argparse
import json
import sys
import urllib.request
import urllib.error


def get(host, path):
    try:
        with urllib.request.urlopen(f"{host}{path}") as r:
            return json.load(r)
    except urllib.error.URLError as e:
        print(f"ERROR: {path} — {e}", file=sys.stderr)
        return None


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


def show_graph(node, depth=0):
    pad = "  " * depth
    ntype = node.get("nodeType", "?")
    status = node.get("currentStatus") or node.get("status", "?")
    action = node.get("actionName") or ""
    last_event = (node.get("lastEventAt") or "")[:19]
    pending = node.get("pendingItems", [])
    action_str = f"  action={action}" if action else ""
    last_str = f"  last={last_event}" if last_event else ""
    print(f"{pad}{ntype}  status={status}{action_str}{last_str}  pending={len(pending)}")
    for p in pending:
        print(f"{pad}  ⚠ PENDING: {p}")
    for child in node.get("children", [])[:8]:
        show_graph(child, depth + 1)


def summarize_payload(pt):
    """Extract the most meaningful fields from a propagatedText JSON payload.

    Handles the Propagation record structure: {"llmOutput": "...", "propagationRequest": {...}}
    where propagationRequest is now a native JSON object (not a double-encoded string).
    Also handles legacy flat payloads for backwards compatibility.
    """
    if not pt:
        return "(empty)"
    try:
        d = json.loads(pt)
        # Propagation record structure: llmOutput + propagationRequest (native object)
        if "llmOutput" in d or "propagationRequest" in d:
            llm = d.get("llmOutput", "")
            req = d.get("propagationRequest")
            # req is now a dict (native JSON object), not a string
            if isinstance(req, str):
                try:
                    req = json.loads(req)
                except Exception:
                    req = None
            llm_summary = str(llm)[:200] if llm else "(no llm output)"
            req_summary = ""
            if req and isinstance(req, dict):
                for key in ["goal", "delegationRationale", "output", "collectorDecision"]:
                    v = req.get(key)
                    if v:
                        req_summary = f"  req.{key}: {str(v)[:150]}"
                        break
                if not req_summary:
                    active = [k for k, v in req.items() if v is not None]
                    req_summary = f"  req.fields: {active[:6]}"
            return f"llmOutput: {llm_summary}{chr(10) + '    ' + req_summary.strip() if req_summary else ''}"
        # Legacy flat payload — priority fields
        for key in ["goal", "delegationRationale", "output", "collectorDecision", "mergeError"]:
            v = d.get(key)
            if v:
                if isinstance(v, dict):
                    v = json.dumps(v)
                return f"{key}: {str(v)[:300]}"
        # Fall back to listing non-null keys
        active = [k for k, v in d.items() if v is not None]
        return f"fields: {active[:8]}"
    except Exception:
        return pt[:200]


def main():
    parser = argparse.ArgumentParser(description="Poll workflow status")
    parser.add_argument("node_id", help="Workflow nodeId (ak:...)")
    parser.add_argument("--limit", type=int, default=2, help="Propagation items to show (default 2)")
    parser.add_argument("--host", default="http://localhost:8080", help="App base URL")
    args = parser.parse_args()

    host = args.host
    node_id = args.node_id

    print(f"═══ WORKFLOW GRAPH  nodeId={node_id} ═══")
    graph = post(host, "/api/ui/workflow-graph", {"nodeId": node_id})
    if graph:
        s = graph["stats"]
        event_counts = s.get("eventTypeCounts") or {}
        goal_done = event_counts.get("GOAL_COMPLETED", 0)
        node_errors = event_counts.get("NODE_ERROR", 0)
        completion = "  *** GOAL_COMPLETED ***" if goal_done else ""
        error_flag = f"  NODE_ERROR={node_errors}" if node_errors else ""
        print(f"events={s['totalEvents']}  chatMsgs={s['chatMessageEvents']}  "
              f"errors={s['recentErrorCount']}{error_flag}{completion}")
        root = graph.get("root")
        if root:
            show_graph(root)
        else:
            print("  (root not yet visible — run still initializing)")
    print()

    print(f"═══ PROPAGATION ITEMS  limit={args.limit} ═══")
    prop = post(host, "/api/propagations/items/by-node",
                {"nodeId": node_id, "limit": args.limit})
    if prop:
        print(f"totalCount={prop['totalCount']}")
        for item in prop["items"]:
            stage = item.get("stage", "?")
            layer = item.get("layerId", "").split("/")[-1]
            status = item.get("status", "?")
            summary = item.get("summaryText", "") or ""
            pt = item.get("propagatedText")  # now a Propagation dict from API
            pt_str = json.dumps(pt) if isinstance(pt, dict) else (pt or "")
            print(f"  [{stage}] {layer}  status={status}")
            if summary:
                print(f"    summary: {summary[:120]}")
            print(f"    {summarize_payload(pt_str)}")
    print()

    print("═══ PENDING PERMISSIONS ═══")
    perms = get(host, "/api/permissions/pending")
    if perms:
        print(f"{len(perms)} pending")
        for p in perms:
            rid = p["requestId"]
            node = p.get("nodeId", "?")
            print(f"  requestId={rid}  node=...{node[-30:]}")
            # Fetch detail to show tool name and input
            detail = get(host, f"/api/permissions/detail?id={rid}")
            if detail:
                for tc in (detail.get("toolCalls") or [])[:2]:
                    tool = tc.get("title", "unknown-tool")
                    raw_in = tc.get("rawInput")
                    input_str = json.dumps(raw_in)[:200] if raw_in else "(no input)"
                    print(f"    tool={tool}")
                    print(f"    input={input_str}")
    else:
        print("0 pending")
    print()

    print("═══ PENDING INTERRUPTS ═══")
    interrupts = get(host, "/api/interrupts/pending") or []
    if interrupts:
        print(f"{len(interrupts)} pending")
        for i in (interrupts if isinstance(interrupts, list) else []):
            print(f"  interruptId={i.get('interruptId', '?')}  node=...{str(i.get('originNodeId',''))[-30:]}")
            reason = i.get("reason") or i.get("message") or ""
            if reason:
                print(f"    reason: {reason[:150]}")
        print("  → run: interrupts.py <nodeId> --resolve APPROVED [--notes \"<choice>\"]")
    else:
        print("0 pending")


if __name__ == "__main__":
    main()
