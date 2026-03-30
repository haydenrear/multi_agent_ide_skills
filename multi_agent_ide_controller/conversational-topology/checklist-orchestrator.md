# Orchestrator Review Checklist

Review criteria for the top-level orchestrator agent. The orchestrator routes the goal to discovery orchestrator, orchestrator collector, or interrupt. It is the entry point for all workflows.

## Common Failure Modes

1. **Skipping to collector**: Agent routes directly to orchestrator collector without running discovery/planning/tickets
2. **Goal reinterpretation**: Agent rewrites or narrows the goal before passing it downstream
3. **Premature completion**: Agent assumes prior phase results are sufficient without verifying
4. **Missing phase awareness**: Agent ignores the current phase and re-routes to discovery when planning or tickets are already underway

## ACTION Table

| Step | ACTION | Description | Gate |
|------|--------|-------------|------|
| 1 | EXTRACT_GOAL | Parse the original goal text into numbered requirements | MUST have all requirements listed |
| 2 | VERIFY_ROUTING | Check that the routing decision matches the current phase | FAIL if routing to discovery when phase is PLANNING or TICKETS |
| 3 | CHECK_GOAL_FIDELITY | Compare the goal text passed downstream with the original | FAIL if goal was narrowed, reworded, or requirements dropped |
| 4 | VALIDATE_PHASE_PROGRESSION | Verify the orchestrator is advancing the workflow, not looping | FAIL if same routing decision made 3+ times without progress |
| 5 | CHECK_COLLECTOR_READINESS | If routing to collector, verify all phases (discovery, planning, tickets) completed | FAIL if routing to collector with incomplete phases |
| 6 | ASSESS_INTERRUPT_JUSTIFICATION | If routing to interrupt, verify the reason is legitimate | ESCALATE if interrupt seems like stalling rather than genuine ambiguity |

## Justification Questions to Ask

When the orchestrator calls `callController` for justification:

- "What phase is the workflow currently in, and why are you routing to X?"
- "Has discovery been completed? What were the key findings?"
- "Has planning been completed? How many tickets were produced?"
- "Have all tickets been executed? What's the completion status?"
- "Why are you routing to collector — is all work genuinely complete?"
- "You're routing back to discovery — what specific gap needs to be filled?"

## Red Flags

- Orchestrator routes to collector on the first invocation (skipping all work)
- Goal text passed to discovery orchestrator is different from the original goal
- Orchestrator loops between discovery and itself without advancing
- Phase is TICKETS but orchestrator routes back to discovery without interrupt/review
- Orchestrator claims "workflow complete" but no ticket results exist
