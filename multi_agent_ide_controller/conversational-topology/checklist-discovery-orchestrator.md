# Discovery Orchestrator Review Checklist

Review criteria for the discovery orchestrator agent. This agent decomposes the goal into discovery agent requests, controlling fan-out and scope coordination.

## Common Failure Modes

1. **Over-fan-out**: Agent splits discovery into many overlapping requests when one would suffice
2. **Under-scoping**: Agent creates a single discovery request that doesn't cover the full goal
3. **Scope overlap**: Multiple discovery agents search the same files/areas without differentiation
4. **Missing sequential ordering**: Agent doesn't order foundational discovery before higher-level discovery
5. **Goal drift**: Discovery requests address a reinterpretation of the goal rather than the actual goal

## ACTION Table

| Step | ACTION | Description | Gate |
|------|--------|-------------|------|
| 1 | EXTRACT_REQUIREMENTS | Parse the goal into numbered discovery objectives | MUST cover all aspects of the goal |
| 2 | VERIFY_FAN_OUT | Check agent count — default is 1, multiple only if truly independent tracks | FAIL if >1 agent without delegation rationale |
| 3 | CHECK_SCOPE_PARTITIONING | If multiple agents, verify non-overlapping scope with clear boundaries | FAIL if scope overlaps detected |
| 4 | VALIDATE_ORDERING | Verify foundational discovery is first, higher-level is later | FAIL if ordering would cause repeated work |
| 5 | CHECK_PRIOR_SUMMARY | If multiple agents, verify later agents receive prior agent context via priorAgentSummary | FAIL if sequential agents lack prior context |
| 6 | VERIFY_GOAL_FIDELITY | Compare discovery request goals with the original goal | FAIL if discovery requests address a different problem |
| 7 | JUSTIFICATION_PASSED | All checks pass — send JUSTIFICATION_PASSED with `--no-expect-response` | Agent may now return final result |

## Justification Questions to Ask

When the discovery orchestrator calls `callController` for justification:

- "Why did you create N discovery requests instead of 1?"
- "What is the non-overlapping scope boundary between agent A and agent B?"
- "Does the first agent's scope cover the foundational aspects (data model, interfaces, dependencies)?"
- "How will later agents build on earlier agents' findings?"
- "Is there any aspect of the goal not covered by any discovery request?"

## Red Flags

- 3+ discovery agents for a goal that touches a single subsystem
- No delegation rationale provided despite multiple agents
- Discovery requests use identical or near-identical goal descriptions
- No priorAgentSummary in requests that will run after the first
- Discovery requests focus on tangential code areas not related to the goal
