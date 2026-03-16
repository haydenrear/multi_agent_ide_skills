# Controller Executables Reference

Scripts in this directory are written and maintained by the controller during sessions. Before writing a new script, check this index — if a matching script exists, use it (and improve it if needed).

| Script | Description |
|--------|-------------|
| `poll.py <nodeId>` | One-shot combined view: workflow graph shape + latest propagation items + pending permissions with tool detail. Primary polling command. |
| `permissions.py` | List all pending permissions with full tool name and rawInput. Use `--resolve` to approve all after inspection, `--option REJECT_ONCE` to reject. |
| `propagation_detail.py <nodeId>` | Full propagation payload detail with parsed JSON. Shows goal, output, agentResult, collectorDecision etc. Use `--raw` for full JSON. |
