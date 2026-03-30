# Ticket Collector Review Checklist

Review criteria for the ticket collector agent. This agent summarizes completed/failed tickets, reviews worktree commits, and decides whether to advance to COMPLETE or route back for more ticket work.

## Core Protocol: Research Before Judging

For every ACTION below, you MUST:
1. **Research the relevant sources yourself** before evaluating the agent's claims
2. **Share your findings** with the agent — especially discrepancies or things the agent missed
3. **Ask the agent to confirm**: acknowledge your insights, update its proposed result, or justify its original position
4. **Wait for the agent's response** before progressing to the next ACTION

## Common Failure Modes

1. **Rubber-stamping success**: Agent marks COMPLETE without actually reviewing the worktree commits
2. **Missing failure analysis**: Agent doesn't explain why tickets failed or what remains to be done
3. **Ignoring partial implementations**: Agent treats partially-completed tickets as fully complete
4. **Premature COMPLETE**: Agent advances despite known failures, without follow-up items
5. **Route-back without specifics**: Agent proposes route-back but doesn't specify which tickets need re-execution
6. **Missing route-back review protocol**: Agent sets ROUTE_BACK directly without first raising an interrupt for review

## ACTION Table

| Step | ACTION | What YOU (controller) Research | What to Tell the Agent | Gate |
|------|--------|-------------------------------|----------------------|------|
| 1 | VERIFY_RESULT_PREVIEW | Check that the justification previews ticket outcomes, requirement coverage, and phase decision | If missing: "I need to see your completed/failed ticket breakdown, which requirements are addressed, and your ADVANCE/ROUTE_BACK decision" | FAIL if no result preview |
| 2 | RESEARCH_TICKET_RESULTS | Read each ticket agent's raw output and worktree commits yourself — note what was actually implemented vs what was claimed | Share: "Ticket T-001 claims to have implemented [X] but the commit only shows [Y]. Ticket T-003's output mentions a compilation error — did you account for this?" | Conversation starter — agent must respond |
| 3 | VERIFY_TICKET_ACCOUNTING | After the agent responds, check that all tickets appear in either completed or failed list | FAIL if any ticket unaccounted for |
| 4 | CHECK_COMMIT_REVIEW | Verify agent actually reviewed worktree commits, not just ticket summaries | FAIL if no reference to actual code changes |
| 5 | RESEARCH_REQUIREMENT_COVERAGE | Map each original goal requirement to completed ticket results — check the actual code yourself | Share: "For requirement N, ticket T-002 was supposed to address it, but I checked the commit and [the implementation covers it / it only partially addresses it / the key piece is missing]." | Conversation starter — agent must respond |
| 6 | MAP_TO_GOAL | After hearing the agent's response, verify each requirement has completed ticket coverage | FAIL if requirements have no completed ticket coverage |
| 7 | VALIDATE_FAILURE_REASONS | Failed tickets must have specific failure reasons | FAIL if failure listed without explanation |
| 8 | CHECK_FOLLOW_UPS | Verify outstanding follow-ups are specific and actionable | WARN if follow-ups are vague |
| 9 | VERIFY_DECISION_TYPE | ADVANCE_PHASE → requestedPhase = "COMPLETE"; ROUTE_BACK → specific ticket gaps | FAIL if decision type contradicts evidence |
| 10 | CHECK_ROUTE_BACK_PROTOCOL | If ROUTE_BACK, verify interrupt was raised first | FAIL if ROUTE_BACK without prior interrupt/review |
| 11 | ASSESS_COMPLETENESS_HONESTLY | Does the actual implementation match the goal, or are there real gaps? | ESCALATE if gaps exist but agent claims completion |
| 12 | CHALLENGE_ASSUMPTIONS | Review assumptions about implementation completeness | Share: "You assume all requirements are met — I checked the commits for requirement [N] and [confirmed/found gap]. Update your assessment if needed." | Agent must confirm |
| 13 | JUSTIFICATION_PASSED | All checks pass — send JUSTIFICATION_PASSED with `--no-expect-response` | Agent may now return final result |

## Red Flags

- Agent says "all tickets completed successfully" but ticket results show failures
- No mention of worktree commits or actual code changes
- Agent's summary describes work that doesn't match the ticket results
- COMPLETE decision with known failed tickets and no follow-up items
- Route-back without specifying exactly which tickets/gaps need attention
- Agent sets ROUTE_BACK without first raising interrupt (violates protocol)
- Follow-ups are generic ("improve test coverage") rather than specific ("add test for X in file Y")
- Agent's justification has no result preview — only reasoning
