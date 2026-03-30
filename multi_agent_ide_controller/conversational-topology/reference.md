# Conversational Topology Documents — Reference Index

This directory contains the review checklists and gate criteria that the controller uses when evaluating agent output at each phase transition.

## Documents

### General

| Document | Purpose | When to use |
|----------|---------|-------------|
| `checklist.md` | General phase-gate review instructions | Every phase transition — extract requirements, map to outputs, check for hallucinated work, apply escalation rules |

### Orchestrator Layer

| Document | Purpose | When to use |
|----------|---------|-------------|
| `checklist-orchestrator.md` | Top-level orchestrator review criteria | Goal entry — verify routing decision, goal fidelity, phase awareness |
| `checklist-orchestrator-collector.md` | Final consolidation review criteria | Tickets → Complete gate — verify all phases ran, ticket results mapped to requirements, merge status |

### Discovery Phase

| Document | Purpose | When to use |
|----------|---------|-------------|
| `checklist-discovery-orchestrator.md` | Discovery orchestrator review criteria | Goal → Discovery agents — verify fan-out policy, scope partitioning, ordering |
| `checklist-discovery-agent.md` | Discovery agent review criteria | Discovery → Planning gate — verify scope coverage, architectural dependencies, interpretation accuracy |
| `checklist-discovery-dispatch.md` | Discovery dispatch review criteria | Discovery agents → Discovery collector — verify synthesis quality, routing |
| `checklist-discovery-collector.md` | Discovery collector review criteria | Discovery → Planning gate — verify unified document, findings sourcing, ADVANCE/ROUTE_BACK decision |

### Planning Phase

| Document | Purpose | When to use |
|----------|---------|-------------|
| `checklist-planning-orchestrator.md` | Planning orchestrator review criteria | Discovery results → Planning agents — verify fan-out, discovery input usage, structured output |
| `checklist-planning-agent.md` | Planning agent review criteria | Planning → Tickets gate — verify traceability, decomposition granularity, dependency ordering |
| `checklist-planning-dispatch.md` | Planning dispatch review criteria | Planning agents → Planning collector — verify ticket preservation, contradiction detection |
| `checklist-planning-collector.md` | Planning collector review criteria | Planning → Tickets gate — verify finalized tickets, dependency graph, structured output |

### Ticket Phase

| Document | Purpose | When to use |
|----------|---------|-------------|
| `checklist-ticket-orchestrator.md` | Ticket orchestrator review criteria | Plan → Ticket agents — verify 1:1 ticket mapping, self-contained requests, ordering |
| `checklist-ticket-agent.md` | Ticket agent review criteria | Tickets → Completion gate — read the diff, verify exhaustive switches, check tests, detect collateral damage |
| `checklist-ticket-dispatch.md` | Ticket dispatch review criteria | Ticket agents → Ticket collector — verify failure reporting, success validation |
| `checklist-ticket-collector.md` | Ticket collector review criteria | Tickets → Complete gate — verify commit review, failure analysis, honest completeness assessment |

## How to use during a controller session

1. At each phase gate, load `checklist.md` first for the general review protocol
2. Then load the agent-specific checklist for the current transition
3. Execute each ACTION row in order — stop at the first FAIL
4. If a new failure mode is observed, update the agent-specific checklist and log the change in `../conversational-topology-history/reference.md`

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

### Full agent coverage — 2026-03-30

- `checklist-orchestrator.md` — 6 ACTION rows, 4 common failure modes, 6 justification questions, 5 red flags
- `checklist-orchestrator-collector.md` — 7 ACTION rows, 5 common failure modes, 6 justification questions, 6 red flags
- `checklist-discovery-orchestrator.md` — 6 ACTION rows, 5 common failure modes, 5 justification questions, 5 red flags
- `checklist-discovery-dispatch.md` — 4 ACTION rows, 4 common failure modes, 4 justification questions, 4 red flags
- `checklist-discovery-collector.md` — 6 ACTION rows, 5 common failure modes, 5 justification questions, 6 red flags
- `checklist-planning-orchestrator.md` — 6 ACTION rows, 5 common failure modes, 5 justification questions, 5 red flags
- `checklist-planning-dispatch.md` — 5 ACTION rows, 4 common failure modes, 4 justification questions, 4 red flags
- `checklist-planning-collector.md` — 7 ACTION rows, 5 common failure modes, 5 justification questions, 6 red flags
- `checklist-ticket-orchestrator.md` — 6 ACTION rows, 5 common failure modes, 5 justification questions, 6 red flags
- `checklist-ticket-dispatch.md` — 5 ACTION rows, 4 common failure modes, 4 justification questions, 5 red flags
- `checklist-ticket-collector.md` — 8 ACTION rows, 5 common failure modes, 6 justification questions, 7 red flags
