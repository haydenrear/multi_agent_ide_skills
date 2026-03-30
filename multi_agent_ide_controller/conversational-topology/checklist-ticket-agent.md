# Ticket Agent Review Checklist

Review criteria for ticket agent output at the tickets->completion gate. Ticket agents implement the actual code changes.

## Common Failure Modes

1. **Cosmetic-only changes**: Agent makes formatting/naming changes without functional impact
2. **Incomplete implementation**: Agent implements the easy parts and skips edge cases
3. **Missing exhaustive switch updates**: New enum values or sealed interface subtypes not added to all switch expressions
4. **Collateral damage**: Changes to shared code break unrelated functionality
5. **Test gap**: Changes made without corresponding test updates

## ACTION Table

| Step | ACTION | Description | Gate |
|------|--------|-------------|------|
| 1 | READ_DIFF | Read the actual diff, not just the agent's summary | MUST review every changed file |
| 2 | CHECK_COMPLETENESS | Verify the diff addresses the ticket's stated goal | FAIL if ticket goal not fully addressed |
| 3 | VERIFY_CORRECTNESS | Check that changes are semantically correct, not just syntactically valid | FAIL if logic errors found |
| 4 | CHECK_EXHAUSTIVE_SWITCHES | If new types/enums added, verify all switch expressions updated | FAIL if any switch missing the new case |
| 5 | CHECK_SEALED_PERMITS | If new subtypes added, verify sealed interface `permits` clause updated | FAIL if permits not updated |
| 6 | VERIFY_TESTS | Check that tests were added/updated for changed behavior | WARN if no test changes for functional changes |
| 7 | CHECK_COLLATERAL | Review files changed that weren't in the ticket scope | ESCALATE if unrelated changes found |
| 8 | VERIFY_COMPILATION | Confirm the code compiles after changes | FAIL if compilation errors |
| 9 | CHECK_SCHEMA_MIGRATION | If JPA entities changed, verify Liquibase changelog updated | FAIL if DB columns added without changeset |
| 10 | JUSTIFICATION_PASSED | All checks pass — send JUSTIFICATION_PASSED with `--no-expect-response` | Agent may now return final result |

## Justification Questions to Ask

When the ticket agent calls `callController` for justification:

- "Why did you change file X? It wasn't in the ticket scope."
- "Show me the specific line where requirement N is addressed."
- "Did you update all exhaustive switches for the new type?"
- "What test covers this new behavior?"
- "This change modifies a shared interface - what's the impact on other consumers?"
- "Why did you choose approach X over approach Y?"

## Red Flags

- Diff is mostly whitespace, import reordering, or comment changes
- Agent claims "straightforward change" but diff touches > 10 files
- New public methods without any test coverage
- Changes to `AgentModels.java` sealed interfaces without corresponding switch updates
- Database entity changes without Liquibase changesets
- Agent summary describes more changes than the diff contains
- `@SuppressWarnings` or `// TODO` added without explanation
