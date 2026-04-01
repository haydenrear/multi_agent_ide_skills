# Discovery Agent Review Checklist

Review criteria for discovery agent output at the discovery->planning gate. Discovery agents explore the codebase to understand the problem space.

## Core Protocol: Research Before Judging

For every ACTION below, you MUST:
1. **Research the relevant sources yourself** before evaluating the agent's claims
2. **Share your findings** with the agent — especially discrepancies or things the agent missed
3. **Ask the agent to confirm**: acknowledge your insights, update its proposed result, or justify its original position
4. **Wait for the agent's response** before progressing to the next ACTION

## Common Failure Modes

1. **Pattern matching instead of understanding**: Agent finds files by keyword match but doesn't understand their architectural role
2. **Scope narrowing**: Agent finds the first relevant file and stops exploring, missing related code
3. **Goal reinterpretation**: Agent addresses a related-but-different problem than what was asked
4. **Surface-level analysis**: Agent describes what code does but not how it interconnects

## ACTION Table

| Step | ACTION | What YOU (controller) Research | What to Tell the Agent | Gate |
|------|--------|-------------------------------|----------------------|------|
| 1 | EXTRACT_REQUIREMENTS | Read the original goal text yourself | Share your numbered requirements list and ask: "Confirm these are the requirements you're addressing" | MUST have all requirements listed |
| 2 | VERIFY_RESULT_PREVIEW | Check that the justification includes a concrete result preview | If missing: "Your justification describes reasoning but not your proposed result. List the specific findings, files, and report structure you plan to return." | FAIL if no result preview |
| 3 | RESEARCH_SCOPE | Open the codebase yourself. For each requirement, search for relevant files/packages beyond what the agent found | Share what you found: "For requirement N, I also found [files/packages] that seem relevant. Did you examine these? Why or why not?" | Conversation starter — agent must respond |
| 4 | RESEARCH_ARCHITECTURE | Trace the call chains and interface hierarchies the agent claims to have found. Look for abstractions the agent may have missed | Share: "I traced the call chain from X to Y and found [additional interfaces/patterns]. Your findings didn't mention Z — is that intentional?" | Conversation starter — agent must respond |
| 5 | VERIFY_SCOPE | After hearing the agent's response to your research, assess whether the search was broad enough | FAIL if agent only searched 1-2 files for a cross-cutting requirement |
| 6 | CHECK_ARCHITECTURE | After the architecture research conversation, verify agent identified key dependencies | FAIL if only concrete classes found, no interfaces/abstractions |
| 7 | VALIDATE_FINDINGS | Cross-reference agent's claims against actual codebase state using your own research | FAIL if agent claims exist that can't be verified |
| 8 | ASSESS_COMPLETENESS | Map each finding back to a requirement using both your research and the agent's | FAIL if any requirement has zero findings |
| 9 | CHECK_INTERPRETATION | Compare agent's interpretation of the goal with the original intent | FAIL if agent solved a different problem |
| 10 | INJECT_RESEARCH | Share your independent codebase research findings — file locations, code details, corrections to the agent's assumptions | Share all findings and corrections. Ask: "Confirm you've received these findings and update your proposed result if needed." | Agent must confirm receipt and integrate |
| 11 | CHALLENGE_ASSUMPTIONS | Review the assumptions the agent listed and verify each one | Share: "Your assumption about X — I checked and [confirmed/found otherwise]. Update your result accordingly." | Agent must confirm |
| 12 | FLAG_GAPS | List any requirements without adequate coverage | ESCALATE to user if gaps found |
| 13 | USER_CONFIRMATION | **Summarize for the user**: what the agent discovered, key findings, areas explored, any concerns or gaps you identified during review. Present this as a concise summary and wait for the user to explicitly confirm before proceeding. Do NOT send to agent — this is a controller↔user gate. If user rejects, go back to INJECT_RESEARCH with user's feedback. | **HARD GATE — must have user approval** |
| 14 | JUSTIFICATION_PASSED | All checks pass, user approved — send JUSTIFICATION_PASSED with `--no-expect-response`. Do NOT include new information — only approval. | Agent returns final structured result |

## Red Flags

- Agent says "I found the relevant code" but only lists 1-2 files for a system-wide change
- Agent describes syntax/structure but not behavior or contracts
- Agent's findings don't mention interfaces, abstractions, or extension points
- Agent claims "this is straightforward" for a change touching multiple subsystems
- Discovery output is shorter than the goal description
- Agent's justification has no result preview — only reasoning
- Agent doesn't list any assumptions (everyone has assumptions)
