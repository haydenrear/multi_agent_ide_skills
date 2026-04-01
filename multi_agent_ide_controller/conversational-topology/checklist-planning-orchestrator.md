# Planning Orchestrator Review Checklist

Review criteria for the planning orchestrator agent. This agent decomposes the goal into planning agent requests based on discovery results, controlling fan-out and scope.

## Core Protocol: Research Before Judging

For every ACTION below, you MUST:
1. **Research the relevant sources yourself** before evaluating the agent's claims
2. **Share your findings** with the agent — especially discrepancies or things the agent missed
3. **Ask the agent to confirm**: acknowledge your insights, update its proposed result, or justify its original position
4. **Wait for the agent's response** before progressing to the next ACTION

## Common Failure Modes

1. **Over-fan-out**: Agent creates multiple planning requests when the goal is a single implementation track
2. **Ignoring discovery findings**: Agent plans without referencing the discovery output
3. **Scope drift**: Planning requests include work not in the original goal
4. **Missing implementation tracks**: Agent omits a planning request for a requirement identified during discovery
5. **Non-structured output**: Agent tries to write files or use tools instead of returning structured PlanningAgentRequests

## ACTION Table

| Step | ACTION | What YOU (controller) Research | What to Tell the Agent | Gate |
|------|--------|-------------------------------|----------------------|------|
| 1 | EXTRACT_REQUIREMENTS | Read the original goal text yourself | Share your numbered requirements list and ask: "Confirm these are the requirements you're planning for" | MUST cover all aspects of the goal |
| 2 | VERIFY_RESULT_PREVIEW | Check that the justification previews the planning dispatch — agent count, scope per agent, ordering | If missing: "I need to see the specific planning agents you'll dispatch — count, scope per agent, which discovery findings each uses" | FAIL if no result preview |
| 3 | RESEARCH_DISCOVERY_OUTPUT | Read the unified discovery document yourself — note key findings, module boundaries, and recommendations | Share: "Discovery identified [N modules/subsystems] and recommended [approach]. Your fan-out of [M] planning agents — does this align with the discovered architecture?" | Conversation starter — agent must respond |
| 4 | VERIFY_DISCOVERY_USAGE | After the agent responds, check that each planning request references specific discovery findings | FAIL if planning ignores discovery output |
| 5 | CHECK_FAN_OUT | Assess whether agent count is justified by the discovered architecture | FAIL if >1 agent without delegation rationale |
| 6 | CHECK_SCOPE_BOUNDARIES | Compare each agent's scope against the discovered module boundaries | Share: "Planning agent A's scope overlaps with agent B in [area discovered by discovery]. How will you prevent duplicate work?" | FAIL if scope overlaps between planning agents |
| 7 | VERIFY_STRUCTURED_OUTPUT | Confirm agent returns structured PlanningAgentRequests, not file writes | FAIL if agent attempts to write files |
| 8 | VALIDATE_INDEPENDENCE | If multiple agents, verify each track can be planned independently based on discovery findings | FAIL if tracks have implicit cross-dependencies |
| 9 | INJECT_RESEARCH | Share your independent codebase research findings — file locations, code details, corrections to the agent's assumptions | Share all findings and corrections. Ask: "Confirm you've received these findings and update your proposed result if needed." | Agent must confirm receipt and integrate |
| 10 | CHALLENGE_ASSUMPTIONS | Review assumptions about implementation track independence — check the discovered dependencies | Share: "You assume tracks A and B are independent — discovery found [shared dependency]. Does this change your decomposition?" | Agent must confirm |
| 11 | USER_CONFIRMATION | **Summarize for the user**: the orchestrator's decomposition — how many planning agents, scope of each, any overlaps or independence concerns. Present this as a concise summary and wait for the user to explicitly confirm before proceeding. Do NOT send to agent — this is a controller↔user gate. If user rejects, go back to INJECT_RESEARCH with user's feedback. | **HARD GATE — must have user approval** |
| 12 | JUSTIFICATION_PASSED | All checks pass, user approved — send JUSTIFICATION_PASSED with `--no-expect-response`. Do NOT include new information — only approval. | Agent returns final structured result |

## Red Flags

- Planning requests don't reference any specific discovery findings
- Agent creates planning tracks that mirror discovery agent splits rather than implementation tracks
- Planning requests include "refactor" or "improve" work not in the original goal
- Agent produces file outputs instead of structured PlanningAgentRequests
- Multiple planning agents assigned to the same subsystem
- Agent's justification has no result preview — only reasoning
