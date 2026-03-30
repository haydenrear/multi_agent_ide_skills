#!/usr/bin/env python3
"""
conversations.py — CLI for managing agent-to-controller conversations.

Usage:
    python conversations.py <nodeId>                          # List active conversations
    python conversations.py <nodeId> --pending                # Show only pending conversations
    python conversations.py <nodeId> --respond --message "..." --interrupt-id <id> --action-name <ACTION>  # Respond
    python conversations.py <nodeId> --host http://localhost:8080
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
    except urllib.error.URLError as e:
        print(f"ERROR: {path} — {e}", file=sys.stderr)
        return None


def list_conversations(host, node_id, pending_only=False):
    convos = post(host, "/api/agent-conversations/list", {"nodeId": node_id})
    if not convos:
        print("No conversations found.")
        return

    if pending_only:
        convos = [c for c in convos if c.get("pending")]

    if not convos:
        print("No pending conversations.")
        return

    print(f"{'PENDING' if pending_only else 'ALL'} CONVERSATIONS under {node_id}")
    print(f"{'─' * 60}")
    for c in convos:
        target = c.get("targetKey", "?")
        agent_type = c.get("agentType", "?")
        iid = c.get("interruptId", "?")
        reason = c.get("reason", "")
        status = "⏳ PENDING" if c.get("pending") else "✓ resolved"
        print(f"\n  {status}  type={agent_type}")
        print(f"  target=...{str(target)[-40:]}")
        print(f"  interruptId={iid}")
        if reason:
            print(f"  justification:")
            for line in reason.splitlines():
                print(f"    {line}")


def respond_to_conversation(host, interrupt_id, message, action_name, expect_response=True):
    body = {
        "interruptId": interrupt_id,
        "message": message,
        "expectResponse": expect_response,
        "checklistAction": action_name,
    }

    result = post(host, "/api/agent-conversations/respond", body)
    if result:
        status = result.get("status", "unknown")
        msg = result.get("message", "")
        print(f"Response: {status} — {msg}")
        print(f"  action: {action_name}")
    else:
        print("Failed to deliver response.", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Manage agent-to-controller conversations")
    parser.add_argument("node_id", help="Workflow nodeId (ak:...)")
    parser.add_argument("--host", default="http://localhost:8080", help="App base URL")
    parser.add_argument("--pending", action="store_true", help="Show only pending conversations")
    parser.add_argument("--respond", action="store_true", help="Respond to a pending conversation")
    parser.add_argument("--message", type=str, help="Response message (with --respond)")
    parser.add_argument("--interrupt-id", type=str, help="Interrupt ID to respond to (with --respond)")
    parser.add_argument("--action-name", type=str,
                        help="REQUIRED with --respond: checklist ACTION name being executed "
                             "(e.g. EXTRACT_REQUIREMENTS, VERIFY_SCOPE, CHECK_ARCHITECTURE). "
                             "Tracks which checklist step the controller is on for self-improvement.")
    parser.add_argument("--no-expect-response", action="store_true",
                        help="Don't tell the agent to respond via call_controller (default: agent is told to respond)")
    args = parser.parse_args()

    if args.respond:
        if not args.interrupt_id:
            print("ERROR: --interrupt-id required with --respond", file=sys.stderr)
            sys.exit(1)
        if not args.message:
            print("ERROR: --message required with --respond", file=sys.stderr)
            sys.exit(1)
        if not args.action_name:
            print("ERROR: --action-name required with --respond. "
                  "Specify the checklist ACTION step (e.g. EXTRACT_REQUIREMENTS, VERIFY_SCOPE).",
                  file=sys.stderr)
            sys.exit(1)
        respond_to_conversation(args.host, args.interrupt_id, args.message,
                                args.action_name, not args.no_expect_response)
    else:
        list_conversations(args.host, args.node_id, args.pending)


if __name__ == "__main__":
    main()
