# Controller UI Ergonomics Report

*Generated after a full integration test session (health-check endpoint ticket). Covers pain points with the controller scripts and backend endpoints, and concrete recommendations for improvement.*

---

## 1. Interrupt Discovery Was the Biggest Pain Point

### What happened
`poll.py` reported "0 pending interrupts" even when an interrupt was actively blocking the run. This was because `GET /api/interrupts/pending` didn't exist — only `POST` endpoints were present in `InterruptController`. The poll script was silently hitting a 404, returning `None`, and printing "0 pending".

### Impact
- Multiple poll cycles wasted on "no pending items" while the run was actually blocked.
- Diagnosis required manual propagation item inspection, grepping for `transitionToInterruptState` layer items — a non-obvious, fragile path.
- Resolution was guesswork: which ID to pass? `contextId` from the propagation payload? The root `nodeId`? The interrupt `requestId`? All three were tried.

### Fix (done)
- Added `GET /api/interrupts/pending` to `InterruptController` returning `PendingInterruptSummary` (interruptId, originNodeId, reason, interruptType).
- Added `interrupts.py` executable: lists pending interrupts for a node, enriches with `/api/interrupts/detail`, resolves with `--resolve`.
- `poll.py` now uses the real endpoint and shows `originNodeId` + a hint to run `interrupts.py --resolve`.

### Still needed
- `interrupts.py --resolve` often needs to try multiple IDs (interruptId, then root nodeId). The backend could be smarter: accept any of these without the caller needing to know which one is the canonical key.
- The `/resolve` endpoint could return a `NOT_FOUND` with a hint ("did you mean interruptId X?") rather than just failing.

---

## 2. Permission Resolution: First Permission Often Has No Tool Info

### What happened
The first permission in a new node sometimes shows `toolCalls: []` and `meta: null` when fetched via `/api/permissions/detail`. The tool name shows as `unknown-tool` in `poll.py`.

### Why
The ToolCallEvent is emitted *after* the permission request, so the detail endpoint can't find a matching tool call yet.

### Impact
- Operator can't see what the agent is asking to do.
- Forces a blind approve/reject decision for the first permission.

### Recommendation
- Buffer the permission detail response slightly (or return the tool name from the permission request itself if it's available).
- Alternatively, have the agent include a `toolName` or `actionDescription` field in the permission payload so the detail endpoint can show it even before the ToolCallEvent arrives.
- Short-term: add a `--wait` flag to `permissions.py` that retries the detail fetch for 5s before showing.

---

## 3. The `propagatedText` Payload Is Hard to Read

### What happened
`propagatedText` stores a nested JSON-in-JSON structure: `{"llmOutput": "...", "propagationRequest": "{\"goal\": ..., \"agentRequests\": ...}"}`. The inner `propagationRequest` is itself a JSON string (double-encoded).

### Impact
- Raw payload is nearly unreadable: escaped quotes, large blobs, no structure.
- `poll.py`'s `summarize_payload()` had to be updated for both the new Propagation record shape and the legacy flat format.
- `validate_propagation.py` is the only way to confirm structural integrity across a run.

### Recommendation
- Store `propagationRequest` as a native JSON object (not a string). This removes the double-encoding.
- `propagation_detail.py` should accept a `--format pretty` flag that fully expands nested JSON for inspection.
- Add a `--field goal` flag to `propagation_detail.py` to extract a single top-level field from `propagationRequest` without parsing it manually.

---

## 4. `summary_text` Overflow (Fixed, But Fragile Design)

### What happened
`summary_text VARCHAR(4000)` was overflowing when large payloads (worktreeContext, mergeAggregation) flowed through non-AI propagators. The raw payload was written directly to `summaryText`.

### Fix (done)
- Liquibase changeSet 017: widened `summary_text` to `TEXT`.
- `truncateSummary()` helper in `PropagationExecutionService`: caps at 3800 chars.

### Residual concern
The root issue is that `summaryText` is being populated with the raw payload as a fallback when the propagator can't produce a real summary. This is a design smell — `summaryText` should always be a *human-readable digest*, not a raw payload dump. The truncation fix is a safety net, but the propagator should produce a proper summary or leave the field null.

### Recommendation
- Non-AI propagators that write the raw payload as summaryText should instead write a structured short description: `"[ACTION_REQUEST] kickOffAnyNumberOfAgentsForCodeSearch: goal=..."`.
- Add a guard in `PropagationExecutionService` that logs a warning when `summaryText` exceeds 500 chars — it signals a propagator writing raw data rather than a summary.

---

## 5. Workflow Graph Node Types Show as SUMMARY

### What happened
The `workflow-graph` endpoint returned `nodeType=SUMMARY` for all child nodes with `status=?` during this session. The graph showed: `ORCHESTRATOR → SUMMARY → SUMMARY → SUMMARY` instead of named agent types.

### Why
This appears to happen when the graph is reconstructed from summary events rather than live node state. When events are 217 with `chatMsgs=0 tools=0`, the graph is not reflecting live state — it's showing compressed/summary nodes.

### Impact
- Can't tell which agent type is running without inspecting propagation items.
- `status=?` makes it impossible to distinguish RUNNING from STALLED from COMPLETED nodes.

### Recommendation
- Add a `nodeType` field to propagation items that always carries the actual agent class name.
- The graph endpoint should maintain the last known `nodeType` per node, not fall back to `SUMMARY`.
- Add a `lastEventTimestamp` to each graph node so the controller can detect stalls without comparing consecutive polls.

---

## 6. Poll Cadence and Stall Detection Are Manual

### What happened
The only way to detect a stall was to compare event counts across polls manually. There's no built-in stall indicator.

### Recommendation
- Add a `stalledSince` field to the graph response: a timestamp if `chatMsgs + toolEvents + streamTokens` hasn't grown in the last N minutes, null otherwise.
- Add a `health` endpoint: `GET /api/ui/workflow-graph/health?nodeId=...` that returns `{running, stalled, error}` — a single field the controller can check without parsing the full graph.
- `poll.py` could accept `--watch N` (poll every N seconds, stop on completion/stall/error).

---

## 7. Permission and Interrupt Resolution IDs Are Confusing

### What happened
Three different ID spaces in use simultaneously:
- Permission: `requestId` (UUID)
- Interrupt: `interruptId` (UUID), `originNodeId` (ArtifactKey), `contextId` (sometimes an ArtifactKey, sometimes a UUID)
- Propagation: `itemId`, `layerId`, `nodeId` (all different namespaces)

`permissions.py` uses `requestId`. `interrupts.py` tries `interruptId`, then falls back to root `nodeId`. The `/resolve` endpoints accept either form but return `NOT_FOUND` with no hint if you pass the wrong one.

### Recommendation
- Standardize on a single `id` field returned by all `/pending` endpoints that is guaranteed to work with the corresponding `/resolve` endpoint.
- Document the ID contract explicitly in the `@Operation` description of each endpoint.
- Both `permissions.py` and `interrupts.py` should print the exact command to resolve each item — not just the ID but the full ready-to-run command:
  ```
  To resolve: python interrupts.py <nodeId> --resolve APPROVED --notes "..."
  ```

---

## 8. No End-to-End "Is the Run Done?" Signal

### What happened
There's no single API call that answers "is this run complete, and did it succeed?". The controller had to infer completion from:
- No pending permissions or interrupts
- No growing `chatMsgs`/`toolEvents`
- Propagation items all RESOLVED or ACKNOWLEDGED

### Recommendation
- Add `GET /api/ui/workflow-graph/status?nodeId=...` returning `{status: RUNNING|COMPLETE|FAILED|STALLED, summary: "..."}`.
- Or add a `terminalStatus` field to the workflow-graph response alongside `stats`.
- `poll.py` should detect completion and print a final summary line: `COMPLETE ✓` or `FAILED: <reason>`.

---

## Priority Summary

| Priority | Item | Effort |
|----------|------|--------|
| P0 (done) | `GET /api/interrupts/pending` endpoint | Low |
| P0 (done) | `interrupts.py` executable | Low |
| P1 | Standardize resolution IDs across permissions + interrupts | Medium |
| P1 | `workflow-graph` `lastEventTimestamp` per node (stall detection) | Medium |
| P1 | `summary_text` should never be raw payload | Low |
| P2 | `poll.py --watch N` continuous mode | Low |
| P2 | `propagation_detail.py --field` extraction flag | Low |
| P2 | `GET /api/ui/workflow-graph/status` completion signal | Medium |
| P3 | Permission detail: buffer or include tool name in payload | Medium |
| P3 | Remove double-encoding in `propagationRequest` | High (schema change) |
