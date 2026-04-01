# Ticket Orchestrator Review Checklist

Review criteria for the ticket orchestrator agent. This agent translates the finalized plan into ticket agent requests — one per ticket — submitted all at once.

## Core Protocol: Research Before Judging

For every ACTION below, you MUST:
1. **Research the relevant sources yourself** before evaluating the agent's claims
2. **Share your findings** with the agent — especially discrepancies or things the agent missed
3. **Ask the agent to confirm**: acknowledge your insights, update its proposed result, or justify its original position
4. **Wait for the agent's response** before progressing to the next ACTION

## Common Failure Modes

1. **Ticket count mismatch**: Agent creates more or fewer requests than tickets in the plan
2. **Ticket merging/splitting**: Agent collapses multiple tickets into one or splits one into many
3. **Incomplete ticket context**: Agent doesn't include enough detail (ticketId, title, description, tasks, acceptance criteria, file refs) for the ticket agent to work independently
4. **Back-referencing**: Agent tells ticket agents to "see ticket X" instead of including full context in each request
5. **Ordering errors**: Agent doesn't respect the dependency graph when ordering requests

## ACTION Table

| Step | ACTION | What YOU (controller) Research | What to Tell the Agent | Gate |
|------|--------|-------------------------------|----------------------|------|
| 1 | VERIFY_RESULT_PREVIEW | Check that the justification previews the dispatch plan — request count, ticket-to-request mapping, ordering | If missing: "I need to see how many requests you're dispatching, which ticket each maps to, and the execution order" | FAIL if no result preview |
| 2 | RESEARCH_FINALIZED_PLAN | Read the finalized tickets and dependency graph from the planning collector output yourself | Share: "The plan has [N] finalized tickets with dependency order [X→Y→Z]. Your dispatch has [M] requests — does this match? I notice ticket [T] is missing from your requests." | Conversation starter — agent must respond |
| 3 | COUNT_MATCH | After the agent responds, verify number of agentRequests equals number of finalized tickets | FAIL if counts don't match |
| 4 | CHECK_1_TO_1 | Each request maps to exactly one ticket, no merging or splitting | FAIL if any request covers multiple tickets or vice versa |
| 5 | RESEARCH_REQUEST_CONTEXT | Read each request's content — check that it includes full ticket detail, not back-references | Share: "Request for ticket [T-003] says 'see ticket T-001 for interface details' — this needs to be self-contained. What interface details should be inlined?" | Conversation starter — agent must respond |
| 6 | VERIFY_SELF_CONTAINED | After the agent responds, confirm each request includes full ticket context | FAIL if any request says "see ticket X" without inline detail |
| 7 | CHECK_REQUIRED_FIELDS | Each request has ticketId, title, description, tasks, acceptance criteria, key file references | FAIL if any required field is missing |
| 8 | VALIDATE_ORDERING | Compare request ordering against the dependency graph | FAIL if dependent ticket comes before its prerequisite |
| 9 | VERIFY_WORKTREE_ASSIGNMENT | If parallel execution, each ticket agent should have worktree context | WARN if worktree assignments are missing for parallel tickets |
| 10 | INJECT_RESEARCH | Share your independent codebase research findings — file locations, code details, corrections to the agent's assumptions | Share all findings and corrections. Ask: "Confirm you've received these findings and update your proposed result if needed." | Agent must confirm receipt and integrate |
| 11 | CHALLENGE_ASSUMPTIONS | Review assumptions about ticket independence and execution order | Share: "You assume tickets [A] and [B] can run in parallel — I checked the files they touch and [they overlap/they're independent]. Confirm?" | Agent must confirm |
| 12 | USER_CONFIRMATION | **Summarize for the user**: the orchestrator's ticket agent requests — how many, execution order, scope of each, any parallel vs sequential decisions. Present this as a concise summary and wait for the user to explicitly confirm before proceeding. Do NOT send to agent — this is a controller↔user gate. If user rejects, go back to INJECT_RESEARCH with user's feedback. | **HARD GATE — must have user approval** |
| 13 | JUSTIFICATION_PASSED | All checks pass, user approved — send JUSTIFICATION_PASSED with `--no-expect-response`. Do NOT include new information — only approval. | Agent returns final structured result |

## Red Flags

- Request count doesn't match finalized ticket count
- Requests contain phrases like "as described in ticket T-001" without inline context
- Agent reinterprets or expands ticket scope beyond what the plan specified
- Dependency-ordered tickets appear in wrong sequence
- Agent creates a "setup" or "cleanup" request not in the original plan
- Ticket descriptions are copy-pasted without adaptation from planning output
- Agent's justification has no result preview — only reasoning
