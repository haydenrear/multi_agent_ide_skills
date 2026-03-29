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


def poll_once(host, node_id, limit):
    """Run a single poll cycle. Returns True if the run is terminally complete."""
    print(f"═══ WORKFLOW GRAPH  nodeId={node_id} ═══")
    graph = post(host, "/api/ui/workflow-graph", {"nodeId": node_id})
    terminal = False
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
        terminal = bool(goal_done)
    print()

    print(f"═══ PROPAGATION ITEMS  limit={limit} ═══")
    prop = post(host, "/api/propagations/items/by-node",
                {"nodeId": node_id, "limit": limit})
    if prop:
        print(f"totalCount={prop['totalCount']}")
        for pos, item in enumerate(prop["items"], 1):
            stage = item.get("stage", "?")
            layer = item.get("layerId", "").split("/")[-1]
            status = item.get("status", "?")
            item_id = item.get("itemId", "")
            summary = item.get("summaryText", "") or ""
            pt = item.get("propagatedText")  # now a Propagation dict from API
            pt_str = json.dumps(pt) if isinstance(pt, dict) else (pt or "")
            print(f"  [{stage}] {layer}  status={status}  itemId={item_id}")
            if summary:
                print(f"    summary: {summary[:120]}")
            print(f"    {summarize_payload(pt_str)}")
            print(f"    → python propagation_detail.py {node_id} --limit {pos}  (item #{pos} most recent — review full payload)")
    print()

    print("═══ PENDING PERMISSIONS ═══")
    perms = get(host, "/api/permissions/pending")
    if perms:
        print(f"{len(perms)} pending")
        for p in perms:
            rid = p["requestId"]
            node = p.get("nodeId", "?")
            print(f"  requestId={rid}  node=...{node[-30:]}")
            detail = get(host, f"/api/permissions/detail?id={rid}")
            if detail:
                for tc in (detail.get("toolCalls") or [])[:2]:
                    tool = tc.get("title", "unknown-tool")
                    raw_in = tc.get("rawInput")
                    input_str = json.dumps(raw_in)[:200] if raw_in else "(no input)"
                    print(f"    tool={tool}")
                    print(f"    input={input_str}")
            print(f"    → python permissions.py --resolve  (requestId={rid})")
    else:
        print("0 pending")
    print()

    print("═══ PENDING INTERRUPTS ═══")
    interrupts = get(host, "/api/interrupts/pending") or []
    if interrupts:
        print(f"{len(interrupts)} pending")
        for i in (interrupts if isinstance(interrupts, list) else []):
            interrupt_id = i.get("interruptId", "?")
            origin = str(i.get("originNodeId", ""))
            print(f"  interruptId={interrupt_id}  node=...{origin[-30:]}")
            reason = i.get("reason") or i.get("message") or ""
            if reason:
                print(f"    reason: {reason[:150]}")
            print(f"    → python interrupts.py {node_id} --resolve APPROVED")
    else:
        print("0 pending")
    print()

    print("═══ CONVERSATIONS ═══")
    convos = post(host, "/api/agent-conversations/list", {"nodeId": node_id})
    if convos:
        pending_convos = [c for c in convos if c.get("pending")]
        print(f"{len(convos)} total, {len(pending_convos)} pending")
        for c in convos:
            target = c.get("targetKey", "?")
            agent_type = c.get("agentType", "?")
            iid = c.get("interruptId", "?")
            reason = c.get("reason", "")
            status = "PENDING" if c.get("pending") else "resolved"
            print(f"  [{status}] {agent_type}  target=...{str(target)[-30:]}  interruptId={iid}")
            if reason:
                print(f"    justification: {reason[:150]}")
            if c.get("pending"):
                print(f"    → python conversations.py {node_id} --respond --message \"...\" (interruptId={iid})")
    else:
        print("0 conversations")

    return terminal


def subscribe_loop(host, node_id, limit, max_wait, tick):
    """Activity-check every tick seconds; full poll on activity or timeout (FR-042, FR-043)."""
    import time
    elapsed = 0
    print(f"Subscribing for {max_wait}s — checking every {tick}s — Ctrl-C to stop\n")
    try:
        while elapsed < max_wait:
            result = post(host, "/api/ui/activity-check", {"nodeId": node_id})
            if result and result.get("hasActivity"):
                print(f"Activity detected at {elapsed}s — running full poll\n")
                done = poll_once(host, node_id, limit)
                if done:
                    print(f"\n✓ GOAL_COMPLETED — stopping subscribe.")
                return  # always return on activity so caller can take action
            else:
                time.sleep(tick)
                elapsed += tick
        print(f"Subscribe timeout ({max_wait}s) — running final poll\n")
        poll_once(host, node_id, limit)
    except KeyboardInterrupt:
        print("\nSubscribe stopped.")


def main():
    import time
    parser = argparse.ArgumentParser(description="Poll workflow status")
    parser.add_argument("node_id", help="Workflow nodeId (ak:...)")
    parser.add_argument("--limit", type=int, default=2, help="Propagation items to show (default 2)")
    parser.add_argument("--host", default="http://localhost:8080", help="App base URL")
    parser.add_argument("--watch", type=int, default=0, metavar="SECS",
                        help="Poll every N seconds until GOAL_COMPLETED or Ctrl-C")
    parser.add_argument("--subscribe", type=int, default=0, metavar="SECS",
                        help="Max wait duration — activity-check every --tick seconds, full poll on activity")
    parser.add_argument("--tick", type=int, default=5, metavar="SECS",
                        help="Activity-check interval when using --subscribe (default 5)")
    args = parser.parse_args()

    host = args.host
    node_id = args.node_id

    if args.subscribe:
        subscribe_loop(host, node_id, args.limit, args.subscribe, args.tick)
    elif args.watch:
        import time
        interval = args.watch
        print(f"Watching every {interval}s — Ctrl-C to stop\n")
        try:
            while True:
                done = poll_once(host, node_id, args.limit)
                if done:
                    print(f"\n✓ GOAL_COMPLETED — stopping watch.")
                    break
                print(f"--- next poll in {interval}s ---\n")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nWatch stopped.")
    else:
        poll_once(host, node_id, args.limit)


if __name__ == "__main__":
    main()
