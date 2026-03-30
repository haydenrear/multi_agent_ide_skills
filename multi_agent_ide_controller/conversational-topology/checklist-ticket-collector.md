# Ticket Collector Review Checklist

Review criteria for the ticket collector agent. This agent summarizes completed/failed tickets, reviews worktree commits, and decides whether to advance to COMPLETE or route back for more ticket work.

## Common Failure Modes

1. **Rubber-stamping success**: Agent marks COMPLETE without actually reviewing the worktree commits
2. **Missing failure analysis**: Agent doesn't explain why tickets failed or what remains to be done
3. **Ignoring partial implementations**: Agent treats partially-completed tickets as fully complete
4. **Premature COMPLETE**: Agent advances despite known failures, without follow-up items
5. **Route-back without specifics**: Agent proposes route-back but doesn't specify which tickets need re-execution

## ACTION Table

| Step | ACTION | Description | Gate |
|------|--------|-------------|------|
| 1 | VERIFY_TICKET_ACCOUNTING | All tickets must appear in either completed or failed list | FAIL if any ticket unaccounted for |
| 2 | CHECK_COMMIT_REVIEW | Verify agent actually reviewed worktree commits, not just ticket summaries | FAIL if no reference to actual code changes |
| 3 | MAP_TO_GOAL | For each original requirement, verify at least one completed ticket addresses it | FAIL if requirements have no completed ticket coverage |
| 4 | VALIDATE_FAILURE_REASONS | Failed tickets must have specific failure reasons | FAIL if failure listed without explanation |
| 5 | CHECK_FOLLOW_UPS | Verify outstanding follow-ups are specific and actionable | WARN if follow-ups are vague |
| 6 | VERIFY_DECISION_TYPE | ADVANCE_PHASE → requestedPhase = "COMPLETE"; ROUTE_BACK → specific ticket gaps | FAIL if decision type contradicts evidence |
| 7 | CHECK_ROUTE_BACK_PROTOCOL | If ROUTE_BACK, verify interrupt was raised first | FAIL if ROUTE_BACK without prior interrupt/review |
| 8 | ASSESS_COMPLETENESS_HONESTLY | Does the actual implementation match the goal, or are there real gaps? | ESCALATE if gaps exist but agent claims completion |
| 9 | JUSTIFICATION_PASSED | All checks pass — send JUSTIFICATION_PASSED with `--no-expect-response` | Agent may now return final result |

## Justification Questions to Ask

When the ticket collector calls `callController` for justification:

- "How many tickets completed vs failed?"
- "Did you review the actual commits in the worktree? What did they contain?"
- "Which requirements from the original goal are fully addressed?"
- "Are there any requirements with only partial or no implementation?"
- "You're marking COMPLETE — what gives you confidence the goal is fully met?"
- "You're routing back — which specific tickets need re-execution and why?"

## Red Flags

- Agent says "all tickets completed successfully" but ticket results show failures
- No mention of worktree commits or actual code changes
- Agent's summary describes work that doesn't match the ticket results
- COMPLETE decision with known failed tickets and no follow-up items
- Route-back without specifying exactly which tickets/gaps need attention
- Agent sets ROUTE_BACK without first raising interrupt (violates protocol)
- Follow-ups are generic ("improve test coverage") rather than specific ("add test for X in file Y")
