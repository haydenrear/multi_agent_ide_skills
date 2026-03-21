# Controller Executables Reference

Scripts in this directory are written and maintained by the controller during sessions. Before writing a new script, check this index — if a matching script exists, use it (and improve it if needed).

| Script | Description |
|--------|-------------|
| `poll.py <nodeId>` | One-shot combined view: workflow graph shape + latest propagation items + pending permissions + pending interrupts. Primary polling command. |
| `permissions.py` | List all pending permissions with full tool name and rawInput. Use `--resolve` to approve all after inspection, `--option REJECT_ONCE` to reject. `--note "reason"` sends a message to the AI agent explaining why a rejection was made. `--detail-timeout N` (default 6s) retries the tool-call detail fetch before blind-approving — handles the ACP buffer delay on first permissions. |
| `interrupts.py <nodeId>` | List pending interrupts via `GET /api/interrupts/pending`. Shows interruptId, reason, type, contextForDecision. Use `--resolve APPROVED [--notes "..."]` to resolve. |
| `propagation_detail.py <nodeId>` | Full propagation payload detail with parsed JSON. Shows goal, output, agentResult, collectorDecision etc. Use `--raw` for full JSON. |
| `ack_propagations.py <nodeId>` | Acknowledge all PENDING propagation items for a node. Use `--dry-run` to list without resolving. Use `--limit N` to control fetch size. |
| `validate_propagation.py <nodeId>` | Validate that all propagation items contain the `Propagation` record structure (`llmOutput` + `propagationRequest`). Prints PASS/FAIL per item. Use `--raw` to dump full `propagatedText`. Exits non-zero if any fail. |
| `search_tool_calls.py <nodeId>` | Search TOOL_CALL events in the event stream. Use `--pattern "regex"` to filter by tool name/path, `--write-only` to find write-like tools (create_new_file, replace_text, Write, Edit), `--detail` for full event payloads. |
