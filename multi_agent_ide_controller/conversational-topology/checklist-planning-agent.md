# Planning Agent Review Checklist

Review criteria for planning agent output at the planning->tickets gate. Planning agents decompose the discovered problem into an implementation plan.

## Common Failure Modes

1. **Missing traceability**: Plan items don't trace back to specific requirements
2. **Over-decomposition**: Trivial changes split into many tickets, creating coordination overhead
3. **Under-decomposition**: Complex changes lumped into single tickets that are too large to review
4. **Ordering errors**: Dependencies between tasks not captured, leading to blocked execution
5. **Scope creep**: Plan includes "improvements" not in the original goal

## ACTION Table

| Step | ACTION | Description | Gate |
|------|--------|-------------|------|
| 1 | MAP_TO_REQUIREMENTS | For each plan item, identify which requirement(s) it serves | FAIL if any plan item has no requirement mapping |
| 2 | VERIFY_COVERAGE | For each requirement, verify at least one plan item addresses it | FAIL if any requirement has no plan item |
| 3 | CHECK_DEPENDENCIES | Verify plan items are ordered correctly (dependencies before dependents) | FAIL if a task depends on another task that comes after it |
| 4 | ASSESS_GRANULARITY | Each ticket should be a single reviewable unit of work | FAIL if a ticket touches > 5 files or spans multiple subsystems |
| 5 | VERIFY_SCOPE | All plan items must trace to the original goal | ESCALATE if plan includes work not in the goal |
| 6 | CHECK_TEST_STRATEGY | Plan should specify how changes will be verified | WARN if no test strategy mentioned |
| 7 | VALIDATE_FILE_PATHS | File paths in the plan must exist in the codebase | FAIL if plan references nonexistent files |
| 8 | JUSTIFICATION_PASSED | All checks pass — send JUSTIFICATION_PASSED with `--no-expect-response` | Agent may now return final result |

## Justification Questions to Ask

When the planning agent calls `callController` for justification:

- "How does ticket N map to requirement M from the goal?"
- "Why did you split X into N separate tickets instead of handling it as one?"
- "What is the dependency order between these tickets?"
- "This ticket touches files in multiple subsystems - should it be split?"
- "Is this task (X) part of the original goal, or is it an improvement you identified?"
- "What's your test strategy for verifying ticket N?"

## Red Flags

- Plan items that say "refactor" or "clean up" without tying to a requirement
- Ticket descriptions that are vague ("update the service", "fix the controller")
- No mention of test updates or verification steps
- Plan assumes specific implementation approach without justification
- File paths that don't match the actual project structure
- Circular dependencies between tickets
