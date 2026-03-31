# Planning Dispatch Review Checklist

Review criteria for the planning dispatch agent. This agent routes planning results to the planning collector, synthesizing multiple planning agent outputs into a single collector input.

## Core Protocol: Research Before Judging

For every ACTION below, you MUST:
1. **Research the relevant sources yourself** before evaluating the agent's claims
2. **Share your findings** with the agent — especially discrepancies or things the agent missed
3. **Ask the agent to confirm**: acknowledge your insights, update its proposed result, or justify its original position
4. **Wait for the agent's response** before progressing to the next ACTION

## Common Failure Modes

1. **Lossy consolidation**: Agent drops tickets or implementation details when synthesizing for the collector
2. **Conflicting plans merged**: Agent merges planning outputs without detecting contradictions between agents
3. **Missing context**: Agent doesn't provide enough synthesis for the collector to finalize tickets
4. **Misrouting**: Agent routes away from collector without justification

## ACTION Table

| Step | ACTION | What YOU (controller) Research | What to Tell the Agent | Gate |
|------|--------|-------------------------------|----------------------|------|
| 1 | VERIFY_RESULT_PREVIEW | Check that the justification previews the routing target and synthesis content | If missing: "I need to see your routing target and a summary of what you're forwarding to the collector" | FAIL if no result preview |
| 2 | RESEARCH_RAW_OUTPUTS | Read each planning agent's raw output yourself — note proposed tickets, file paths, and approaches | Share: "Planning agent A proposed [ticket X with approach Y] — is this preserved in your synthesis? Agent B's ticket about [Z] seems missing." | Conversation starter — agent must respond |
| 3 | VERIFY_ALL_RESULTS | After the agent responds, check that all planning results are accounted for | FAIL if planning results missing or incomplete |
| 4 | CHECK_TICKET_PRESERVATION | Compare ticket count in synthesis against sum of individual agent outputs | FAIL if tickets dropped during consolidation |
| 5 | DETECT_CONTRADICTIONS | Check for conflicting approaches between planning agents' outputs | Share: "Agent A proposes [approach X] for [area] but Agent B proposes [approach Y] for the same area. How did you resolve this?" | ESCALATE if agents proposed incompatible strategies |
| 6 | VALIDATE_ROUTING | Confirm agent routes to planningCollectorRequest (the default) | WARN if routing elsewhere without clear justification |
| 7 | ASSESS_COLLECTOR_CONTEXT | Check that enough detail is provided for collector to produce finalizedTickets | FAIL if synthesis lacks ticket descriptions, tasks, or acceptance criteria |
| 8 | INJECT_RESEARCH | Share your independent research findings — corrections, additional context the agent missed | Share all findings. Ask: "Confirm you've received these findings and update your proposed result if needed." | Agent must confirm receipt and integrate |
| 9 | JUSTIFICATION_PASSED | All checks pass — send JUSTIFICATION_PASSED with `--no-expect-response`. Do NOT include new information — only approval. | Agent returns final structured result |

## Red Flags

- Synthesis has fewer tickets than the sum of individual planning agent outputs
- Agent doesn't mention any planning results by name or content
- Routing away from collector without raising an interrupt first
- Agent introduces new tickets not present in any planning agent's output
- Agent's justification has no result preview — only reasoning
