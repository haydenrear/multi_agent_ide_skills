# Planning Agent Review Checklist

Review criteria for planning agent output at the planning->tickets gate. Planning agents decompose the discovered problem into an implementation plan.

## Core Protocol: Research Before Judging

For every ACTION below, you MUST:
1. **Research the relevant sources yourself** before evaluating the agent's claims
2. **Share your findings** with the agent — especially discrepancies or things the agent missed
3. **Ask the agent to confirm**: acknowledge your insights, update its proposed result, or justify its original position
4. **Wait for the agent's response** before progressing to the next ACTION

## Common Failure Modes

1. **Missing traceability**: Plan items don't trace back to specific requirements
2. **Over-decomposition**: Trivial changes split into many tickets, creating coordination overhead
3. **Under-decomposition**: Complex changes lumped into single tickets that are too large to review
4. **Ordering errors**: Dependencies between tasks not captured, leading to blocked execution
5. **Scope creep**: Plan includes "improvements" not in the original goal
6. **Discovery disconnect**: Plan ignores or contradicts discovery findings

## ACTION Table

| Step | ACTION | What YOU (controller) Research | What to Tell the Agent | Gate |
|------|--------|-------------------------------|----------------------|------|
| 1 | EXTRACT_REQUIREMENTS | Read the original goal text yourself | Share your numbered requirements list and ask: "Confirm these are the requirements your plan addresses" | MUST have all requirements listed |
| 2 | VERIFY_RESULT_PREVIEW | Check that the justification previews the plan structure — ticket count, titles, dependency order | If missing: "I need to see your planned tickets, their dependency order, and which requirements each addresses before I can evaluate" | FAIL if no result preview |
| 3 | RESEARCH_DISCOVERY_ALIGNMENT | Read the discovery output yourself — compare what was discovered against what the agent plans to change | Share: "Discovery found [architecture pattern X] in [area]. Your plan modifies this area but doesn't account for [pattern]. How does your plan handle this?" | Conversation starter — agent must respond |
| 4 | RESEARCH_FILE_PATHS | Open the actual files referenced in the plan — verify they exist and contain what the agent claims | Share: "I checked [file] and it [has/doesn't have] the class/method you reference. Also, [related file] seems relevant but isn't in your plan." | Conversation starter — agent must respond |
| 5 | VERIFY_COVERAGE | After hearing the agent's response, verify each requirement maps to at least one plan item | FAIL if any requirement has no plan item |
| 6 | CHECK_DEPENDENCIES | Trace the dependency chain yourself — open the files and check what imports/extends what | FAIL if a task depends on another task that comes after it |
| 7 | ASSESS_GRANULARITY | For each ticket, count the files it touches and check if they span subsystem boundaries | FAIL if a ticket touches > 5 files or spans multiple subsystems without justification |
| 8 | VERIFY_SCOPE | All plan items must trace to the original goal — flag any "refactor" or "clean up" tasks | Share: "Ticket N says 'refactor X' — I don't see this in the goal. Is this necessary for the goal or is it scope creep?" | ESCALATE if plan includes work not in the goal |
| 9 | CHECK_TEST_STRATEGY | Verify the plan includes verification steps for each ticket | WARN if no test strategy mentioned |
| 10 | INJECT_RESEARCH | Share your independent codebase research findings — file locations, code details, corrections to the agent's assumptions | Share all findings and corrections. Ask: "Confirm you've received these findings and update your proposed result if needed." | Agent must confirm receipt and integrate |
| 11 | CHALLENGE_ASSUMPTIONS | Review the assumptions the agent listed — check each against the actual codebase | Share: "You assume [X about the codebase]. I checked and [confirmed/found otherwise]. Update your plan if needed." | Agent must confirm |
| 12 | USER_CONFIRMATION | **Summarize for the user**: the proposed tickets — count, scope of each, dependency order, test strategy, any concerns about granularity or missing coverage. Present this as a concise summary and wait for the user to explicitly confirm before proceeding. Do NOT send to agent — this is a controller↔user gate. If user rejects, go back to INJECT_RESEARCH with user's feedback. | **HARD GATE — must have user approval** |
| 13 | JUSTIFICATION_PASSED | All checks pass, user approved — send JUSTIFICATION_PASSED with `--no-expect-response`. Do NOT include new information — only approval. | Agent returns final structured result |

## Red Flags

- Plan items that say "refactor" or "clean up" without tying to a requirement
- Ticket descriptions that are vague ("update the service", "fix the controller")
- No mention of test updates or verification steps
- Plan assumes specific implementation approach without justification
- File paths that don't match the actual project structure
- Circular dependencies between tickets
- Plan contradicts discovery findings about architecture or dependencies
- Agent's justification has no result preview — only reasoning
