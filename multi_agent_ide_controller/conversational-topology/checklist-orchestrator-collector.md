# Orchestrator Collector Review Checklist

Review criteria for the orchestrator collector agent. This is the final consolidation step — it validates whether the entire workflow (discovery, planning, tickets) is complete against the stated goal.

## Common Failure Modes

1. **Premature ADVANCE_PHASE**: Agent marks workflow COMPLETE without verifying ticket results against the original goal
2. **Shallow validation**: Agent checks that tickets ran but not that the code changes actually address requirements
3. **Missing route-back assessment**: Agent never considers whether gaps exist that warrant re-running earlier phases
4. **Lost context**: Agent's consolidated output drops important findings from earlier phases
5. **Merge-skip**: Agent advances to COMPLETE without verifying worktree merges succeeded

## ACTION Table

| Step | ACTION | Description | Gate |
|------|--------|-------------|------|
| 1 | EXTRACT_REQUIREMENTS | Re-read the original goal and enumerate requirements | MUST match the goal text exactly |
| 2 | VERIFY_PHASE_COMPLETION | Confirm discovery, planning, and ticket phases all ran | FAIL if any phase was skipped |
| 3 | MAP_TICKET_RESULTS | For each requirement, identify which ticket(s) addressed it | FAIL if any requirement has no ticket coverage |
| 4 | CHECK_MERGE_STATUS | Verify worktree merges completed successfully | FAIL if unmerged worktrees remain |
| 5 | VALIDATE_CONSOLIDATED_OUTPUT | Check that the consolidated output accurately reflects all phase results | FAIL if output contradicts or omits phase findings |
| 6 | ASSESS_ROUTE_BACK | If agent proposes ROUTE_BACK, verify the gaps are real and specific | ESCALATE if route-back reason is vague |
| 7 | CHECK_DECISION_TYPE | Verify decisionType matches the actual state (ADVANCE_PHASE vs ROUTE_BACK) | FAIL if marking COMPLETE with known gaps |
| 8 | JUSTIFICATION_PASSED | All checks pass — send JUSTIFICATION_PASSED with `--no-expect-response` | Agent may now return final result |

## Justification Questions to Ask

When the orchestrator collector calls `callController` for justification:

- "Which requirements from the original goal are fully addressed by ticket results?"
- "Are there any requirements that were partially or not addressed?"
- "Did all worktree merges succeed? Were there any conflicts?"
- "Why are you marking this COMPLETE — what evidence supports full goal completion?"
- "You're proposing ROUTE_BACK — what specific gaps need to be addressed?"
- "Does the consolidated output accurately reflect what was actually implemented?"

## Red Flags

- Agent sets ADVANCE_PHASE to COMPLETE but ticket results show failures
- Consolidated output is much shorter than the combined phase outputs
- Agent doesn't mention merge status at all
- Route-back proposal lacks specific gap descriptions
- Agent claims completion but references work that hasn't been done
- COMPLETE decision made without reviewing the actual diff/commits
