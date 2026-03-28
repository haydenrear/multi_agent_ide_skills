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

### 6. Record Your Decision

After each gate decision:
- Note which requirements were verified and how
- If you approved, record what gave you confidence
- If you rejected, record the specific gap
- If a new failure mode was observed, update the agent-specific checklist

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
