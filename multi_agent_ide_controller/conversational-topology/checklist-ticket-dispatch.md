# Ticket Dispatch Review Checklist

Review criteria for the ticket dispatch agent. This agent routes ticket execution results to the ticket collector, synthesizing multiple ticket agent outputs into a single collector input.

## Common Failure Modes

1. **Missing failure reports**: Agent omits failed ticket results from synthesis
2. **Over-summarization**: Agent reduces ticket outputs to one-line summaries, losing implementation details
3. **Misrouting**: Agent routes away from collector without justification
4. **False success reporting**: Agent claims all tickets succeeded when some failed or were partial

## ACTION Table

| Step | ACTION | Description | Gate |
|------|--------|-------------|------|
| 1 | VERIFY_ALL_RESULTS | Check that all ticket agent results are present | FAIL if any ticket results missing |
| 2 | CHECK_FAILURE_REPORTING | Verify failed tickets are explicitly identified with reasons | FAIL if failures hidden or omitted |
| 3 | VALIDATE_SUCCESS_CLAIMS | Cross-reference success claims against actual ticket output | FAIL if agent claims success for tickets that failed |
| 4 | VALIDATE_ROUTING | Confirm agent routes to ticketCollectorRequest (the default) | WARN if routing elsewhere without justification |
| 5 | ASSESS_COLLECTOR_CONTEXT | Verify synthesis includes enough detail for collector to assess completeness | FAIL if collector can't determine what was actually implemented |
| 6 | JUSTIFICATION_PASSED | All checks pass — send JUSTIFICATION_PASSED with `--no-expect-response` | Agent may now return final result |

## Justification Questions to Ask

When the ticket dispatch agent calls `callController` for justification:

- "How many tickets succeeded vs failed?"
- "Are all ticket results accounted for in your synthesis?"
- "What specific details are you forwarding about each ticket's outcome?"
- "Why are you routing to X instead of the ticket collector?"

## Red Flags

- Synthesis omits any ticket entirely
- Agent reports 100% success but ticket outputs contain errors or incomplete work
- Agent adds implementation claims not present in any ticket agent's output
- Routing away from collector without interrupt justification
- Synthesis is significantly shorter than the combined ticket outputs
