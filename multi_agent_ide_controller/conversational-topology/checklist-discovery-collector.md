# Discovery Collector Review Checklist

Review criteria for the discovery collector agent. This agent consolidates discovery findings into a unified discovery document and decides whether to advance to PLANNING or route back for more discovery.

## Core Protocol: Research Before Judging

For every ACTION below, you MUST:
1. **Research the relevant sources yourself** before evaluating the agent's claims
2. **Share your findings** with the agent — especially discrepancies or things the agent missed
3. **Ask the agent to confirm**: acknowledge your insights, update its proposed result, or justify its original position
4. **Wait for the agent's response** before progressing to the next ACTION

## Common Failure Modes

1. **Premature advancement**: Agent advances to PLANNING with insufficient discovery (key modules unexplored)
2. **Unnecessary route-back**: Agent routes back to discovery when findings are adequate
3. **Incomplete unified document**: Agent produces a discovery document missing required sections (architecture, data flow, test patterns, etc.)
4. **Hallucinated findings**: Agent includes architectural claims not supported by any discovery agent's output
5. **Missing route-back review protocol**: Agent sets ROUTE_BACK directly without first raising an interrupt for review

## ACTION Table

| Step | ACTION | What YOU (controller) Research | What to Tell the Agent | Gate |
|------|--------|-------------------------------|----------------------|------|
| 1 | VERIFY_RESULT_PREVIEW | Check that the justification previews the unified document structure and phase decision | If missing: "I need to see your phase decision, document sections, and key recommendations before I can evaluate" | FAIL if no result preview |
| 2 | RESEARCH_DISCOVERY_OUTPUTS | Read the raw discovery agent outputs yourself — compare against the collector's synthesis | Share: "Discovery agent A found [X] but I don't see it in your unified document. Agent B's finding about [Y] seems condensed — is important detail lost?" | Conversation starter — agent must respond |
| 3 | CHECK_DOCUMENT_COMPLETENESS | After the agent responds, verify all required sections present | FAIL if architecture overview, key modules, data flow, integration points, or test patterns missing |
| 4 | VALIDATE_FINDINGS_SOURCE | Every claim in the document must trace to a discovery agent result | FAIL if findings present that no agent reported |
| 5 | RESEARCH_COVERAGE_GAPS | For each goal requirement, check whether the discovery findings actually cover it — look at the codebase yourself for areas that should have been discovered | Share: "For requirement N, the discovery found [X] but I also see [Y area] in the codebase that seems relevant and wasn't explored. Does this affect your phase decision?" | Conversation starter — agent must respond |
| 6 | ASSESS_COVERAGE | After hearing the agent's response, map each requirement to findings | FAIL if any requirement has zero discovery coverage |
| 7 | VERIFY_DECISION_TYPE | Check that ADVANCE_PHASE or ROUTE_BACK matches the actual state of findings | FAIL if advancing with known gaps or routing back with comprehensive findings |
| 8 | CHECK_ROUTE_BACK_PROTOCOL | If ROUTE_BACK, verify agent raised interrupt first | FAIL if ROUTE_BACK set without prior interrupt/review |
| 9 | VALIDATE_REQUESTED_PHASE | If advancing, requestedPhase must be "PLANNING" | FAIL if advancing to wrong phase |
| 10 | INJECT_RESEARCH | Share your independent codebase research findings — file locations, code details, corrections to the agent's assumptions | Share all findings and corrections. Ask: "Confirm you've received these findings and update your proposed result if needed." | Agent must confirm receipt and integrate |
| 11 | CHALLENGE_ASSUMPTIONS | Review assumptions about discovery completeness | Share: "You assume discovery is sufficient for planning — I checked [area] and [found gap/confirmed coverage]. Update if needed." | Agent must confirm |
| 12 | USER_CONFIRMATION | **Summarize for the user**: the collector's decision (ADVANCE_PHASE or ROUTE_BACK), consolidated discovery findings, coverage assessment, any gaps. Present this as a concise summary and wait for the user to explicitly confirm before proceeding. Do NOT send to agent — this is a controller↔user gate. If user rejects, go back to INJECT_RESEARCH with user's feedback. | **HARD GATE — must have user approval** |
| 13 | JUSTIFICATION_PASSED | All checks pass, user approved — send JUSTIFICATION_PASSED with `--no-expect-response`. Do NOT include new information — only approval. | Agent returns final structured result |

## Red Flags

- Unified document has empty or one-sentence sections
- Agent claims "comprehensive discovery" but only 2-3 files were explored
- ADVANCE_PHASE set but unifiedCodeMap or recommendations are empty
- Agent sets ROUTE_BACK without first raising interrupt (violates protocol)
- Discovery document includes code patterns or file paths that don't exist
- requestedPhase is anything other than "PLANNING" when advancing
- Agent's justification has no result preview — only reasoning
