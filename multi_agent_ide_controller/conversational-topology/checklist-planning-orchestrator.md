# Planning Orchestrator Review Checklist

Review criteria for the planning orchestrator agent. This agent decomposes the goal into planning agent requests based on discovery results, controlling fan-out and scope.

## Common Failure Modes

1. **Over-fan-out**: Agent creates multiple planning requests when the goal is a single implementation track
2. **Ignoring discovery findings**: Agent plans without referencing the discovery output
3. **Scope drift**: Planning requests include work not in the original goal
4. **Missing implementation tracks**: Agent omits a planning request for a requirement identified during discovery
5. **Non-structured output**: Agent tries to write files or use tools instead of returning structured PlanningAgentRequests

## ACTION Table

| Step | ACTION | Description | Gate |
|------|--------|-------------|------|
| 1 | VERIFY_DISCOVERY_INPUT | Confirm planning requests reference discovery findings | FAIL if planning ignores discovery output |
| 2 | CHECK_FAN_OUT | Verify agent count — default is 1, multiple only for independent tracks | FAIL if >1 agent without delegation rationale |
| 3 | MAP_REQUIREMENTS | Each goal requirement should map to at least one planning request | FAIL if any requirement has no planning coverage |
| 4 | CHECK_SCOPE_BOUNDARIES | If multiple agents, verify non-overlapping implementation tracks | FAIL if scope overlaps between planning agents |
| 5 | VERIFY_STRUCTURED_OUTPUT | Confirm agent returns structured output, not file writes or tool calls | FAIL if agent attempts to write files |
| 6 | VALIDATE_INDEPENDENCE | If multiple agents, verify each track can be planned independently | FAIL if tracks have implicit cross-dependencies |
| 7 | JUSTIFICATION_PASSED | All checks pass — send JUSTIFICATION_PASSED with `--no-expect-response` | Agent may now return final result |

## Justification Questions to Ask

When the planning orchestrator calls `callController` for justification:

- "How does the planning decomposition relate to the discovery findings?"
- "Why did you create N planning requests instead of 1?"
- "Which discovery findings informed each planning track?"
- "Are there any goal requirements not covered by any planning request?"
- "Are the planning tracks truly independent, or do they share dependencies?"

## Red Flags

- Planning requests don't reference any specific discovery findings
- Agent creates planning tracks that mirror discovery agent splits rather than implementation tracks
- Planning requests include "refactor" or "improve" work not in the original goal
- Agent produces file outputs instead of structured PlanningAgentRequests
- Multiple planning agents assigned to the same subsystem
