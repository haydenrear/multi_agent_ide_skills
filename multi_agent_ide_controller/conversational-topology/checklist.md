# Phase-Gate Review Checklist

General instructions for reviewing agent output at every phase transition. This checklist applies to ALL phase gates regardless of agent type.

## Before Approving Any Phase Transition

### 1. Extract Goal Requirements

- Read the original goal text submitted via `/api/ui/goals/start`
- Enumerate each distinct requirement as a numbered item
- If the goal is ambiguous, escalate to the user BEFORE proceeding

### 2. Map Requirements to Agent Output

For each numbered requirement:

| # | Requirement | Addressed? | Evidence | Gap? |
|---|-------------|-----------|----------|------|
| 1 | ... | YES/NO/PARTIAL | Where in the output | What's missing |

- Every requirement must have at least PARTIAL coverage
- If any requirement is NO, the phase transition MUST be rejected or escalated

### 3. Check for Hallucinated Work

- Does the agent claim to have done things not reflected in the actual output?
- Are file paths, class names, or API endpoints real (verify against codebase)?
- Does the agent address the STATED goal or a reinterpretation of it?

### 4. Propagator Signals Are Necessary But Not Sufficient

- Propagators check form: duplication, ambiguity, domain relevance
- Propagators do NOT check substance: does this actually solve the goal?
- "No escalation" from propagators means the output is well-formed, not correct
- You MUST independently verify semantic correctness

### 5. Escalation Rules

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

### 6. Conversation Continuation

The controller drives the review conversation by stepping through ACTION rows one at a time. After each response:

**If there are more checklist items to review:**
- Include the `--action-name` for the current step when responding via `conversations.py`
- End your message with: *"After addressing this feedback, call `call_controller` again with your updated response."*
- The agent will call back, and you proceed to the next ACTION step

**If a checklist item FAILs with a critical issue:**
- Describe the specific failure and what the agent must change
- End with: *"Address the above issues and call `call_controller` again. Do not return your result until these are resolved."*
- Do NOT approve until the agent has remedied the issue and called back

**If all checklist items pass:**
- Respond with `--action-name JUSTIFICATION_PASSED` and `--no-expect-response`
- The agent is instructed to only return its final structured result after receiving `JUSTIFICATION_PASSED`
- This is the terminal signal — do not send it until you are satisfied with the agent's work

**If you need to escalate to the user:**
- Do NOT respond to the agent — escalate to the user first
- After user guidance, resume the conversation with the agent

### 7. Checklist Evolution

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
