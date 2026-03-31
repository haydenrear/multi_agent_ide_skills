# Orchestrator Review Checklist

Review criteria for the top-level orchestrator agent. The orchestrator routes the goal to discovery orchestrator, orchestrator collector, or interrupt. It is the entry point for all workflows.

## Core Protocol: Research Before Judging

For every ACTION below, you MUST:
1. **Research the relevant sources yourself** before evaluating the agent's claims
2. **Share your findings** with the agent — especially discrepancies or things the agent missed
3. **Ask the agent to confirm**: acknowledge your insights, update its proposed result, or justify its original position
4. **Wait for the agent's response** before progressing to the next ACTION

## Common Failure Modes

1. **Skipping to collector**: Agent routes directly to orchestrator collector without running discovery/planning/tickets
2. **Goal reinterpretation**: Agent rewrites or narrows the goal before passing it downstream
3. **Premature completion**: Agent assumes prior phase results are sufficient without verifying
4. **Missing phase awareness**: Agent ignores the current phase and re-routes to discovery when planning or tickets are already underway

## ACTION Table

| Step | ACTION | What YOU (controller) Research | What to Tell the Agent | Gate |
|------|--------|-------------------------------|----------------------|------|
| 1 | EXTRACT_GOAL | Parse the original goal text into numbered requirements yourself | Share your numbered requirements list and ask: "Confirm these are the requirements you're routing for" | MUST have all requirements listed |
| 2 | VERIFY_RESULT_PREVIEW | Check that the justification previews the routing decision, target, and goal text being passed | If missing: "I need to see your routing target, the goal text you're passing, and why this routing decision is correct for the current phase" | FAIL if no result preview |
| 3 | RESEARCH_PHASE_STATE | Check the workflow's current phase yourself — what phases have completed, what results exist | Share: "I see the workflow is in [phase] with [discovery/planning/ticket] results available. Your routing to [target] — does this match the workflow state?" | Conversation starter — agent must respond |
| 4 | VERIFY_ROUTING | After the agent responds, check that the routing decision matches the current phase | FAIL if routing to discovery when phase is PLANNING or TICKETS |
| 5 | CHECK_GOAL_FIDELITY | Compare the goal text passed downstream with the original word-for-word | FAIL if goal was narrowed, reworded, or requirements dropped |
| 6 | VALIDATE_PHASE_PROGRESSION | Verify the orchestrator is advancing the workflow, not looping | FAIL if same routing decision made 3+ times without progress |
| 7 | RESEARCH_COLLECTOR_READINESS | If routing to collector, check all phase results yourself — discovery findings, finalized tickets, ticket execution results | Share: "You're routing to collector. I checked: discovery [complete/incomplete], planning [N tickets finalized], tickets [M completed, K failed]. Is this sufficient for completion?" | Conversation starter — agent must respond |
| 8 | CHECK_COLLECTOR_READINESS | After the agent responds, verify all phases completed before collector routing | FAIL if routing to collector with incomplete phases |
| 9 | ASSESS_INTERRUPT_JUSTIFICATION | If routing to interrupt, verify the reason is legitimate and specific | ESCALATE if interrupt seems like stalling rather than genuine ambiguity |
| 10 | INJECT_RESEARCH | Share your independent codebase research findings — file locations, code details, corrections to the agent's assumptions | Share all findings and corrections. Ask: "Confirm you've received these findings and update your proposed result if needed." | Agent must confirm receipt and integrate |
| 11 | CHALLENGE_ASSUMPTIONS | Review assumptions about workflow state and readiness | Share: "You assume [phase X] is complete — I checked the results and [confirmed/found gap]. Update your routing if needed." | Agent must confirm |
| 12 | JUSTIFICATION_PASSED | All checks pass — send JUSTIFICATION_PASSED with `--no-expect-response`. Do NOT include new information — only approval. | Agent returns final structured result |

## Red Flags

- Orchestrator routes to collector on the first invocation (skipping all work)
- Goal text passed to discovery orchestrator is different from the original goal
- Orchestrator loops between discovery and itself without advancing
- Phase is TICKETS but orchestrator routes back to discovery without interrupt/review
- Orchestrator claims "workflow complete" but no ticket results exist
- Agent's justification has no result preview — only reasoning
