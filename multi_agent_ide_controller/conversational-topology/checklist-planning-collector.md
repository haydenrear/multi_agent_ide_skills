# Planning Collector Review Checklist

Review criteria for the planning collector agent. This agent finalizes tickets, dependency graphs, and consolidated output, then decides whether to advance to TICKETS or route back for more planning.

## Common Failure Modes

1. **Ticket bloat**: Agent creates excessive tickets for simple changes, adding coordination overhead
2. **Missing dependencies**: Agent doesn't capture ordering constraints between tickets
3. **Vague ticket descriptions**: Tickets lack specific file paths, tasks, or acceptance criteria
4. **Premature advancement**: Agent advances to TICKETS with incomplete or contradictory plans
5. **Non-structured output**: Agent writes files instead of returning structured PlanningCollectorResult

## ACTION Table

| Step | ACTION | Description | Gate |
|------|--------|-------------|------|
| 1 | VERIFY_FINALIZED_TICKETS | Check that finalizedTickets list is populated with complete ticket objects | FAIL if tickets missing ticketId, title, description, tasks, or acceptanceCriteria |
| 2 | CHECK_DEPENDENCY_GRAPH | Verify dependencyGraph captures real ordering constraints | FAIL if tickets have implicit dependencies not in the graph |
| 3 | MAP_TO_REQUIREMENTS | Each goal requirement must map to at least one ticket | FAIL if requirements have no ticket coverage |
| 4 | ASSESS_GRANULARITY | Each ticket should be a single reviewable unit (<= 5 files) | WARN if any ticket spans > 5 files or multiple subsystems |
| 5 | VERIFY_STRUCTURED_OUTPUT | Confirm output uses structured fields, not file writes | FAIL if agent writes files instead of returning schema |
| 6 | VALIDATE_DECISION | If ADVANCE_PHASE, requestedPhase must be "TICKETS" | FAIL if advancing to wrong phase |
| 7 | CHECK_ROUTE_BACK_PROTOCOL | If ROUTE_BACK, verify interrupt was raised first | FAIL if ROUTE_BACK without prior interrupt/review |
| 8 | JUSTIFICATION_PASSED | All checks pass — send JUSTIFICATION_PASSED with `--no-expect-response` | Agent may now return final result |

## Justification Questions to Ask

When the planning collector calls `callController` for justification:

- "How many finalized tickets are there, and do they cover all requirements?"
- "What is the dependency order between tickets?"
- "Are there any tickets that touch more than 5 files?"
- "Why are you advancing to TICKETS — is the plan complete?"
- "You're routing back — what specific planning gaps need to be addressed?"

## Red Flags

- finalizedTickets is empty or has only 1 ticket for a multi-requirement goal
- Tickets reference file paths that don't exist in the codebase
- dependencyGraph is empty when tickets clearly have ordering needs
- Agent sets requestedPhase to something other than "TICKETS" when advancing
- Ticket acceptance criteria are just restated requirements, not verifiable conditions
- Agent sets ROUTE_BACK without first raising interrupt (violates protocol)
