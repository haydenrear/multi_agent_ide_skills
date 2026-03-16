# Controller Executables Reference

Scripts in this directory are written and maintained by the controller during sessions. Before writing a new script, check this index — if a matching script exists, use it (and improve it if needed).

| Script | Description |
|--------|-------------|
| `poll.py <nodeId>` | One-shot combined view: workflow graph shape + latest propagation items + pending permissions with tool detail. Primary polling command. Handles the new `Propagation` record structure (`llmOutput`/`propagationRequest`) as well as legacy flat payloads. |
| `permissions.py` | List all pending permissions with full tool name and rawInput. Use `--resolve` to approve all after inspection, `--option REJECT_ONCE` to reject. |
| `propagation_detail.py <nodeId>` | Full propagation payload detail with parsed JSON. Shows goal, output, agentResult, collectorDecision etc. Use `--raw` for full JSON. |
| `ack_propagations.py <nodeId>` | Acknowledge all PENDING propagation items for a node. Use `--dry-run` to list without resolving. Use `--limit N` to control fetch size. |
| `validate_propagation.py <nodeId>` | Validate that all propagation items contain the `Propagation` record structure (`llmOutput` + `propagationRequest`). Prints PASS/FAIL per item. Use `--raw` to dump full `propagatedText`. Exits non-zero if any fail. |
