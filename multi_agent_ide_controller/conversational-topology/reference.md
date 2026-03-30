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
3. For each ACTION row, follow the **Core Protocol: Research Before Judging**:
   - Research the relevant sources yourself before evaluating the agent's claims
   - Share your findings with the agent — especially discrepancies or things the agent missed
   - Ask the agent to confirm: acknowledge your insights, update its proposed result, or justify its original position
   - Wait for the agent's response before progressing to the next ACTION
4. Stop at the first FAIL — but treat RESEARCH_* and CHALLENGE_* steps as conversation starters, not gates
5. If a new failure mode is observed, update the agent-specific checklist and log the change in `../conversational-topology-history/reference.md`

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

- All 14 agent-specific checklists created with basic ACTION tables

### Research/Insight protocol overhaul — 2026-03-30

Transformed all 14 checklists from rubber-stamp gates into active research/refinement processes:

**Structural changes to every checklist:**
- Added "Core Protocol: Research Before Judging" header with 4-step research protocol
- Replaced old ACTION tables (Description + Gate columns) with research-driven tables (What YOU Research + What to Tell the Agent + Gate columns)
- Added `VERIFY_RESULT_PREVIEW` as early step — agents must preview their planned result, not just explain reasoning
- Added `CHALLENGE_ASSUMPTIONS` step near the end — controller verifies agent assumptions against actual codebase
- Added agent-type-specific `RESEARCH_*` steps as conversation starters

**Per-agent research actions added:**
- Discovery agent: RESEARCH_SCOPE, RESEARCH_ARCHITECTURE (12 ACTION rows)
- Discovery orchestrator: RESEARCH_CODEBASE_STRUCTURE (10 ACTION rows)
- Discovery collector: RESEARCH_DISCOVERY_OUTPUTS, RESEARCH_COVERAGE_GAPS (11 ACTION rows)
- Discovery dispatch: RESEARCH_RAW_OUTPUTS (7 ACTION rows)
- Planning agent: RESEARCH_DISCOVERY_ALIGNMENT, RESEARCH_FILE_PATHS (11 ACTION rows)
- Planning orchestrator: RESEARCH_DISCOVERY_OUTPUT (10 ACTION rows)
- Planning collector: RESEARCH_PLANNING_OUTPUTS, RESEARCH_DEPENDENCY_CHAIN (12 ACTION rows)
- Planning dispatch: RESEARCH_RAW_OUTPUTS (8 ACTION rows)
- Ticket agent: RESEARCH_DIFF, RESEARCH_CORRECTNESS, RESEARCH_TEST_COVERAGE (13 ACTION rows)
- Ticket orchestrator: RESEARCH_FINALIZED_PLAN, RESEARCH_REQUEST_CONTEXT (11 ACTION rows)
- Ticket collector: RESEARCH_TICKET_RESULTS, RESEARCH_REQUIREMENT_COVERAGE (13 ACTION rows)
- Ticket dispatch: RESEARCH_RAW_OUTPUTS (8 ACTION rows)
- Orchestrator: RESEARCH_PHASE_STATE, RESEARCH_COLLECTOR_READINESS (11 ACTION rows)
- Orchestrator collector: RESEARCH_PHASE_RESULTS, RESEARCH_REQUIREMENT_FULFILLMENT (12 ACTION rows)

**Also updated:**
- `checklist.md` — added "Core Principle: This Is a Refinement Process", "Verify the Agent Previewed Its Result", and "Research Before Evaluating" sections
- `_review_justification.jinja` — added Result Preview requirement and refinement process description
- All 13 justification jinja prompts — added "Result Preview (REQUIRED)" section and "Assumptions" item per agent type
