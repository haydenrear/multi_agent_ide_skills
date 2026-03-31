# Orchestrator Collector Review Checklist

Review criteria for the orchestrator collector agent. This is the final consolidation step — it validates whether the entire workflow (discovery, planning, tickets) is complete against the stated goal.

## Core Protocol: Research Before Judging

For every ACTION below, you MUST:
1. **Research the relevant sources yourself** before evaluating the agent's claims
2. **Share your findings** with the agent — especially discrepancies or things the agent missed
3. **Ask the agent to confirm**: acknowledge your insights, update its proposed result, or justify its original position
4. **Wait for the agent's response** before progressing to the next ACTION

## Common Failure Modes

1. **Premature ADVANCE_PHASE**: Agent marks workflow COMPLETE without verifying ticket results against the original goal
2. **Shallow validation**: Agent checks that tickets ran but not that the code changes actually address requirements
3. **Missing route-back assessment**: Agent never considers whether gaps exist that warrant re-running earlier phases
4. **Lost context**: Agent's consolidated output drops important findings from earlier phases
5. **Merge-skip**: Agent advances to COMPLETE without verifying worktree merges succeeded

## ACTION Table

| Step | ACTION | What YOU (controller) Research | What to Tell the Agent | Gate |
|------|--------|-------------------------------|----------------------|------|
| 1 | EXTRACT_REQUIREMENTS | Re-read the original goal and enumerate requirements yourself | Share your numbered requirements list and ask: "Confirm these are the requirements you're validating completion against" | MUST match the goal text exactly |
| 2 | VERIFY_RESULT_PREVIEW | Check that the justification previews the consolidated output, decision type, and requirement coverage | If missing: "I need to see your consolidated output structure, ADVANCE/ROUTE_BACK decision, and which requirements you consider fully addressed" | FAIL if no result preview |
| 3 | RESEARCH_PHASE_RESULTS | Read the actual results from each phase yourself — discovery findings, finalized tickets, ticket execution outcomes | Share: "I reviewed all phase results. Discovery found [X]. Planning produced [N tickets]. Ticket execution: [M passed, K failed]. Your consolidated output — does it accurately reflect this?" | Conversation starter — agent must respond |
| 4 | VERIFY_PHASE_COMPLETION | After the agent responds, confirm discovery, planning, and ticket phases all ran | FAIL if any phase was skipped |
| 5 | RESEARCH_REQUIREMENT_FULFILLMENT | For each requirement, trace through ticket results and worktree commits to verify actual implementation | Share: "For requirement [N], I traced ticket [T-X] to its commit and [the implementation covers it / it's only partially done / the key piece is missing]. For requirement [M], I don't see any ticket that addresses it." | Conversation starter — agent must respond |
| 6 | MAP_TICKET_RESULTS | After hearing the agent's response, verify each requirement has ticket coverage | FAIL if any requirement has no ticket coverage |
| 7 | CHECK_MERGE_STATUS | Verify worktree merges completed successfully — check for unmerged branches | FAIL if unmerged worktrees remain |
| 8 | VALIDATE_CONSOLIDATED_OUTPUT | Check that the consolidated output accurately reflects all phase results | FAIL if output contradicts or omits phase findings |
| 9 | ASSESS_ROUTE_BACK | If agent proposes ROUTE_BACK, verify the gaps are real and specific | ESCALATE if route-back reason is vague |
| 10 | CHECK_DECISION_TYPE | Verify decisionType matches the actual state | FAIL if marking COMPLETE with known gaps |
| 11 | INJECT_RESEARCH | Share your independent codebase research findings — file locations, code details, corrections to the agent's assumptions | Share all findings and corrections. Ask: "Confirm you've received these findings and update your proposed result if needed." | Agent must confirm receipt and integrate |
| 12 | CHALLENGE_ASSUMPTIONS | Review assumptions about goal completion — check the actual code state | Share: "You assume the goal is fully met. I checked [specific area] and [confirmed/found that requirement N is not fully addressed]. Update your decision if needed." | Agent must confirm |
| 13 | JUSTIFICATION_PASSED | All checks pass — send JUSTIFICATION_PASSED with `--no-expect-response`. Do NOT include new information — only approval. | Agent returns final structured result |

## Red Flags

- Agent sets ADVANCE_PHASE to COMPLETE but ticket results show failures
- Consolidated output is much shorter than the combined phase outputs
- Agent doesn't mention merge status at all
- Route-back proposal lacks specific gap descriptions
- Agent claims completion but references work that hasn't been done
- COMPLETE decision made without reviewing the actual diff/commits
- Agent's justification has no result preview — only reasoning
