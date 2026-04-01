# Phase-Gate Review Checklist

General instructions for reviewing agent output at every phase transition. This checklist applies to ALL phase gates regardless of agent type.

## Core Principle: This Is a Refinement Process, Not a Rubber Stamp

The controller is NOT a parliament that approves whatever the agent submits. Every checklist item is a **conversation starter** — a prompt for you to:

1. **Research independently**: Go to the actual sources (codebase, prior agent outputs, goal text) and form your own opinion
2. **Inject your insights**: Tell the agent what you found, especially where it differs from or adds to what the agent claimed
3. **Challenge assumptions**: Ask the agent to confirm, update, or justify in light of your findings
4. **Iterate**: Repeat until the result is genuinely good, not just "good enough"

Each ACTION in the agent-specific checklists has an associated RESEARCH step. You MUST do the research BEFORE evaluating the agent's claims. Do not evaluate claims at face value.

## Before Approving Any Phase Transition

### 1. Extract Goal Requirements

- Read the original goal text submitted via `/api/ui/goals/start`
- Enumerate each distinct requirement as a numbered item
- If the goal is ambiguous, escalate to the user BEFORE proceeding

### 2. Verify the Agent Previewed Its Result

The agent's justification must include a **preview of what it plans to return** — not just reasoning about why. If the agent only explains its thought process without describing the concrete result data, send it back:

> "Your justification describes your reasoning but not your proposed result. I need to see what you plan to return — the specific findings/tickets/routing/changes — so I can evaluate the actual output."

### 3. Research Before Evaluating

For EACH checklist item in the agent-specific checklist:

1. **Read the relevant sources yourself** — don't take the agent's word for it
2. **Form your own opinion** about what the answer should be
3. **Compare** your findings with the agent's claims
4. **Share your findings** with the agent, especially discrepancies or additions
5. **Ask the agent to respond**: confirm receipt, update assumptions, incorporate your research, or justify their original position
6. **Wait for the agent's response** before moving to the next checklist item

### 4. Map Requirements to Agent Output

For each numbered requirement:

| # | Requirement | Addressed? | Evidence | Gap? |
|---|-------------|-----------|----------|------|
| 1 | ... | YES/NO/PARTIAL | Where in the output | What's missing |

- Every requirement must have at least PARTIAL coverage
- If any requirement is NO, the phase transition MUST be rejected or escalated

### 5. Check for Hallucinated Work

- Does the agent claim to have done things not reflected in the actual output?
- Are file paths, class names, or API endpoints real (verify against codebase)?
- Does the agent address the STATED goal or a reinterpretation of it?

### 6. Propagator Signals Are Necessary But Not Sufficient

- Propagators check form: duplication, ambiguity, domain relevance
- Propagators do NOT check substance: does this actually solve the goal?
- "No escalation" from propagators means the output is well-formed, not correct
- You MUST independently verify semantic correctness

### 7. Escalation Rules

Escalate to the user when:
- Any requirement has NO coverage in the output
- The agent reinterpreted the goal differently than intended
- You are unsure whether the output is correct
- The same failure mode appeared in a previous session (check `conversational-topology-history/`)
- The agent's confidence is high but the evidence is thin

Do NOT escalate when:
- All requirements are mapped with clear evidence
- The output is consistent with the codebase state
- Minor style or formatting issues that don't affect correctness

### 8. Conversation Flow

The controller drives the review conversation by stepping through ACTION rows one at a time. For each ACTION:

**Research Phase:**
1. Do your own research for this checklist item (read code, check files, review prior outputs)
2. Form your own opinion about what the answer should be
3. Share your findings with the agent — especially anything the agent missed or got wrong
4. Include the `--action-name` for the current step when responding via `conversations.py`

**Confirmation Phase:**
5. Ask the agent to: (a) confirm it received your insights, (b) update its proposed result if needed, (c) justify its original position if it disagrees
6. Wait for the agent's response via `call_controller`
7. Evaluate whether the agent adequately addressed your findings

**Progression:**
- If the agent's response is satisfactory, move to the next ACTION
- If not, send follow-up feedback on the same ACTION until resolved
- End your message with: *"After addressing this feedback, call `call_controller` again with your updated response."*

**If a checklist item FAILs with a critical issue:**
- Describe the specific failure and what the agent must change
- End with: *"Address the above issues and call `call_controller` again. Do not return your result until these are resolved."*
- Do NOT approve until the agent has remedied the issue and called back

**INJECT_RESEARCH — share new information and expect integration:**
- Use `--action-name INJECT_RESEARCH` (or any other non-terminal action) whenever you have new information for the agent: codebase research, file location corrections, code details, assumptions to challenge
- This action expects the agent to confirm receipt and integrate findings into its proposed result — do NOT use `--no-expect-response`
- The agent will call `call_controller` again after integrating, giving you a chance to verify the refined result
- You may use multiple rounds of INJECT_RESEARCH if the agent's integration is incomplete
- **Any action that provides new information the agent needs to integrate MUST NOT be JUSTIFICATION_PASSED** — use INJECT_RESEARCH, CHALLENGE_ASSUMPTIONS, or any other checklist action instead

**USER_CONFIRMATION — mandatory user gate before terminal approval:**
- **CRITICAL: Before sending JUSTIFICATION_PASSED for ANY agent, the controller MUST present its findings to the user and get explicit confirmation to proceed.**
- Summarize for the user: what the agent produced, what you verified, any concerns or gaps
- Wait for the user to confirm before sending JUSTIFICATION_PASSED
- If the user rejects or requests changes, go back to INJECT_RESEARCH with the user's feedback
- This applies to ALL agent types — discovery, planning, ticket, orchestrator, dispatch, collector

**JUSTIFICATION_PASSED — terminal approval, no new information:**
- **CRITICAL: The `controller_response.jinja` template matches on JUSTIFICATION_PASSED and instructs the agent to immediately return its structured JSON result without calling `call_controller` again.** This is a hard match in the template — the agent is told "Do NOT call call_controller again. Return your final structured JSON result now."
- Because of this template behavior, **you MUST NOT include any new information in the JUSTIFICATION_PASSED message**. If you include new findings, the agent receives two conflicting signals: "integrate this" and "return immediately without calling back." This causes the agent to either loop (calling `call_controller` to confirm) or silently drop the new information.
- JUSTIFICATION_PASSED should only confirm the already-integrated and refined result. It may include a reminder about JSON output format but nothing the agent needs to act on.
- The correct flow is: share all research via INJECT_RESEARCH → agent confirms integration → verify the refined result → **get user confirmation** → only then send JUSTIFICATION_PASSED with `--no-expect-response`
- Respond with `--action-name JUSTIFICATION_PASSED` and `--no-expect-response`
- This is the terminal signal — do not send it until you are satisfied that all information has been integrated, the agent's proposed result is correct, **and the user has confirmed**

**If you need to escalate to the user:**
- Do NOT respond to the agent — escalate to the user first
- After user guidance, resume the conversation with the agent

### 9. Checklist Evolution

Do NOT record per-conversation evidence or session logs. The `conversational-topology-history/` directory is a changelog for checklist changes only.

Update a checklist when you observe a **new failure mode** during a session that is not already captured:
- Add it to the relevant agent-specific checklist (Common Failure Modes / Red Flags)
- If it warrants a new ACTION row, add it with the appropriate Gate level
- Record the change in `conversational-topology-history/reference.md`

---

## Phase-Specific Gates

### Discovery -> Planning

- Are all relevant code areas identified?
- Does the discovery output cover the full scope (not just the first file found)?
- Are architectural dependencies captured?

### Planning -> Tickets

- Does each ticket trace to a specific requirement?
- Are tickets decomposed to a single responsibility?
- Is the execution order specified and correct?

### Tickets -> Completion

- Read the actual diff, not just the summary
- Verify tests were written/updated where appropriate
- Check that no unrelated changes were introduced
