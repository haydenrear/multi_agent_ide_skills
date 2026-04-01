# Discovery Orchestrator Review Checklist

Review criteria for the discovery orchestrator agent. This agent decomposes the goal into discovery agent requests, controlling fan-out and scope coordination.

## Core Protocol: Research Before Judging

For every ACTION below, you MUST:
1. **Research the relevant sources yourself** before evaluating the agent's claims
2. **Share your findings** with the agent — especially discrepancies or things the agent missed
3. **Ask the agent to confirm**: acknowledge your insights, update its proposed result, or justify its original position
4. **Wait for the agent's response** before progressing to the next ACTION

## Common Failure Modes

1. **Over-fan-out**: Agent splits discovery into many overlapping requests when one would suffice
2. **Under-scoping**: Agent creates a single discovery request that doesn't cover the full goal
3. **Scope overlap**: Multiple discovery agents search the same files/areas without differentiation
4. **Missing sequential ordering**: Agent doesn't order foundational discovery before higher-level discovery
5. **Goal drift**: Discovery requests address a reinterpretation of the goal rather than the actual goal

## ACTION Table

| Step | ACTION | What YOU (controller) Research | What to Tell the Agent | Gate |
|------|--------|-------------------------------|----------------------|------|
| 1 | EXTRACT_REQUIREMENTS | Read the original goal text yourself | Share your numbered requirements list and ask: "Confirm these are the discovery objectives you're targeting" | MUST cover all aspects of the goal |
| 2 | VERIFY_RESULT_PREVIEW | Check that the justification includes concrete dispatch plan | If missing: "I need to see the specific agents you plan to dispatch — count, scope per agent, ordering, goal text per agent" | FAIL if no result preview |
| 3 | RESEARCH_CODEBASE_STRUCTURE | Explore the codebase structure yourself — package layout, module boundaries, subsystem divisions | Share: "The codebase has [N subsystems/modules]. Your fan-out of [M] agents — does the split align with actual module boundaries or are you splitting within a single module?" | Conversation starter — agent must respond |
| 4 | VERIFY_FAN_OUT | After the agent responds, assess whether agent count is justified | FAIL if >1 agent without delegation rationale |
| 5 | CHECK_SCOPE_PARTITIONING | Compare each agent's scope against actual codebase boundaries you researched | Share: "Agent A's scope overlaps with Agent B in [area]. How do you plan to handle this?" | FAIL if scope overlaps detected |
| 6 | VALIDATE_ORDERING | Check whether foundational code (models, interfaces, config) is assigned to earlier agents | FAIL if ordering would cause repeated work |
| 7 | CHECK_PRIOR_SUMMARY | If multiple agents, verify later agents receive prior agent context | FAIL if sequential agents lack prior context |
| 8 | VERIFY_GOAL_FIDELITY | Compare discovery request goals with the original goal word-for-word | Share any drift: "The original goal says X but your agent request says Y — is this intentional?" | FAIL if discovery requests address a different problem |
| 9 | INJECT_RESEARCH | Share your independent codebase research findings — file locations, code details, corrections to the agent's assumptions | Share all findings and corrections. Ask: "Confirm you've received these findings and update your proposed result if needed." | Agent must confirm receipt and integrate |
| 10 | CHALLENGE_ASSUMPTIONS | Review assumptions about codebase structure and independence of tracks | Share: "You assumed X and Y are independent — I checked and [they share/don't share] dependencies" | Agent must confirm |
| 11 | USER_CONFIRMATION | **Summarize for the user**: how the orchestrator partitioned discovery work, agent scopes, any overlaps or gaps you found. Present this as a concise summary and wait for the user to explicitly confirm before proceeding. Do NOT send to agent — this is a controller↔user gate. If user rejects, go back to INJECT_RESEARCH with user's feedback. | **HARD GATE — must have user approval** |
| 12 | JUSTIFICATION_PASSED | All checks pass, user approved — send JUSTIFICATION_PASSED with `--no-expect-response`. Do NOT include new information — only approval. | Agent returns final structured result |

## Red Flags

- 3+ discovery agents for a goal that touches a single subsystem
- No delegation rationale provided despite multiple agents
- Discovery requests use identical or near-identical goal descriptions
- No priorAgentSummary in requests that will run after the first
- Discovery requests focus on tangential code areas not related to the goal
- Agent's justification has no result preview — only reasoning
