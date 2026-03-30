# Ticket Dispatch Review Checklist

Review criteria for the ticket dispatch agent. This agent routes ticket execution results to the ticket collector, synthesizing multiple ticket agent outputs into a single collector input.

## Core Protocol: Research Before Judging

For every ACTION below, you MUST:
1. **Research the relevant sources yourself** before evaluating the agent's claims
2. **Share your findings** with the agent — especially discrepancies or things the agent missed
3. **Ask the agent to confirm**: acknowledge your insights, update its proposed result, or justify its original position
4. **Wait for the agent's response** before progressing to the next ACTION

## Common Failure Modes

1. **Missing failure reports**: Agent omits failed ticket results from synthesis
2. **Over-summarization**: Agent reduces ticket outputs to one-line summaries, losing implementation details
3. **Misrouting**: Agent routes away from collector without justification
4. **False success reporting**: Agent claims all tickets succeeded when some failed or were partial

## ACTION Table

| Step | ACTION | What YOU (controller) Research | What to Tell the Agent | Gate |
|------|--------|-------------------------------|----------------------|------|
| 1 | VERIFY_RESULT_PREVIEW | Check that the justification previews the routing target and synthesis content | If missing: "I need to see your routing target, ticket success/fail breakdown, and what you're forwarding to the collector" | FAIL if no result preview |
| 2 | RESEARCH_RAW_OUTPUTS | Read each ticket agent's raw output yourself — note successes, failures, partial completions, and error messages | Share: "Ticket agent for T-001 reported [success with caveat X]. Ticket agent for T-003 had [compilation error Y]. Is this accurately reflected in your synthesis?" | Conversation starter — agent must respond |
| 3 | VERIFY_ALL_RESULTS | After the agent responds, check that all ticket agent results are present | FAIL if any ticket results missing |
| 4 | CHECK_FAILURE_REPORTING | Verify failed tickets are explicitly identified with reasons | FAIL if failures hidden or omitted |
| 5 | VALIDATE_SUCCESS_CLAIMS | Cross-reference success claims against actual ticket output — look for partial implementations claimed as complete | FAIL if agent claims success for tickets that failed |
| 6 | VALIDATE_ROUTING | Confirm agent routes to ticketCollectorRequest (the default) | WARN if routing elsewhere without justification |
| 7 | ASSESS_COLLECTOR_CONTEXT | Verify synthesis includes enough detail for collector to assess what was actually implemented | FAIL if collector can't determine what was actually implemented |
| 8 | JUSTIFICATION_PASSED | All checks pass — send JUSTIFICATION_PASSED with `--no-expect-response` | Agent may now return final result |

## Red Flags

- Synthesis omits any ticket entirely
- Agent reports 100% success but ticket outputs contain errors or incomplete work
- Agent adds implementation claims not present in any ticket agent's output
- Routing away from collector without interrupt justification
- Synthesis is significantly shorter than the combined ticket outputs
- Agent's justification has no result preview — only reasoning
