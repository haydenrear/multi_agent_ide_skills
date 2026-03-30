# Discovery Dispatch Review Checklist

Review criteria for the discovery dispatch agent. This agent routes discovery results to the discovery collector, synthesizing multiple discovery agent outputs into a single collector input.

## Core Protocol: Research Before Judging

For every ACTION below, you MUST:
1. **Research the relevant sources yourself** before evaluating the agent's claims
2. **Share your findings** with the agent — especially discrepancies or things the agent missed
3. **Ask the agent to confirm**: acknowledge your insights, update its proposed result, or justify its original position
4. **Wait for the agent's response** before progressing to the next ACTION

## Common Failure Modes

1. **Lossy synthesis**: Agent drops important discovery findings when consolidating for the collector
2. **Premature routing**: Agent routes to collector before all discovery agents have reported results
3. **Missing context**: Agent doesn't provide enough synthesis for the collector to make ADVANCE_PHASE vs ROUTE_BACK decision
4. **Misrouting**: Agent routes to interrupt or other targets instead of defaulting to collector

## ACTION Table

| Step | ACTION | What YOU (controller) Research | What to Tell the Agent | Gate |
|------|--------|-------------------------------|----------------------|------|
| 1 | VERIFY_RESULT_PREVIEW | Check that the justification previews the routing target and synthesis content | If missing: "I need to see your routing target and a summary of what you're forwarding to the collector" | FAIL if no result preview |
| 2 | RESEARCH_RAW_OUTPUTS | Read each discovery agent's raw output yourself — note key findings | Share: "Discovery agent A's key finding about [X] — is this preserved in your synthesis? Agent B found [Y] — I don't see it forwarded." | Conversation starter — agent must respond |
| 3 | VERIFY_ALL_RESULTS | After the agent responds, check that all discovery results are accounted for | FAIL if discovery results are missing or incomplete |
| 4 | CHECK_SYNTHESIS_QUALITY | Compare synthesis against raw outputs for completeness | FAIL if important findings dropped |
| 5 | VALIDATE_ROUTING | Confirm agent routes to collectorRequest (the default) | WARN if routing elsewhere without clear justification |
| 6 | ASSESS_COLLECTOR_CONTEXT | Check that enough context is provided for collector's ADVANCE/ROUTE_BACK decision | FAIL if collector input lacks findings summary |
| 7 | JUSTIFICATION_PASSED | All checks pass — send JUSTIFICATION_PASSED with `--no-expect-response` | Agent may now return final result |

## Red Flags

- Dispatch synthesis is shorter than any individual discovery agent result
- Agent routes away from collector without interrupt justification
- Key architectural findings from discovery agents are absent in the synthesis
- Agent adds its own new findings not present in any discovery agent's output
- Agent's justification has no result preview — only reasoning
