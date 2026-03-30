# Discovery Dispatch Review Checklist

Review criteria for the discovery dispatch agent. This agent routes discovery results to the discovery collector, synthesizing multiple discovery agent outputs into a single collector input.

## Common Failure Modes

1. **Lossy synthesis**: Agent drops important discovery findings when consolidating for the collector
2. **Premature routing**: Agent routes to collector before all discovery agents have reported results
3. **Missing context**: Agent doesn't provide enough synthesis for the collector to make ADVANCE_PHASE vs ROUTE_BACK decision
4. **Misrouting**: Agent routes to interrupt or other targets instead of defaulting to collector

## ACTION Table

| Step | ACTION | Description | Gate |
|------|--------|-------------|------|
| 1 | VERIFY_ALL_RESULTS | Check that all discovery agent results are present in the input | FAIL if discovery results are missing or incomplete |
| 2 | CHECK_SYNTHESIS_QUALITY | Verify the dispatch synthesis preserves key findings from each agent | FAIL if important findings dropped |
| 3 | VALIDATE_ROUTING | Confirm agent routes to collectorRequest (the default) | WARN if routing elsewhere without clear justification |
| 4 | ASSESS_COLLECTOR_CONTEXT | Check that enough context is provided for collector's ADVANCE/ROUTE_BACK decision | FAIL if collector input lacks findings summary |
| 5 | JUSTIFICATION_PASSED | All checks pass — send JUSTIFICATION_PASSED with `--no-expect-response` | Agent may now return final result |

## Justification Questions to Ask

When the discovery dispatch agent calls `callController` for justification:

- "Are all discovery agent results accounted for in your synthesis?"
- "What key findings are you forwarding to the collector?"
- "Why are you routing to X instead of the collector?"
- "Is there enough context for the collector to decide whether to advance or route back?"

## Red Flags

- Dispatch synthesis is shorter than any individual discovery agent result
- Agent routes away from collector without interrupt justification
- Key architectural findings from discovery agents are absent in the synthesis
- Agent adds its own new findings not present in any discovery agent's output
