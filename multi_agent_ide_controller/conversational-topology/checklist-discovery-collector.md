# Discovery Collector Review Checklist

Review criteria for the discovery collector agent. This agent consolidates discovery findings into a unified discovery document and decides whether to advance to PLANNING or route back for more discovery.

## Common Failure Modes

1. **Premature advancement**: Agent advances to PLANNING with insufficient discovery (key modules unexplored)
2. **Unnecessary route-back**: Agent routes back to discovery when findings are adequate
3. **Incomplete unified document**: Agent produces a discovery document missing required sections (architecture, data flow, test patterns, etc.)
4. **Hallucinated findings**: Agent includes architectural claims not supported by any discovery agent's output
5. **Missing route-back review protocol**: Agent sets ROUTE_BACK directly without first raising an interrupt for review

## ACTION Table

| Step | ACTION | Description | Gate |
|------|--------|-------------|------|
| 1 | CHECK_DOCUMENT_COMPLETENESS | Verify unified discovery document has all required sections | FAIL if architecture overview, key modules, data flow, integration points, or test patterns missing |
| 2 | VALIDATE_FINDINGS_SOURCE | Every claim in the document must trace to a discovery agent result | FAIL if findings present that no agent reported |
| 3 | ASSESS_COVERAGE | Map each goal requirement to discovery findings | FAIL if any requirement has zero discovery coverage |
| 4 | VERIFY_DECISION_TYPE | Check that ADVANCE_PHASE or ROUTE_BACK matches the actual state of findings | FAIL if advancing with known gaps or routing back with comprehensive findings |
| 5 | CHECK_ROUTE_BACK_PROTOCOL | If ROUTE_BACK, verify agent raised interrupt first (not direct ROUTE_BACK) | FAIL if ROUTE_BACK set without prior interrupt/review |
| 6 | VALIDATE_REQUESTED_PHASE | If advancing, requestedPhase must be "PLANNING" | FAIL if advancing to wrong phase |
| 7 | JUSTIFICATION_PASSED | All checks pass — send JUSTIFICATION_PASSED with `--no-expect-response` | Agent may now return final result |

## Justification Questions to Ask

When the discovery collector calls `callController` for justification:

- "Which sections of the unified discovery document are you most confident about?"
- "Are there any goal requirements without adequate discovery coverage?"
- "Why are you advancing to PLANNING — is the discovery comprehensive enough to plan against?"
- "You're proposing ROUTE_BACK — what specific areas need more exploration?"
- "Did you include findings about test patterns and conventions?"

## Red Flags

- Unified document has empty or one-sentence sections
- Agent claims "comprehensive discovery" but only 2-3 files were explored
- ADVANCE_PHASE set but unifiedCodeMap or recommendations are empty
- Agent sets ROUTE_BACK without first raising interrupt (violates protocol)
- Discovery document includes code patterns or file paths that don't exist
- requestedPhase is anything other than "PLANNING" when advancing
