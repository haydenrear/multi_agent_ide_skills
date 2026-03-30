# Planning Dispatch Review Checklist

Review criteria for the planning dispatch agent. This agent routes planning results to the planning collector, synthesizing multiple planning agent outputs into a single collector input.

## Common Failure Modes

1. **Lossy consolidation**: Agent drops tickets or implementation details when synthesizing for the collector
2. **Conflicting plans merged**: Agent merges planning outputs without detecting contradictions between agents
3. **Missing context**: Agent doesn't provide enough synthesis for the collector to finalize tickets
4. **Misrouting**: Agent routes away from collector without justification

## ACTION Table

| Step | ACTION | Description | Gate |
|------|--------|-------------|------|
| 1 | VERIFY_ALL_RESULTS | Check that all planning agent results are present | FAIL if planning results missing or incomplete |
| 2 | CHECK_TICKET_PRESERVATION | Verify all tickets from all planning agents are preserved in synthesis | FAIL if tickets dropped during consolidation |
| 3 | DETECT_CONTRADICTIONS | Check for conflicting approaches between planning agents | ESCALATE if agents proposed incompatible strategies |
| 4 | VALIDATE_ROUTING | Confirm agent routes to planningCollectorRequest (the default) | WARN if routing elsewhere without justification |
| 5 | ASSESS_COLLECTOR_CONTEXT | Verify enough detail for collector to produce finalizedTickets | FAIL if synthesis lacks ticket descriptions, tasks, or acceptance criteria |
| 6 | JUSTIFICATION_PASSED | All checks pass — send JUSTIFICATION_PASSED with `--no-expect-response` | Agent may now return final result |

## Justification Questions to Ask

When the planning dispatch agent calls `callController` for justification:

- "Are all planning agent outputs accounted for in your synthesis?"
- "Did any planning agents propose conflicting approaches?"
- "How many total tickets are being forwarded to the collector?"
- "Why are you routing to X instead of the planning collector?"

## Red Flags

- Synthesis has fewer tickets than the sum of individual planning agent outputs
- Agent doesn't mention any planning results by name or content
- Routing away from collector without raising an interrupt first
- Agent introduces new tickets not present in any planning agent's output
