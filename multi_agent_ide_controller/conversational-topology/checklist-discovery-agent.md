# Discovery Agent Review Checklist

Review criteria for discovery agent output at the discovery->planning gate. Discovery agents explore the codebase to understand the problem space.

## Common Failure Modes

1. **Pattern matching instead of understanding**: Agent finds files by keyword match but doesn't understand their architectural role
2. **Scope narrowing**: Agent finds the first relevant file and stops exploring, missing related code
3. **Goal reinterpretation**: Agent addresses a related-but-different problem than what was asked
4. **Surface-level analysis**: Agent describes what code does but not how it interconnects

## ACTION Table

| Step | ACTION | Description | Gate |
|------|--------|-------------|------|
| 1 | EXTRACT_REQUIREMENTS | Parse the goal into numbered requirements | MUST have all requirements listed |
| 2 | VERIFY_SCOPE | For each requirement, check that the agent searched broadly enough | FAIL if agent only searched 1-2 files for a cross-cutting requirement |
| 3 | CHECK_ARCHITECTURE | Verify agent identified architectural dependencies (interfaces, abstractions, call chains) | FAIL if only concrete classes found, no interfaces/abstractions |
| 4 | VALIDATE_FINDINGS | Cross-reference agent's claims against actual codebase state | FAIL if agent claims exist that can't be verified |
| 5 | ASSESS_COMPLETENESS | Map each finding back to a requirement | FAIL if any requirement has zero findings |
| 6 | CHECK_INTERPRETATION | Compare agent's interpretation of the goal with the original intent | FAIL if agent solved a different problem |
| 7 | FLAG_GAPS | List any requirements without adequate coverage | ESCALATE to user if gaps found |

## Justification Questions to Ask

When the discovery agent calls `callController` for justification:

- "Which specific files did you examine for requirement N?"
- "What architectural patterns did you identify that connect these components?"
- "Are there other modules that might be affected by this change?"
- "Why did you focus on X instead of Y?" (when the focus seems narrow)
- "What would break if we changed the code in the way you suggest?"

## Red Flags

- Agent says "I found the relevant code" but only lists 1-2 files for a system-wide change
- Agent describes syntax/structure but not behavior or contracts
- Agent's findings don't mention interfaces, abstractions, or extension points
- Agent claims "this is straightforward" for a change touching multiple subsystems
- Discovery output is shorter than the goal description
