# Controller Executables Reference

Scripts in this directory are written and maintained by the controller during sessions. Before writing a new script, check this index — if a matching script exists, use it (and improve it if needed).

| Script | Description |
|--------|-------------|
| `poll.py <nodeId> --subscribe 600` | **Primary monitoring command.** Checks activity endpoint every `--tick` seconds (default 5). Runs a full poll only when activity is detected (permissions, interrupts, conversations, propagations). Auto-stops on `GOAL_COMPLETED`. Use this for all ongoing monitoring — do not sleep-and-poll. |
| `poll.py <nodeId>` | One-shot combined view: workflow graph + propagation items + permissions + interrupts + conversations. Use for quick status checks only. |
| `permissions.py` | List all pending permissions with full tool name and rawInput. Use `--resolve` to approve all after inspection, `--option REJECT_ONCE` to reject. `--note "reason"` sends a message to the AI agent explaining why a rejection was made. `--detail-timeout N` (default 6s) retries the tool-call detail fetch before blind-approving — handles the ACP buffer delay on first permissions. |
| `interrupts.py <nodeId>` | List pending interrupts via `GET /api/interrupts/pending`. Shows interruptId, reason, type, contextForDecision. Use `--resolve APPROVED [--notes "..."]` to resolve. |
| `propagation_detail.py <nodeId>` | Full propagation payload detail with parsed JSON. Shows goal, output, agentResult, collectorDecision etc. Use `--raw` for full JSON. |
| `ack_propagations.py <nodeId>` | Acknowledge all PENDING propagation items for a node. Use `--dry-run` to list without resolving. Use `--limit N` to control fetch size. |
| `validate_propagation.py <nodeId>` | Validate that all propagation items contain the `Propagation` record structure (`llmOutput` + `propagationRequest`). Prints PASS/FAIL per item. Use `--raw` to dump full `propagatedText`. Exits non-zero if any fail. |
| `conversations.py <nodeId>` | List active agent-to-controller conversations. Use `--pending` for unresponded only. Use `--respond --interrupt-id <id> --action-name <ACTION> --message "..."` to respond — `--action-name` is **required** and tracks the checklist step (e.g. `VERIFY_SCOPE`, `CHECK_ARCHITECTURE`, `APPROVE`). Use `--no-expect-response` for final approvals. |
| `search_tool_calls.py <nodeId>` | Search TOOL_CALL events in the event stream. Use `--pattern "regex"` to filter by tool name/path, `--write-only` to find write-like tools (create_new_file, replace_text, Write, Edit), `--detail` for full event payloads. |
