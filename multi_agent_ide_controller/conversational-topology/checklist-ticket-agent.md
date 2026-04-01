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
| 2 | RESEARCH_DIFF | **HARD GATE — you MUST `git diff` every commit the agent made and read every hunk before proceeding.** A `--stat` line count is NOT sufficient. Read the actual code changes: new functions, modified signatures, updated call sites, added parameters. Verify the diff matches the agent's claims. If the agent says it added helper functions, confirm they exist and are correct. If the agent says it updated all call sites, confirm each one. Do NOT approve based on the justification text alone — the diff is the source of truth. | Share: "I read the diff. In [file], you changed [X] but I notice [Y concern]. Also, [file B] wasn't changed but seems to need updating based on your changes to [file A]." | **FAIL if controller did not read full diff** — do not proceed to later steps |
| 3 | CHECK_COMPLETENESS | After hearing the agent's response, verify the diff addresses the ticket's full goal | FAIL if ticket goal not fully addressed |
| 4 | RESEARCH_CORRECTNESS | Trace the logic of each change — follow call chains, check types, verify semantics | Share: "In [method], you pass [X] but the callee expects [Y]. Also, [edge case Z] doesn't seem handled." | Conversation starter — agent must respond |
| 5 | VERIFY_CORRECTNESS | After the agent responds, confirm logic errors are resolved | FAIL if logic errors remain |
| 6 | CHECK_EXHAUSTIVE_SWITCHES | If new types/enums added, search the codebase yourself for all switch expressions on that type | FAIL if any switch missing the new case |
| 7 | CHECK_SEALED_PERMITS | If new subtypes added, verify sealed interface `permits` clause updated | FAIL if permits not updated |
| 8 | RESEARCH_TEST_COVERAGE | Check what tests exist for the changed code — run or read the test files yourself | Share: "I see tests for [existing behavior] but no test covers [new behavior from your changes]. What's your test strategy?" | WARN if no test changes for functional changes |
| 9 | CHECK_COLLATERAL | Review files changed that weren't in the ticket scope | ESCALATE if unrelated changes found |
| 10 | VERIFY_COMPILATION | Confirm the code compiles after changes | FAIL if compilation errors |
| 11 | CHECK_SCHEMA_MIGRATION | If JPA entities changed, verify Liquibase changelog updated | FAIL if DB columns added without changeset |
| 12 | INJECT_RESEARCH | Share your independent codebase research findings — file locations, code details, corrections to the agent's assumptions | Share all findings and corrections. Ask: "Confirm you've received these findings and update your proposed result if needed." | Agent must confirm receipt and integrate |
| 13 | CHALLENGE_ASSUMPTIONS | Review the agent's assumptions about the change's impact | Share: "You assume [X] about [downstream consumers/callers]. I checked and [confirmed/found otherwise]. Update if needed." | Agent must confirm |
| 14 | REQUEST_VALIDATION | After your review is complete, ask the agent to run its own validations — compile, run relevant tests, verify the changes work end-to-end | Tell the agent: "Run validations on your changes: compile the project, run relevant unit/integration tests, and confirm the changes work as expected. Report back with the validation results." | Agent must run validations and call back |
| 15 | REVIEW_VALIDATION | Read the agent's validation results. Check: did tests pass? Did compilation succeed? Are there any warnings or failures the agent glossed over? Cross-check against your own knowledge of the test suite. | If validation gaps: "Your tests passed but you didn't run [X] which covers the code you changed. Run that too." If failures: "Test [X] failed — investigate and fix before proceeding." | FAIL if validations incomplete or failing |
| 16 | USER_CONFIRMATION | Present your full review to the user: what the agent changed, what you verified, what the agent's validations showed, any remaining concerns. Wait for the user to explicitly confirm before proceeding. | Do NOT send to agent — this is a controller↔user gate. If user rejects, go back to INJECT_RESEARCH with user's feedback. | **HARD GATE — must have user approval** |
| 17 | JUSTIFICATION_PASSED | All checks pass, validations confirmed, user approved — send JUSTIFICATION_PASSED with `--no-expect-response`. Do NOT include new information — only approval. | Agent returns final structured result |

## Red Flags

- Diff is mostly whitespace, import reordering, or comment changes
- Agent claims "straightforward change" but diff touches > 10 files
- New public methods without any test coverage
- Changes to `AgentModels.java` sealed interfaces without corresponding switch updates
- Database entity changes without Liquibase changesets
- Agent summary describes more changes than the diff contains
- `@SuppressWarnings` or `// TODO` added without explanation
- Agent's justification has no result preview — only reasoning
- **Controller approved without reading the full diff** — only checked `--stat` line counts or trusted the agent's justification text. This is the most dangerous failure mode: the agent may claim changes were made that don't exist in the diff, or the implementation may be subtly wrong in ways only visible by reading the actual code hunks
