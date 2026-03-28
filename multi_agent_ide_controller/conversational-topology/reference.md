# Conversational Topology Documents — Reference Index

This directory contains the review checklists and gate criteria that the controller uses when evaluating agent output at each phase transition.

## Documents

| Document | Purpose | When to use |
|----------|---------|-------------|
| `checklist.md` | General phase-gate review instructions | Every phase transition — extract requirements, map to outputs, check for hallucinated work, apply escalation rules |
| `checklist-discovery-agent.md` | Discovery agent review criteria | Discovery → Planning gate — verify scope coverage, architectural dependencies, interpretation accuracy |
| `checklist-planning-agent.md` | Planning agent review criteria | Planning → Tickets gate — verify traceability, decomposition granularity, dependency ordering |
| `checklist-ticket-agent.md` | Ticket agent review criteria | Tickets → Completion gate — read the diff, verify exhaustive switches, check tests, detect collateral damage |

## How to use during a controller session

1. At each phase gate, load `checklist.md` first for the general review protocol
2. Then load the agent-specific checklist for the current transition
3. Execute each ACTION row in order — stop at the first FAIL
4. Record your decision (approved/rejected/escalated) with evidence
5. If a new failure mode is observed, update the agent-specific checklist

## Change history

When updating any document in this directory:

1. Make the change in the relevant file
2. Add an entry to `../conversational-topology-history/reference.md` with the date, file changed, and what was modified
3. If the change adds a new ACTION row or removes one, verify the step numbering is still sequential

### Initial creation — 2026-03-27

- `checklist.md` — general phase-gate review (6 sections: extract requirements, map to outputs, check hallucinations, propagator signals, escalation rules, record decision)
- `checklist-discovery-agent.md` — 7 ACTION rows, 4 common failure modes, 5 justification questions
- `checklist-planning-agent.md` — 7 ACTION rows, 5 common failure modes, 6 justification questions
- `checklist-ticket-agent.md` — 9 ACTION rows, 5 common failure modes, 6 justification questions, 7 red flags
