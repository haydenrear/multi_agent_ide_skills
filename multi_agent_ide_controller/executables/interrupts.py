#!/usr/bin/env python3
"""
interrupts.py — Find and resolve pending interrupts for a workflow node.

Interrupts are surfaced via propagation items with layer=transitionToInterruptState
and status=PENDING. There is no GET /api/interrupts/pending endpoint — this script
derives pending interrupts from the propagation item stream.

For each pending interrupt it shows:
  - The reason and choices extracted from propagationRequest
  - The contextId to use for resolution

Usage:
    python interrupts.py <nodeId>                         # list pending interrupts
    python interrupts.py <nodeId> --resolve APPROVED      # approve (APPROVED/REJECTED/CANCELLED/FEEDBACK)
    python interrupts.py <nodeId> --resolve APPROVED --notes "A - Yes, proceed."
    python interrupts.py <nodeId> --host http://localhost:8080
"""
import argparse
import json
import sys
import urllib.request
import urllib.error

INTERRUPT_LAYER = "transitionToInterruptState"


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
        print(f"ERROR {e.code}: {path} — {body_text[:300]}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"ERROR: {path} — {e}", file=sys.stderr)
        return None


def find_pending_interrupts(host, node_id):
    """List pending interrupts from GET /api/interrupts/pending, filtered to node scope."""
    req = urllib.request.Request(f"{host}/api/interrupts/pending")
    try:
        with urllib.request.urlopen(req) as r:
            all_pending = json.load(r)
    except urllib.error.URLError as e:
        print(f"ERROR: /api/interrupts/pending — {e}", file=sys.stderr)
        return []
    # Filter to the requested node scope
    return [
        i for i in (all_pending if isinstance(all_pending, list) else [])
        if node_id in (i.get("originNodeId") or "")
        or (i.get("originNodeId") or "").startswith(node_id)
    ]


def parse_interrupt_item(item):
    """Extract reason, choices, and contextId from a propagation item."""
    pt = item.get("propagatedText") or ""
    context_id = None
    reason = item.get("summaryText") or ""
    choices = []
    llm_output = ""

    try:
        outer = json.loads(pt)
        llm_output = outer.get("llmOutput", "")
        req_str = outer.get("propagationRequest", "")
        if req_str:
            req = json.loads(req_str)
            ctx = req.get("contextId")
            if isinstance(ctx, dict):
                context_id = ctx.get("value")
            elif isinstance(ctx, str):
                context_id = ctx
            reason = req.get("reason") or reason
            choices = req.get("choices") or []
    except Exception:
        pass

    return {
        "itemId": item.get("itemId", item.get("id", "?")),
        "layerId": item.get("layerId", ""),
        "stage": item.get("stage", "?"),
        "contextId": context_id,
        "reason": reason,
        "choices": choices,
        "llmOutput": llm_output,
    }


def resolve_interrupt(host, interrupt_id, origin_node_id, resolution_type, notes):
    """Try resolving by interruptId first, fall back to originNodeId (ArtifactKey scope lookup)."""
    candidates = []
    if interrupt_id and interrupt_id != "?":
        candidates.append(interrupt_id)
    if origin_node_id and origin_node_id != "?":
        candidates.append(origin_node_id)

    for candidate in candidates:
        result = post(host, "/api/interrupts/resolve", {
            "id": candidate,
            "originNodeId": candidate,
            "resolutionType": resolution_type,
            "resolutionNotes": notes or "",
        })
        if result is not None and result.get("status") not in (None, "NOT_FOUND"):
            return result, candidate
    return None, None


def main():
    parser = argparse.ArgumentParser(description="Find and resolve pending interrupts")
    parser.add_argument("node_id", help="Workflow nodeId (ak:...)")
    parser.add_argument("--resolve", metavar="TYPE",
                        choices=["APPROVED", "REJECTED", "CANCELLED", "FEEDBACK", "RESOLVED"],
                        help="Resolution type")
    parser.add_argument("--notes", default="", help="Resolution notes (e.g. chosen option)")
    parser.add_argument("--host", default="http://localhost:8080")
    args = parser.parse_args()

    pending = find_pending_interrupts(args.host, args.node_id)

    if not pending:
        print("No pending interrupts found.")
        return

    print(f"{len(pending)} pending interrupt(s)\n")

    for item in pending:
        interrupt_id = item.get("interruptId", "?")
        origin_node = item.get("originNodeId", "?")
        reason = item.get("reason") or ""
        interrupt_type = item.get("interruptType", "?")

        # Enrich with detail if available
        detail = None
        detail_resp = post(args.host, "/api/interrupts/detail", {"id": interrupt_id})
        if detail_resp:
            detail = detail_resp

        print("─" * 60)
        print(f"interruptId : {interrupt_id}")
        print(f"originNodeId: ...{origin_node[-50:]}")
        print(f"type        : {interrupt_type}")
        if reason:
            print(f"reason      : {reason[:300]}")
        if detail:
            ctx = detail.get("contextForDecision") or ""
            if ctx:
                print(f"context     : {ctx[:300]}")

        if args.resolve:
            print(f"\nResolving as {args.resolve}...")
            result, used_id = resolve_interrupt(
                args.host, interrupt_id, origin_node, args.resolve, args.notes
            )
            if result:
                print(f"  RESOLVED via id={used_id}")
                print(f"  status={result.get('status')}  resumeNodeId={result.get('resumeNodeId')}")
            else:
                print("  FAILED — could not resolve interrupt", file=sys.stderr)
        else:
            node_str = args.node_id
            print(f"\n  → python interrupts.py {node_str} --resolve APPROVED [--notes \"<choice>\"]")

    print()


if __name__ == "__main__":
    main()
