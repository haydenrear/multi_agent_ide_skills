# Ticket Agent Review Checklist

Review criteria for ticket agent output at the tickets->completion gate. Ticket agents implement the actual code changes.

## Core Protocol: Research Before Judging

For every ACTION below, you MUST:
1. **Research the relevant sources yourself** before evaluating the agent's claims
2. **Share your findings** with the agent — especially discrepancies or things the agent missed
3. **Ask the agent to confirm**: acknowledge your insights, update its proposed result, or justify its original position
4. **Wait for the agent's response** before progressing to the next ACTION

## Common Failure Modes

1. **Cosmetic-only changes**: Agent makes formatting/naming changes without functional impact
2. **Incomplete implementation**: Agent implements the easy parts and skips edge cases
3. **Missing exhaustive switch updates**: New enum values or sealed interface subtypes not added to all switch expressions
4. **Collateral damage**: Changes to shared code break unrelated functionality
5. **Test gap**: Changes made without corresponding test updates

## ACTION Table

| Step | ACTION | What YOU (controller) Research | What to Tell the Agent | Gate |
|------|--------|-------------------------------|----------------------|------|
| 1 | VERIFY_RESULT_PREVIEW | Check that the justification previews the specific changes made — files modified, what was added/changed, test results | If missing: "I need to see which files you changed, what you added/modified in each, and whether tests pass before I can evaluate" | FAIL if no result preview |
| 2 | RESEARCH_DIFF | Read the actual diff yourself — every changed file, every hunk | Share: "I read the diff. In [file], you changed [X] but I notice [Y concern]. Also, [file B] wasn't changed but seems to need updating based on your changes to [file A]." | Conversation starter — agent must respond |
| 3 | CHECK_COMPLETENESS | After hearing the agent's response, verify the diff addresses the ticket's full goal | FAIL if ticket goal not fully addressed |
| 4 | RESEARCH_CORRECTNESS | Trace the logic of each change — follow call chains, check types, verify semantics | Share: "In [method], you pass [X] but the callee expects [Y]. Also, [edge case Z] doesn't seem handled." | Conversation starter — agent must respond |
| 5 | VERIFY_CORRECTNESS | After the agent responds, confirm logic errors are resolved | FAIL if logic errors remain |
| 6 | CHECK_EXHAUSTIVE_SWITCHES | If new types/enums added, search the codebase yourself for all switch expressions on that type | FAIL if any switch missing the new case |
| 7 | CHECK_SEALED_PERMITS | If new subtypes added, verify sealed interface `permits` clause updated | FAIL if permits not updated |
| 8 | RESEARCH_TEST_COVERAGE | Check what tests exist for the changed code — run or read the test files yourself | Share: "I see tests for [existing behavior] but no test covers [new behavior from your changes]. What's your test strategy?" | WARN if no test changes for functional changes |
| 9 | CHECK_COLLATERAL | Review files changed that weren't in the ticket scope | ESCALATE if unrelated changes found |
| 10 | VERIFY_COMPILATION | Confirm the code compiles after changes | FAIL if compilation errors |
| 11 | CHECK_SCHEMA_MIGRATION | If JPA entities changed, verify Liquibase changelog updated | FAIL if DB columns added without changeset |
| 12 | CHALLENGE_ASSUMPTIONS | Review the agent's assumptions about the change's impact | Share: "You assume [X] about [downstream consumers/callers]. I checked and [confirmed/found otherwise]. Update if needed." | Agent must confirm |
| 13 | JUSTIFICATION_PASSED | All checks pass — send JUSTIFICATION_PASSED with `--no-expect-response` | Agent may now return final result |

## Red Flags

- Diff is mostly whitespace, import reordering, or comment changes
- Agent claims "straightforward change" but diff touches > 10 files
- New public methods without any test coverage
- Changes to `AgentModels.java` sealed interfaces without corresponding switch updates
- Database entity changes without Liquibase changesets
- Agent summary describes more changes than the diff contains
- `@SuppressWarnings` or `// TODO` added without explanation
- Agent's justification has no result preview — only reasoning
