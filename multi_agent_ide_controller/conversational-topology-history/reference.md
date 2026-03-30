# Conversational Topology — Change History

Changelog for modifications to checklist files in `conversational-topology/`. Only record entries here when a checklist file is actually changed — do not log per-conversation decisions or session evidence.

## How to record a change

After modifying any file in `conversational-topology/`:

```
### YYYY-MM-DD — <brief description>
- **File**: `<filename>`
- **Change**: <what was added/removed/modified>
- **Reason**: <why — observed failure mode, user feedback, or gap identified>
- **Session**: <session ID or "N/A" if offline edit>
```

---

## Entries

### 2026-03-27 — Initial creation

- **Files**: `checklist.md`, `checklist-discovery-agent.md`, `checklist-planning-agent.md`, `checklist-ticket-agent.md`, `reference.md`
- **Change**: Created all initial documents with ACTION tables, failure modes, justification questions, and red flags
- **Reason**: Establishing the conversational topology review framework per spec 001-agent-topology US10
- **Session**: N/A (initial creation)

### 2026-03-30 — Full agent coverage checklists

- **Files**: `checklist-orchestrator.md`, `checklist-orchestrator-collector.md`, `checklist-discovery-orchestrator.md`, `checklist-discovery-dispatch.md`, `checklist-discovery-collector.md`, `checklist-planning-orchestrator.md`, `checklist-planning-dispatch.md`, `checklist-planning-collector.md`, `checklist-ticket-orchestrator.md`, `checklist-ticket-dispatch.md`, `checklist-ticket-collector.md`, `reference.md`
- **Change**: Created 11 new agent-specific checklists covering all agent types in the workflow graph (orchestrators, dispatchers, collectors). Updated reference.md with organized tables by phase. Each checklist includes failure modes, ACTION table, justification questions, and red flags tailored to that agent's specific role.
- **Reason**: Controller was rubber-stamping call_controller justification conversations without using checklists because checklists only existed for 3 of 14 agent types. User feedback: "you didn't bother to use your checklist."
- **Session**: a26a5735-61cd-465b-9b29-2c4369f49356

### 2026-03-30 — Action name tracking and conversation continuation protocol

- **Files**: `checklist.md`, `reference.md` (conversational-topology), `conversations.py`, `reference.md` (executables), `SKILL.md`, `controller_response.jinja`
- **Change**: Added required `--action-name` field to `conversations.py --respond` for checklist step tracking. Added conversation continuation protocol to `checklist.md` (new step 6) — instructs controller to tell agents to call back via `call_controller` when more checklist items remain or when issues need remediation. Updated `controller_response.jinja` with agent-side instructions to use `call_controller` for follow-ups. Updated SKILL.md with full action name tracking documentation and multi-round conversation examples.
- **Reason**: Action names were not being tracked, making self-improvement impossible. Agents would return their result instead of calling back when the controller had more checklist items to review. The conversation protocol was one-shot instead of multi-round.
- **Session**: a26a5735-61cd-465b-9b29-2c4369f49356
