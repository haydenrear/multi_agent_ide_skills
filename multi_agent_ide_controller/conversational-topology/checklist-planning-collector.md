# Planning Collector Review Checklist

Review criteria for the planning collector agent. This agent finalizes tickets, dependency graphs, and consolidated output, then decides whether to advance to TICKETS or route back for more planning.

## Core Protocol: Research Before Judging

For every ACTION below, you MUST:
1. **Research the relevant sources yourself** before evaluating the agent's claims
2. **Share your findings** with the agent — especially discrepancies or things the agent missed
3. **Ask the agent to confirm**: acknowledge your insights, update its proposed result, or justify its original position
4. **Wait for the agent's response** before progressing to the next ACTION

## Common Failure Modes

1. **Ticket bloat**: Agent creates excessive tickets for simple changes, adding coordination overhead
2. **Missing dependencies**: Agent doesn't capture ordering constraints between tickets
3. **Vague ticket descriptions**: Tickets lack specific file paths, tasks, or acceptance criteria
4. **Premature advancement**: Agent advances to TICKETS with incomplete or contradictory plans
5. **Non-structured output**: Agent writes files instead of returning structured PlanningCollectorResult
6. **Missing route-back review protocol**: Agent sets ROUTE_BACK directly without first raising an interrupt for review

## ACTION Table

| Step | ACTION | What YOU (controller) Research | What to Tell the Agent | Gate |
|------|--------|-------------------------------|----------------------|------|
| 1 | VERIFY_RESULT_PREVIEW | Check that the justification previews finalized tickets, dependency graph, and phase decision | If missing: "I need to see your finalized ticket list, dependency graph, and ADVANCE/ROUTE_BACK decision before I can evaluate" | FAIL if no result preview |
| 2 | RESEARCH_PLANNING_OUTPUTS | Read each planning agent's raw output yourself — compare ticket proposals against the collector's finalized list | Share: "Planning agent A proposed [ticket X] but I don't see it in your finalized list. Agent B's ticket about [Y] seems merged with [Z] — is important detail lost?" | Conversation starter — agent must respond |
| 3 | CHECK_TICKET_COMPLETENESS | After the agent responds, verify each finalized ticket has ticketId, title, description, tasks, and acceptanceCriteria | FAIL if required fields missing |
| 4 | RESEARCH_DEPENDENCY_CHAIN | Open the actual files referenced by tickets and trace imports/dependencies yourself | Share: "Ticket T-002 modifies [interface X] which Ticket T-003 depends on, but your dependency graph doesn't capture this. Should T-002 be a prerequisite?" | Conversation starter — agent must respond |
| 5 | CHECK_DEPENDENCY_GRAPH | After hearing the agent's response, verify the graph captures all real ordering constraints | FAIL if tickets have implicit dependencies not in the graph |
| 6 | MAP_TO_REQUIREMENTS | For each original goal requirement, verify at least one finalized ticket addresses it | FAIL if requirements have no ticket coverage |
| 7 | ASSESS_GRANULARITY | For each ticket, check file count and subsystem span | WARN if any ticket spans > 5 files or multiple subsystems |
| 8 | VERIFY_STRUCTURED_OUTPUT | Confirm output uses structured fields, not file writes | FAIL if agent writes files instead of returning schema |
| 9 | VALIDATE_DECISION | If ADVANCE_PHASE, requestedPhase must be "TICKETS" | FAIL if advancing to wrong phase |
| 10 | CHECK_ROUTE_BACK_PROTOCOL | If ROUTE_BACK, verify agent raised interrupt first | FAIL if ROUTE_BACK without prior interrupt/review |
| 11 | INJECT_RESEARCH | Share your independent codebase research findings — file locations, code details, corrections to the agent's assumptions | Share all findings and corrections. Ask: "Confirm you've received these findings and update your proposed result if needed." | Agent must confirm receipt and integrate |
| 12 | CHALLENGE_ASSUMPTIONS | Review assumptions about ticket completeness and dependency ordering | Share: "You assume the tickets cover all requirements — I mapped them and [found gap/confirmed coverage]. Update if needed." | Agent must confirm |
| 13 | USER_CONFIRMATION | **Summarize for the user**: the collector's decision (ADVANCE_PHASE or ROUTE_BACK), finalized ticket list, dependency ordering, any gaps or concerns about ticket completeness. Present this as a concise summary and wait for the user to explicitly confirm before proceeding. Do NOT send to agent — this is a controller↔user gate. If user rejects, go back to INJECT_RESEARCH with user's feedback. | **HARD GATE — must have user approval** |
| 14 | JUSTIFICATION_PASSED | All checks pass, user approved — send JUSTIFICATION_PASSED with `--no-expect-response`. Do NOT include new information — only approval. | Agent returns final structured result |

## Red Flags

- finalizedTickets is empty or has only 1 ticket for a multi-requirement goal
- Tickets reference file paths that don't exist in the codebase
- dependencyGraph is empty when tickets clearly have ordering needs
- Agent sets requestedPhase to something other than "TICKETS" when advancing
- Ticket acceptance criteria are just restated requirements, not verifiable conditions
- Agent sets ROUTE_BACK without first raising interrupt (violates protocol)
- Agent's justification has no result preview — only reasoning
