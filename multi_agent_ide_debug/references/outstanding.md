# Outstanding Ergonomic Issues

Items that were identified during controller sessions but not yet addressed. Add new items as they surface; move to done or delete when fixed.

---

## 1. No by-itemId endpoint for propagation items

**Problem:** `poll.py` shows `itemId` per propagation item and prints a `--limit N` hint to fetch it via `propagation_detail.py`. But the hint is only positionally correct at the moment of that poll — as new items arrive they push older items to higher `--limit` positions, making stale hints wrong.

**Root cause:** There is no `POST /api/propagations/items/by-id` (or equivalent) endpoint. The only fetch path is `POST /api/propagations/items/by-node` which returns the N most recent items. You can't fetch a specific item by its `itemId` directly.

**Workaround:** Re-run `propagation_detail.py <nodeId> --limit <N>` with a limit large enough to include the item you want, then look at position N. If you still have the itemId from poll output, grep the raw output to find it.

**Fix needed:** Add `POST /api/propagations/items/by-id` to `PropagationController.java` accepting `{"itemId": "prop-item-..."}` and returning the single item. Then update `propagation_detail.py` to support `--item-id <id>` and update the poll hint to use `--item-id` instead of `--limit N`.

---

## 3. ACP `usage_update` deserialization error (noisy but non-fatal)

**Problem:** Log shows repeated `JsonDecodingException: Serializer for subclass 'usage_update' is not found in the polymorphic scope of 'SessionUpdate'` when ACP server sends `session/update` notifications.

**Root cause:** The `agentclientprotocol` Kotlin SDK's `SessionNotification` sealed class does not include a `usage_update` subtype. Newer ACP server versions send `usage_update` events (likely for token-usage reporting) but the client model doesn't register them.

**Workaround:** Errors are caught and logged; no impact on workflow execution.

**Fix needed:** Add `usage_update` as a registered subtype in the ACP Kotlin SDK's `SessionNotification` polymorphic scope, or add a catch-all `UnknownSessionUpdate` type with `@JsonDefaultSerializer`.

---

## 4. Propagator summary too long for `prompt-health-check` layer

**Problem:** Log shows `summaryText is 132528 chars (expected <500)` for `prompt-health-check` registrationId.

---

## 5. Propagator loop detection false positive — counts visits across different discovery agents

**Problem:** Propagator flagged "3rd invocation with identical subdomain focus" for `runDiscoveryAgent`, but the 3 visits were: Agent 1 (git infrastructure), an internal routing visit, and Agent 2 (orchestration). These are different agents with different subdomain focus, not a loop.

**Root cause:** The propagator's loop detection uses the Embabel framework's action visit counter, which counts all visits to the `runDiscoveryAgent` action regardless of which agent instance is being run. It then claims "identical scope" without comparing the actual `subdomainFocus` values.

**Fix needed:** The loop-detection propagator should compare `subdomainFocus` (or `contextId`) across visits before flagging a loop, not just the visit count.

---

## 2. poll.py --limit hint reuse only valid at time of poll

Related to #1: the `→ python propagation_detail.py <nodeId> --limit N` hint printed per item in `poll.py` reflects the item's position *at the time of that poll*. By the time you act on it, new items may have been added and the position will be wrong.

**Fix:** Blocked on #1 (by-itemId endpoint). Once that exists, the hint can use `--item-id` which is stable across polls.

---

## 6. Discovery agents hallucinate package paths (haiku model quality)

**Problem:** Discovery agent output contains `com/symbiosis/ide/orchestration/` in `fileReferences`, `relatedFiles`, and `relatedFilePaths` throughout the `unifiedCodeMap`. The correct package is `com/hayden/multiagentide/`. This propagates into the planning request and would cause ticket agents to target non-existent files.

**Root cause:** Haiku model hallucinated package names during discovery instead of using actual paths found via filesystem tools. The agents likely inferred paths from class names rather than reading the actual directory structure.

**Workaround:** Sent corrective message to planning orchestrator instructing it to verify all file paths against the actual filesystem before creating tickets.

**Fix needed:** Discovery agent prompts should include a validation step requiring agents to confirm file paths exist before including them in output. Alternatively, a post-discovery propagator could validate file paths against the worktree.

---

## 7. Planning dispatch routing fails with "Prompt is too long" when >2 planning agents

**Problem:** `dispatchPlanningAgentRequests` routing call failed after 10 retries with `JsonRpcException: Internal error: Prompt is too long`. This caused `PlanningAgentRequests not found in process context` and the entire orchestrator crashed. Goal `ak:01KKZ9ZH0NQJ63EJXN4TDBFWNV`.

**Root cause:** The planning orchestrator decomposed the goal into 3 planning agent tracks. When all 3 completed, the `dispatchPlanningAgentRequests` routing step tried to include all 3 agents' full ticket outputs (each with multiple tickets containing tasks and relatedFiles) in the prompt context. The combined output exceeded the ACP session's prompt token limit.

**Workaround:** None — the workflow crashed and cannot recover. Would need to restart with a smaller decomposition (1-2 planning agents instead of 3).

**Fix needed:** (1) The planning dispatch routing should summarize or truncate planning agent results before passing them to the routing LLM call, rather than including full ticket JSON. (2) Consider a max token budget check before the routing call, with automatic summarization if exceeded. (3) The planning orchestrator decomposition prompt could be tuned to produce fewer agents (max 2) to reduce consolidation payload size.

**Partial fix applied:** Added `CollectorSerialization` context that compacts worktree context to parent-only (single line). Used at all dispatch/collector routing call sites in `AgentInterfaces.java`. Also fixed `HistoricalRequestSerializationCtx` not suppressing worktree context in `appendPrettyWorktreeContext`.

---

## 8. PlanningAgentRequests vanishes from process context on action retry after "Prompt is too long"

**Problem:** After `dispatchPlanningAgentRequests` exhausted 10 inner LLM retries (all hitting "Prompt is too long"), the Embabel `RetryTemplate` retried the entire action. On outer retry count 2, the action failed with `IllegalArgumentException: Input it of type PlanningAgentRequests not found in process context`. The `PlanningAgentRequests` input was on the blackboard before the first attempt but disappeared by the second outer retry.

**Root cause:** Unknown. `RegisterAndHideInputResultDecorator` is a result/routing decorator — it only calls `hideInput` after a successful result, and the action never produced a result (it threw). The Embabel framework's `AbstractAgentProcess.executeAction` retry path may re-plan via `formulateAndExecutePlan` → `BlackboardRoutingPlanner.planToGoal()` between outer retries, which could alter blackboard state. Added logging to `BlackboardRoutingPlanner` and `RegisterAndHideInputResultDecorator` to capture this on next occurrence.

**Workaround:** None — workflow crashed. Root cause (prompt too long) is partially addressed by #7's fix.

**Fix needed:** Investigate the Embabel retry path. Determine whether `formulateAndExecutePlan` is called between outer retries (re-planning), and whether that re-planning or any intermediate step removes or hides the input from the blackboard. Add guards to prevent input loss during action retries.

---

## 9. Prompt health-check propagators trigger self-referential "deadlock" escalation

**Problem:** The prompt-health-check propagators fire on every LLM call via `PromptHealthCheckLlmCallDecorator`. When they produce propagation items, their own execution traces appear in subsequent health-check analyses. After 3-5 cycles, the propagator AI flags the accumulating execution history as a "catastrophic deadlock."

**Root cause:** The health-check propagator assembles the full prompt including execution history. The propagator AI misinterprets the growing history as evidence of a deadlock rather than recognizing it as normal propagator activity.

**Fix needed:** Either (1) strip propagation-related execution history entries from the prompt content before passing to health-check propagators, or (2) add context to the health-check system prompt explaining that propagation execution traces are normal.

---

## 10. GoalExecutor accepts `.git`-suffixed repositoryUrl despite path validation

**Problem:** `GoalExecutor.startGoal()` checks `Path.of(request.repositoryUrl()).toFile().exists()` — passing `/path/to/repo/.git` satisfies this check because the `.git` directory exists. The goal starts but downstream components may fail.

**Fix needed:** Add validation in `GoalExecutor` to strip trailing `/.git` or reject paths that are `.git` directories.

---

## 11. Duplicate goals run concurrently without deduplication

**Problem:** Submitting two goals pointing to the same repository starts both as independent workflow runs. Both consume LLM resources and may create conflicting worktrees.

**Fix needed:** Add optional deduplication check: warn or reject if an active goal already targets the same repositoryUrl.

---

## 12. STOP sequence needs finessing — agents retry on invalid JSON, orchestrator vs sub-agent differences

**Problem:** Sending `SEND_MESSAGE` with "STOP" to an agent node doesn't reliably stop it. The LLM may return immediately with an unparseable response, causing the framework to retry. Additionally, stop-q needs to propagate to close all acp chat sessions below that ArtifactKey that is the node ID.

**Fix needed — two tiers:**

### Tier 1: Graceful STOP (sub-agent and orchestrator nodes)
- STOP message should instruct the LLM to return a valid JSON payload.
- Add a `ResultDecorator` that detects a `null` result when a `StopRequest` exists in the blackboard history, and returns a sensible default by matching over the expected request type.

### Tier 2: Hard STOPQ (orchestrator nodes only)
- Support a `STOPQ` command that closes the ACP session entirely on `AcpChatModel`.
- Only safe for `OrchestratorNode` — sub-agents must use Tier 1.

**Workaround — Tier 2 confirmed working:** Send `SEND_MESSAGE` with message content `"stop-q"` to the orchestrator root nodeId. Routes through `MultiAgentEmbabelConfig.llmOutputChannel()` → `agentPlatform.getAgentProcess(processId).kill()`. Tested on `ak:01KM1NMADTF1A8MKG3HYT2E291`. Stale pending permissions from in-flight ACP sessions may still appear after the kill — reject them. Tier 1 is still unimplemented.

---

## 13. Discovery agent looping — sequential agents lack prior-agent context

**Problem:** Sequential discovery agents have no context about what earlier agents found, causing re-discovery, loop-detection alerts (#5), and wasted context.

**Partial fix applied (templates only):** `discovery_agent.jinja` and `discovery_orchestrator.jinja` updated with `priorAgentSummary` support.

**Fix still needed:** Add `priorAgentSummary` field to `DiscoveryAgentRequest` record in `AgentModels.java`, update constructors, and integrate the discovery orchestrator dispatch to inject prior findings.

---

## 14. Prompt-health-check propagators dump raw JSON instead of producing analysis

**Problem:** The `unnecessary-context-identifier` and `prompt-reduction-advisor` propagators frequently output raw worktreeContext JSON as their `llmOutput` / `summaryText` instead of producing an actual analysis. Example: the summary field contains `{"worktreeContext":{"mainWorktree":{"worktreeId":"ef2a0a75-...` instead of an insight about the prompt.

**Root cause:** The haiku model used for propagators is sometimes echoing back the prompt content or a portion of the request instead of following the propagator system prompt instructions. This may be due to (a) the prompt being too large for haiku to process meaningfully, (b) the propagator system prompt not being prominent enough, or (c) the haiku model struggling with the structured output schema (`AiPropagatorResult`).

**Workaround:** These items are noise — acknowledge and move on.

**Fix needed:** (1) Consider using a more capable model for prompt-health-check propagators. (2) Truncate the prompt content passed to propagators to a reasonable size. (3) Add stronger framing in the propagator system prompt to prevent echoing input.

---

## 15. Propagation detail API / script truncates large payloads — cannot inspect full planning results

**Problem:** When a planning agent produces a large result (e.g. 5 tickets with tasks and relatedFiles), `propagation_detail.py` and the underlying `/api/propagations/items/by-node` endpoint truncate the `agentResult` field. The controller cannot see the full ticket list to validate file paths, task descriptions, or ticket dependencies.

**Root cause:** Either the API serializes a truncated version of the `propagatedRequestFields`, or `propagation_detail.py` truncates output. The `agentResult` field in the propagation item may be stored as a summary string rather than the full JSON object.

**Workaround:** Query the propagation items directly in the database to see the full payload.

**Fix needed:** (1) Ensure `/api/propagations/items/by-node` returns the full `propagatedRequestFields` without truncation. (2) Add a `--full` flag to `propagation_detail.py` that outputs the complete raw JSON. (3) Consider adding a dedicated endpoint for fetching the raw agent result by itemId (related to #1).

---

## 16. JetBrains MCP tools write to IDE project directory instead of worktree sandbox

**Problem:** Agents using `mcp__jetbrains__create_new_file`, `mcp__jetbrains__replace_text_in_file`, and `mcp__jetbrains__execute_terminal_command` target `projectPath: /Users/hayde/IdeaProjects/multi_agent_ide_parent` (the IDE's open project). This is the **source checkout**, not the agent's worktree sandbox (`~/.multi-agent-ide/worktrees/<id>/`). Files created by agents end up in the wrong repo.

**Evidence:** Four scripts created at 21:33 during the discovery collector phase were written to the source checkout:
- `skills/multi_agent_ide_skills/multi_agent_ide_deploy/scripts/create-feature-branch.py`
- `skills/multi_agent_ide_skills/multi_agent_ide_deploy/scripts/merge-feature-to-main.py`
- `skills/multi_agent_ide_skills/multi_agent_ide_deploy/scripts/pull-merged-code.py`
- `skills/multi_agent_ide_skills/multi_agent_ide_deploy/scripts/sync-feature-branch.py`

**Root cause:** The JetBrains MCP server uses `projectPath` to determine where to write. The agent's worktree context provides the worktree path, but the JetBrains tools default to (or are explicitly passed) the IDE project path. The `AddIntellij` prompt decorator may be contributing by providing the IDE project path in tool descriptions.

**Fix needed:** Either (1) the `AddIntellij` decorator should rewrite `projectPath` to the agent's worktree path, (2) the agent prompt should instruct use of the worktree path for all file operations, or (3) a permission filter should block `mcp__jetbrains__create_new_file` calls targeting the source checkout when a worktree sandbox is active.

---

## 17. Discovery collectors and planning agents write files — only ticket agents should

**Problem:** The discovery collector created 4 Python scripts (`create-feature-branch.py`, `merge-feature-to-main.py`, `pull-merged-code.py`, `sync-feature-branch.py`) at 21:33 during the discovery collector phase. Discovery and planning phases are supposed to be **read-only** — only ticket execution agents should create or modify files.

**Root cause (two parts):**
1. **Phase constraint not enforced:** The discovery collector and planning agent prompts don't explicitly prohibit file creation. The agents have access to JetBrains MCP file creation tools and Terminal write access, with no guardrail preventing use during read-only phases.
2. **ALLOW_ALWAYS escalation:** When the controller approves a Terminal or JetBrains tool permission as `ALLOW_ALWAYS`, all subsequent calls from any node in that goal (and potentially other goals) are auto-approved. A read-only `ls` approval escalates to allowing `cat >file.py` writes. Permission grants are too coarse — they apply per-tool across all nodes rather than per-node or per-phase.

**Fix needed:**
1. Add explicit "DO NOT create, edit, or delete any files" instructions to discovery agent, discovery collector, planning orchestrator, and planning agent prompts/templates.
2. Consider phase-aware permission scoping: during discovery/planning phases, auto-reject any `create_new_file`, `replace_text_in_file`, or write-capable Terminal commands. Only ticket execution agents should have write permissions.
3. Make `ALLOW_ALWAYS` scope to the specific node that requested it, not to all nodes in the goal. Or add a `ALLOW_ALWAYS_READ_ONLY` option that permits only read operations.

---

## 18. Propagator receives bloated raw AgentRequest with duplicated worktreeContext

**Problem:** `ActionRequestPropagationIntegration` passes the raw Java object (e.g. `DiscoveryAgentResults`, `PlanningAgentResults`, `TicketAgentResults`) to `propagationExecutionService.execute()`. These objects carry `worktreeContext` on the top-level request AND on every nested child result AND on every merge aggregation entry. For the discovery dispatch with 3 agents, the propagator received **533KB** of input with **7 copies** of the 30KB `worktreeContext` (~224KB of redundancy). Planning dispatch was 226KB; ticket dispatch was 434KB.

**Root cause:** The `DecorateRequestResults.decorateResultsRequest(d, ...)` decorator chain (which includes `PropagateActionRequestDecorator`) fires at step 2 of the dispatch method, passing the raw `d` object. The `CollectorSerialization` compaction only happens at step 3 when building the `Map.of(...)` template args for the jinja LLM prompt. The propagator never sees the compacted version.

```java
// Step 2 — propagator fires here with raw d (7x worktreeContext)
d = DecorateRequestResults.decorateResultsRequest(d, context, resultsRequestDecorators, ...);

// Step 3 — compacted version only used for jinja template
Map<String, Object> model = Map.of("discoveryResults",
    d.prettyPrint(new CollectorSerialization()));
```

**Fix needed:** Add a `PropagatorSerialization` context to `AgentPretty.AgentSerializationCtx`. When the propagator serializes an `AgentRequest`/`ResultsRequest` for its input payload, use `prettyPrint(new PropagatorSerialization())` instead of raw JSON serialization. Each request type's `prettyPrint(PropagatorSerialization)` should:
1. Include `worktreeContext` only once at the top level (strip from nested child results and merge aggregation entries)
2. Preserve the actual content (agent outputs, reports, tickets) — don't strip those
3. Apply the same parent-only compaction for the single top-level `worktreeContext` (no submodule details)

This requires updating `ActionRequestPropagationIntegration.propagate()` to call `prettyPrint(new PropagatorSerialization())` on the request before passing it to `propagationExecutionService.execute()`, and implementing the deduplication logic in the `prettyPrint` switch for each `ResultsRequest` type (`DiscoveryAgentResults`, `PlanningAgentResults`, `TicketAgentResults`).

---

## 19. Haiku propagator echoes raw JSON instead of producing analysis on dispatch ACTION_REQUEST items

**Problem:** 4 out of 32 propagation items have `summaryText` and `llmOutput` that are raw JSON echoes of the input object. All 4 are `ACTION_REQUEST` stage on dispatch actions: `dispatchDiscoveryAgentRequests` (253K and 131K), `dispatchPlanningAgentRequests` (107K), `dispatchTicketAgentRequests` (206K). The haiku model receives input too large to analyze and parrots it back verbatim.

**Root cause:** Downstream of #18 — the propagator input is the raw bloated object (100-260KB). Haiku cannot meaningfully analyze payloads this large, so it echoes the input as its "output." The `summaryText` is set to `llmOutput`, so both become raw JSON.

**Fix needed:** Primarily fixed by #18 (`PropagatorSerialization` compaction). Additionally, add a guard in the propagation execution path: if the serialized input exceeds a size threshold (e.g. 20KB), truncate or summarize before passing to the haiku propagator. Also consider a fallback in `AiPropagatorResult` storage: if `summaryText` starts with `{` and exceeds 500 chars, flag it as a failed analysis rather than storing raw JSON.

---

## 20. Stale episodic memory from prior goal leaks into current session

**Problem:** The `decomposePlanAndCreateWorkItems` ACTION_RESPONSE propagator flagged a temporal inconsistency: the planning orchestrator was about to dispatch planning agents, but the episodic memory system contained `FINAL_STATUS.md` claiming implementation was already COMPLETE from a prior session (2026-03-18). The propagator correctly asked: "Should planning agents proceed, or verify whether implementation is already complete?"

**Root cause:** Episodic memory from a previous goal execution (possibly the duplicate goal ak:01KM1NMADTF1A8MKG3HYT2E291 or a prior session) was not cleared or scoped when the new goal started. The memory system does not partition by goal ID, so stale artifacts from prior runs leak into the current goal's context.

**Fix needed:** (1) Scope episodic memory by goal ID so prior goal artifacts don't contaminate new goals. (2) On goal start, either clear or archive prior goal memory, or at minimum mark it with the source goal ID so agents can distinguish current vs prior. (3) Consider adding a goal-start propagator that validates episodic memory state against the current workflow phase.

---

## 21. Propagator confuses ACTION_REQUEST vs ACTION_RESPONSE — expects result in request-stage item

**Problem:** One `runPlanningAgent` ACTION_REQUEST propagation item produced the summary: "Missing planning agent result in propagation context—expected agentResult with findings/tickets but received only request." The propagator was analyzing the request *before* the agent ran, but its analysis assumed a result should already be present.

**Root cause:** The propagator prompt/instructions do not clearly distinguish between ACTION_REQUEST (pre-execution, should analyze the request being sent TO the agent) and ACTION_RESPONSE (post-execution, should analyze what the agent returned). The same propagator registration fires on both stages, and the haiku model doesn't always understand which stage it's in.

**Fix needed:** (1) Include explicit stage context in the propagator prompt: "You are analyzing an ACTION_REQUEST — this is the input being sent to the agent. The agent has not run yet. Do not expect results." vs "You are analyzing an ACTION_RESPONSE — this is what the agent returned." (2) Consider separate propagator registrations for request vs response stages with different system prompts.

---

## 22. Prompt-health-check propagators produce 4 consecutive false-positive deadlock escalations

**Problem:** All 4 `prompt-health-check` items for the ORCHESTRATOR escalate with increasing severity: "Structural concerns" → "Workflow livelock" → "Critical deadlock" → "CATASTROPHIC: 5+ propagation cycles." The orchestrator was not actually deadlocked — it was functioning normally. Each propagator invocation saw the prior propagator's execution trace in the assembled prompt and misinterpreted it as evidence of a loop.

**Root cause:** Same as #9 (self-referential deadlock). The prompt-health-check propagator fires on every LLM call and includes the full assembled prompt. Prior propagator execution traces (which are part of the execution history) appear in subsequent health-check analyses. The haiku model counts these traces as "cycles" and escalates.

**Evidence from this run:** 4 items, all `ACTION_REQUEST` stage, all for `ORCHESTRATOR` source, all with ~32KB `propagationRequest`. Summaries escalate: "Structural and execution concerns" → "Workflow livelock: 3 times" → "Critical deadlock: 4th cycle" → "CATASTROPHIC: 5+ cycles."

**Fix needed (extends #9):** (1) Strip propagation execution history entries from the prompt content before passing to health-check propagators. (2) Add a maximum invocation count per node per action — after 2 health-check firings for the same node+action, skip further analysis. (3) The deduplication hash check in `PromptHealthCheckLlmCallDecorator.lastPromptHashByNode` is already implemented but didn't prevent this because each cycle's prompt is slightly different (it includes the new propagation trace from the prior cycle).

---

## 23. ~~Remove redundant UpstreamContext, PreviousContext, and their prompt contributor factories~~ **DONE** (2026-03-19)

**Status:** Fixed. All items 1-8 completed:
- Deleted `UpstreamContextPromptContributorFactory`, `PreviousContextPromptContributorFactory` (+ test)
- Deleted `PreviousContext` sealed interface (all 13 subtypes)
- Deleted 9 non-curation `UpstreamContext` subtypes (kept 3 collector subtypes)
- Removed `previousContext` field from all `AgentRequest` records in `AgentModels.java`
- Removed `upstreamContexts` and `previousContext` fields from `PromptContext`
- Removed upstream/previous extraction from `PromptContextFactory.build()`
- Removed `RequestEnrichment.PreviousContextFactory` and all `previousContext` enrichment code
- Updated `AgentModelMixin.java`, `ArtifactSerializationTest.java`, `WeAreHerePromptContributorTest.java`, `WorktreeAutoCommitService.java`, `WorktreeMergeConflictService.java`
- All tests pass (9/9 BUILD SUCCESSFUL)

Item 9 (removing `discoveryCuration`/`planningCuration`/`ticketCuration` from request records) deferred — `CurationOverrides` still uses them.

---

## 24. WorktreeSandboxPromptContributor has incomplete sentence in template

**Problem:** `WorktreeSandboxPromptContributorFactory.java:138` — the template ends with `"This is especially because"` followed by the closing `"""`. The LLM receives a dangling incomplete sentence in its prompt.

**Fix needed:** Either complete the sentence (e.g., explaining why the worktree path must be used instead of the repository path) or remove the dangling fragment entirely. The preceding sentence already explains the rationale.

---

## 25. Goal text triple-duplicated in orchestrator prompt

**Problem:** The full 1,617-char goal text appears 3 times in the assembled orchestrator prompt (28,567 chars total):
1. In the jinja template via `Goal: {{ goal }}`
2. In `curation-request-context-orchestratorrequest` via `Goal: <goalExtraction>` (line 1075-1078 of `CurationHistoryContextContributorFactory`)
3. In the same contributor's `Details:` line via `prettyPrint(HistoricalRequestSerializationCtx)` which itself includes the goal

That's ~4,850 chars of pure redundancy (~17% of the prompt).

**Root cause:** `RequestContextContributor.contribute()` emits both `Goal: <goalExtraction>` AND `Details: <prettyPrint(...)>`, and the prettyPrint of an `OrchestratorRequest` includes the goal in its output. For the orchestrator's own historical request, this is also redundant with the template's `Goal:` line.

**Fix needed:** (1) The `RequestContextContributor` should either emit the goal OR the details, not both (since details includes the goal). (2) For the current node's own request, the curation factory should skip emitting a `RequestContextContributor` since the template already provides the full context. (3) Consider stripping goal from `prettyPrint(HistoricalRequestSerializationCtx)` output since it's already emitted as a separate line.

---

## 26. Verbose submodule listing in worktree sandbox context (~1,700 chars for 25 entries)

**Problem:** The `worktree-sandbox-context` prompt contributor lists all 25 submodule worktrees with their full absolute paths and branch names. Every entry has the same derived branch (`main-bf95161c-...`). For orchestrators and collectors (which only route, never write files), this is pure noise. Even for ticket agents, most submodules (e.g., `proto`, `tracing_aspect`, `test_graph/sdk`) are irrelevant to the ticket being implemented.

**Fix needed:** (1) For non-ticket-agent nodes (orchestrators, dispatchers, collectors), either omit submodule details entirely or show only the main worktree path. (2) For ticket agents, filter submodules to only those relevant to the ticket's `relatedFiles`. (3) At minimum, de-duplicate the branch name — show it once rather than repeating it 25 times.

---

## 27. Discovery agent attempts to create files (BranchStateRepository.java) — haiku model

**Problem:** During the parallel-execution-with-branches goal run (nodeId `ak:01KM41APXWZ6TR6KNV13AX1PZN`), a discovery agent (nodeId `...FNWC/...8GAH`) attempted to create `BranchStateRepository.java` via `mcp__jetbrains__create_new_file`. Discovery agents are read-only; only ticket agents should write files. This is a repeat of issue #17.

**Root cause:** Haiku model does not consistently respect the phase boundary between discovery (read-only search) and ticket implementation (write). The discovery prompt may not emphasize the read-only constraint strongly enough for smaller models.

**Workaround:** Permission rejected (REJECT_ONCE). Corrective message sent to the specific discovery agent node: "You are a DISCOVERY agent — your role is READ-ONLY. You must NOT create, modify, or write any files."

**Fix needed:** Strengthen the discovery agent prompt to explicitly forbid file creation/modification tools. Consider adding a tool filter that blocks `create_new_file`, `replace_text_in_file`, `Write`, and `Edit` tools for discovery and planning agent sessions.

## 28. ~~AutoAiPropagatorBootstrap misses `runDiscoveryAgent` and `planTickets` layers~~ **DONE** (2026-03-19)

All 35 attachable layers now have both ACTION_REQUEST and ACTION_RESPONSE propagators after the record→class DTO conversion and redeploy.

## 29. ~~Manual propagator registration via API fails with "Name is null"~~ **DONE** (2026-03-19)

Fixed by converting `PropagatorRegistrationRequest` from a Java record to a `@Data` class with `@NoArgsConstructor`/`@AllArgsConstructor`. Jackson now deserializes all fields correctly. Removed `register_propagator.py` script (API works directly now).

## 30. Goal text duplicated ~4x across workflow phases (~2,400 tokens wasted per agent dispatch)

**Problem:** The full goal statement (~450 words, ~600 tokens) is repeated identically across multiple workflow contexts: Orchestrator, Discovery Orchestrator, Discovery Dispatch, and Discovery Agent. Prompt health propagator detected ~2,400 tokens of pure duplication.

**Root cause:** Each phase includes the full goal in the prompt context rather than referencing a centralized goal ID. The goal is passed through `propagationRequest` fields at every routing hop.

**Impact:** Token waste compounds with agent count — 3 discovery agents = ~7,200 wasted tokens; planning and ticket phases multiply further.

**Fix needed:** Introduce a goal reference mechanism: store goal text once (e.g., in session context), pass only a goal ID or shortened summary through subsequent phases. Sub-agents can look up full text when needed.

## 31. Discovery agent attempted to write files (ANALYSIS_GOAL_A_SUBMODULE_CONSTRAINTS.md) — rejected

**Problem:** During discovery phase, a discovery agent tried to create `ANALYSIS_GOAL_A_SUBMODULE_CONSTRAINTS.md` in the worktree sandbox. This was caught via permission request and rejected. A corrective message was sent. Related to outstanding #17 and #27.

**Root cause:** Discovery agent prompt may not sufficiently emphasize read-only constraint. The haiku model may especially struggle with this boundary.

**Workaround:** Controller rejected the write permission and sent corrective message. Discovery orchestrator then referenced the non-existent file in its subdomain focus.

**Fix needed:** Strengthen discovery agent prompt to include explicit "DO NOT CREATE FILES" instruction. Consider adding a filter policy to auto-reject Write/Edit tools for discovery agent nodes.

## 32. Prompt-health-check propagators continue producing false-positive deadlock escalations

**Problem:** During orchestrator onboarding phase, prompt-health-check propagators reported "SYSTEM FAILURE: Orchestrator infinite loop" and "CRITICAL workflow loop" when the orchestrator was actually progressing normally through its propagation evaluation cycles. This is a continuation of outstanding #9 and #22.

**Root cause:** The health-check propagator interprets normal propagation evaluation cycles as deadlocks. It sees repeated AI_FILTER_SESSION → runAiPropagator → ACTION_COMPLETED patterns and flags them without understanding that propagation cycles are expected behavior.

**Fix needed:** Teach the prompt-health-check propagator to distinguish between: (a) normal propagation evaluation cycles (expected), (b) actual workflow stalls (no new actions over extended period).

## 33. Interrupt resolution does not auto-resume WAITING_REVIEW dispatch node

**Problem:** After resolving an AGENT_REVIEW interrupt from a discovery agent via `POST /api/interrupts/resolve`, the discovery-dispatch node remained in WAITING_REVIEW state indefinitely. No pending interrupts or permissions were shown. Had to manually resume the dispatch node via `POST /api/agents/resume` to unblock the workflow.

**Root cause:** The interrupt resolution endpoint returns `status=RESOLVED` with a `resumeNodeId`, but the resume does not appear to propagate to the parent dispatch node that is waiting on the interrupt result.

**Workaround:** Use `POST /api/agents/resume` with the dispatch node ID after resolving interrupts.

**Fix needed:** Interrupt resolution should automatically resume the waiting dispatch node, or the dispatch should poll for interrupt resolution status.

**Update (same session):** Attempted `POST /api/agents/resume` on the dispatch node, the discovery agent node, and the discovery orchestrator node — all returned `status=queued` but the dispatch remained in WAITING_REVIEW. NODE_ERROR count increased from 7 to 9 after resume attempts. The workflow is fully stuck. This is a blocking issue for any workflow that uses AGENT_REVIEW interrupts from sub-agents.

**Root cause identified:** `EmitActionCompletedResultDecorator` runs during `transitionToInterruptState` via the `DispatchedAgentResultDecorator` list. When the interrupt's `review_resolution` LLM call returns a `DiscoveryAgentRouting` with `agentResult` populated, the decorator calls `BlackboardHistory.unsubscribe(eventBus, operationContext)` — treating the routing as a completed agent when it's actually mid-interrupt. This kills the dispatch subagent's event bus subscription, preventing the framework from delivering subsequent events. Combined with `WorktreeMergeResultDecorator` publishing false NODE_ERROR events (#34), this explains both the stall and the error count increase.

**Fix applied:** Added `if (context.agentRequest() instanceof AgentModels.InterruptRequest) { return t; }` guard to both `EmitActionCompletedResultDecorator.decorate(Routing)` and `WorktreeMergeResultDecorator.decorate(Routing)`. Both decorators now skip entirely when the decorator context indicates an interrupt request.

## 34. WorktreeMergeResultDecorator fires on read-only discovery agents — publishes false NODE_ERROR

**Problem:** After `transitionToInterruptState` returns a valid `DiscoveryAgentRouting`, `decorateRouting` runs `WorktreeMergeResultDecorator` which detects that child and trunk worktree IDs are the same and publishes a `NodeErrorEvent` + `MergePhaseCompletedEvent(successful=false)`. This happens because discovery agents share their parent's worktree (they're read-only), so childId == trunkId is expected — not an error.

**Impact:** (1) False NODE_ERROR events pollute the event stream and inflate error counts (the 7→9 increase in #33 may partly be from this). (2) The same issue will affect ticket agents and planning agents that share a parent worktree. (3) May contribute to the WAITING_REVIEW stall in #33 — the error events could confuse framework state tracking even though the decorator returns the routing.

**Root cause:** `WorktreeMergeResultDecorator.decorate(AgentResult)` at line 99 treats childId == trunkId as an error condition, but for dispatch subagents that share the parent worktree (all discovery agents, and potentially planning agents during interrupt handling), this is the normal expected state. The decorator does not distinguish between "same worktree because read-only agent" and "same worktree due to a bug."

**Why it only happens on deploy:** In local dev the worktree resolution may differ (e.g. null contexts skip the check). The deployed environment resolves worktree contexts from the database, so both child and trunk get populated with the same worktree ID, triggering the equality check.

**Fix applied:** Added `if (context.agentRequest() instanceof AgentModels.InterruptRequest) { return routing; }` guard at the top of `WorktreeMergeResultDecorator.decorate(Routing)`. The decorator now skips entirely when the decorator context indicates an interrupt request, avoiding false error events and no-op merge descriptors.

## 35. AI propagator (haiku) executes tools — `ls`, `mkdir`, `cp`, `pytest` — instead of only analyzing

**Problem:** Node `ak:01KM49DYWWD7YSPJ43NDT7GMP5/01KM49FNFQH33DYKKMWBY7S9PK` is the recycled **AI_PROPAGATOR** ACP session (claude-haiku-4-5), not a stale planning orchestrator. This propagator agent is requesting terminal permissions to run `ls`, `mkdir -p && cp -r`, and `pytest` commands. Propagators should only analyze and report — they should not execute tools or write files.

**Root cause:** The AI propagator's ACP session has tool access (Terminal). The propagation prompt or the ACP profile does not restrict tool use to analysis-only. The haiku model interprets its task as "implement suggestions" rather than "report observations."

**Workaround:** Rejected write permissions. Allowed the initial `ls` (read-only) before identifying the node as a propagator. The corrective message sent to this node was misdirected (thought it was a planning node).

**Fix needed:** Either (1) restrict the AI propagator's ACP profile to exclude Terminal/file-write tools, or (2) add explicit "DO NOT execute tools — report observations only" instruction to the propagation prompt template, or (3) use a sandbox profile that prevents tool execution for propagator sessions.

## 36. ~~RegisterBlackboardHistoryInputRequestDecorator silently drops first action's entry~~ **FIXED** (2026-03-20)

**Problem:** After reordering decorators (RegisterBlackboardHistory from 10,000→9,000), `kickOffAnyNumberOfAgentsForCodeSearch` failed on every retry with "Discovery orchestrator request not found." The OrchestratorRequest entry from `coordinateWorkflow` was never recorded in history because the BlackboardHistory didn't exist yet at order 9,000 — it was created by `EmitActionStartedRequestDecorator.ensureSubscribed()` at order 10,000.

**Root cause:** Decorator ordering dependency: `RegisterBlackboardHistoryInputRequestDecorator` (9,000) called `register()` which returned null when no history existed (first action of a run). The entry was silently dropped.

**Workaround:** None — caused infinite retry loop requiring kill + redeploy.

**Fix:** Added `ensureSubscribed` call in `RegisterBlackboardHistoryInputRequestDecorator.decorate()` before calling `register()`, so the history is created if needed regardless of execution order relative to `EmitActionStartedRequestDecorator`.

## 37. Discovery agent prompt payload bloat: goal duplicated 5x, ~6700 removable tokens

**Problem:** The prompt-health-check propagator reported that the discovery agent's request payload contains ~6700 removable tokens. The goal text is duplicated 5 times across different sections (Goal, Details, Curated Workflow Context, etc.). There are also duplicate Details fields, an unused Workflow Graph section, and verbose instructions that don't add decision-relevant value.

**Root cause:** Multiple prompt contributors independently inject the goal into different prompt sections without deduplication. The `OrchestratorCollectorRequestDecorator` and various `PromptContributor` beans each add their own copy of the goal context.

**Workaround:** The agent still functions correctly — just burns extra tokens per invocation.

**Fix needed:** Implement goal deduplication in prompt assembly. Either (1) have a single canonical goal section and reference it from other contributors, or (2) add a post-assembly deduplication pass that detects and removes duplicate goal blocks, or (3) make prompt contributors aware of what's already been contributed so they skip redundant content.

## 38. Prompt-health-check propagator produces false-positive "deadlock" and "out-of-distribution" escalations

**Problem:** The prompt-health-check propagator sees its own prior execution history in the blackboard and misinterprets propagation analysis cycles as a workflow deadlock. It also flags valid multi-agent dispatch (e.g. agent 2 starting after agent 1 completes) as "out-of-distribution workflow state" claiming implementation is already complete.

**Root cause:** The propagator lacks context about (1) its own recursive nature (analyzing prompts that include its own prior output) and (2) the multi-agent dispatch pattern where multiple agents are dispatched sequentially by the same dispatch action. Related to outstanding #22 and #32.

**Workaround:** Acknowledge and dismiss these propagation items. They are informational noise.

**Fix needed:** Either (1) exclude prompt-health-check's own output from the context it analyzes, or (2) add dispatch-awareness so it understands sequential multi-agent dispatch is normal, or (3) add a confidence threshold below which it suppresses escalation.

## 39. RemoveIntellij settings.local.json written too late — JetBrains MCP tools still available in agent sessions

**Problem:** Discovery agents request JetBrains MCP tools (`mcp__jetbrains__get_file_text_by_path`, `mcp__jetbrains__list_directory_tree`) despite `RemoveIntellij` writing a deny list to `.claude/settings.local.json` in the worktree. The tools appear as permission prompts rather than being auto-rejected.

**Root cause:** `RemoveIntellij` is an `LlmCallDecorator` (order -10,001) that writes the settings file during prompt assembly. However, the ACP/Claude Code session is started *before* the first LLM call, so the tool list is already loaded when `settings.local.json` is written. Claude Code likely reads `settings.local.json` at session startup, not on each tool invocation. Confirmed: both worktrees have the correct deny file, but agents still get offered JetBrains tools.

**Workaround:** Manually reject JetBrains tool permissions when they appear. The agents fall back to Find/Read/Terminal tools.

**Fix needed:** Write `.claude/settings.local.json` **before** the ACP session is started — either (1) move the deny-file write into the worktree creation step (`GitWorktreeService.createMainWorktree()`), or (2) make it a `WorktreeContextRequestDecorator` post-hook that runs before the ACP session init, or (3) pre-populate the settings file in the worktree template.

## 40. No `/api/workflow-graph/events` endpoint — event queries by type return 404

**Problem:** `GET /api/workflow-graph/events` and `POST /api/workflow-graph/events` both return 404. There is no endpoint to query workflow events filtered by event type (e.g. `ACTION_STARTED`, `NODE_ERROR`) for a given node. The controller scripts and skill docs reference patterns like filtering events by `eventType` but no such endpoint exists.

**Root cause:** The only event endpoints are under `/api/ui/nodes/events` (paginated, returns all event types) and `/api/ui/nodes/events/detail` (single event detail). Neither supports filtering by `eventType` in the request body. The `/api/ui/workflow-graph` endpoint returns aggregate stats (event type counts) but not the events themselves.

**Workaround:** Use `/api/ui/nodes/events` and filter client-side, or grep the application log for specific event patterns.

**Fix needed:** Add `POST /api/ui/nodes/events` support for an `eventType` filter parameter (e.g. `{"nodeId": "ak:...", "eventType": "NODE_ERROR", "limit": 10}`) so controller scripts can query specific event types without downloading all events or parsing logs.

## 41. Discovery agent attempts file edits — phase boundary violation (recurring)

**Problem:** During goal `ak:01KM4QQH8K1CR0EJEH1KGFE1VV`, a discovery agent (node `01KM4R6T38EFVFRJX0F60FGM8E`) requested `Edit` permission on `WorkflowGraphService.java` in the worktree. Discovery agents should be strictly read-only — they must not create, edit, or delete files.

**Root cause:** The discovery agent prompt does not include a hard constraint preventing file writes. The agent model interprets "analyze the codebase" as license to modify code. This is the same class of issue as outstanding #17, #27, #29, #35.

**Workaround:** Permission rejected (`REJECT_ALWAYS`). Corrective message sent via `POST /api/ui/quick-actions` (actionId `4515ca58`). Controller must continue monitoring for repeat write attempts from discovery agents.

**Fix needed:** Add an explicit system-prompt constraint to discovery agent prompts: "You are READ-ONLY. Do not request Edit, Write, or any file-modification tool calls." Alternatively, enforce at the decorator level by auto-rejecting write tool calls from nodes in discovery phase.

## 42. Discovery agent searches tmp repo path instead of its worktree sandbox

**Problem:** During goal `ak:01KM4QQH8K1CR0EJEH1KGFE1VV`, discovery agent #2 (node `01KM4RDKR03G6G8G1NJKKWAXCS`) requested `Find **/*.py` on path `/private/tmp/multi_agent_ide_parent/multi_agent_ide_parent/multi_agent_ide_python_parent` — the deployed tmp repo, not its assigned worktree (`/Users/hayde/.multi-agent-ide/worktrees/89a53ffe-...`). The agent escaped its sandbox boundary.

**Root cause:** The tmp repo path appears in files within the worktree (e.g., deploy scripts, `clone_or_pull.py` output, or config files that reference `/private/tmp/...`). The agent reads these paths during discovery and treats them as valid search targets. The `WorktreeSandboxPromptContributor` tells the agent which worktree to use, but does not explicitly forbid searching paths outside the worktree. The haiku model does not reliably infer the constraint.

**Workaround:** Permission rejected (`REJECT_ONCE`). Controller must continue monitoring for out-of-sandbox path access.

**Fix needed:** Add an explicit constraint to the sandbox prompt contributor: "You MUST only read files under your assigned worktree path. Do not access /private/tmp/, the source IDE project, or any other path outside the worktree." Alternatively, enforce at the permission gate by auto-rejecting tool calls targeting paths outside the agent's worktree root.

## 43. Propagation pattern summary for goal `ak:01KM4QQH8K1CR0EJEH1KGFE1VV`

**Observed patterns (18 propagation items, discovery phase):**

1. **Prompt-health-check self-referential loop** (5 items at goal start): Propagator saw its own prior output in execution history and escalated as "CRITICAL LOOP" / "deadlock". Same class as #9, #22, #32, #38. Burned 5 cycles before the orchestrator could route forward.

2. **Goal duplication flagged 3x**: Each discovery agent request triggered the same finding — goal duplicated 5-6x, ~5400 duplicate chars. Valid finding but redundantly reported. Same as #30, #37.

3. **Scope ambiguity flagged 3x**: Each discovery agent request triggered scope mismatch — goal mixes design directives with discovery tasks. Valid and explains why agent #1 went off-domain.

4. **Worktree context switch false positive** (1 item): Child worktree flagged as "significant deviation." Expected behavior for dispatched subagents.

5. **Agent #1 returned out-of-domain results**: Analyzed SKILL.md and standard_workflow.md (documentation) instead of `.gitmodules` and `git config` (actual git configuration). Propagator correctly caught this.

6. **Agent #2 searched outside sandbox** (outstanding #42): Tried to glob the tmp repo path.

**Root cause for agent quality issues:** The goal statement includes 5 design/implementation directives (~250 tokens) that belong in the planning phase, not discovery. Agents conflate "analyze current state" with "design new state." The subdomain focus is too weak to override the goal's prescriptive language.

## 44. Propagator registration requires all matcher fields despite appearing optional in OpenAPI

**Problem:** `POST /api/propagators/registrations` returns `"Name is null"` when `matcherKey`, `matcherType`, or `matcherText` are omitted from `layerBindings[]`. The OpenAPI spec does not mark these as required, and the error message is misleading (it's actually a `NullPointerException` from `Enum.valueOf(null)` in `FilterEnums.MatcherKey.valueOf(binding.getMatcherKey())`).

**Root cause:** `PropagatorRegistrationService.register()` at line 47-50 calls `FilterEnums.MatcherKey.valueOf(binding.getMatcherKey())` without null-checking. Java's `Enum.valueOf()` throws `NullPointerException("Name is null")` when given null.

**Workaround:** Always provide `matcherKey`, `matcherType`, and `matcherText` in every layer binding. Example: `"matcherKey": "NAME", "matcherType": "CONTAINS", "matcherText": "checkPromptHealth"`.

**Fix needed:** Add null-guard in `PropagatorRegistrationService.register()` before the `valueOf()` calls — use a default like `NAME`/`CONTAINS`/`""` when fields are null, or make them required in the OpenAPI schema.

## 45. OpenAPI spec shows wrong enum values for propagator layerBinding matchOn

**Problem:** The OpenAPI spec for `LayerBindingRequest.matchOn` shows only `CONTROLLER_ENDPOINT_RESPONSE` as an allowed value. The actual `PropagatorMatchOn` enum has `ACTION_REQUEST` and `ACTION_RESPONSE`. Using the OpenAPI-documented value fails.

**Root cause:** The `@Schema(allowableValues)` annotation on `LayerBindingRequest.matchOn` in the inner DTO class does not list the correct propagator match-on values, or the schema is being inherited from a different DTO (likely the filter `LayerBindingRequest` which uses `CONTROLLER_ENDPOINT_RESPONSE`).

**Workaround:** Use `ACTION_REQUEST` or `ACTION_RESPONSE` for propagator layer bindings (ignore OpenAPI suggestion).

**Fix needed:** Update the `@Schema` annotation on `PropagatorRegistrationRequest.LayerBindingRequest.matchOn` to list `ACTION_REQUEST, ACTION_RESPONSE`.

## 46. Structured output retry causes ticket agent path confusion and redundant edits

**Problem:** When the LLM fails to produce valid JSON for `TicketAgentRouting` or `CommitAgentResult` (returns empty content instead of JSON), the retry mechanism re-invokes the full LLM conversation. On retry, the LLM produces additional tool calls (file edits, compilation) instead of the required routing JSON. These spurious tool calls target wrong paths (e.g. the tmp repo instead of the worktree) because the agent loses context about its operating directory across retries.

**Observed in:** TICKET-001 had 3 retries for `CommitAgentResult` (03:57-04:01 UTC). TICKET-002 had 2+ retries for `TicketAgentRouting` (03:17-03:21 UTC) followed by the agent re-editing files in `/private/tmp/multi_agent_ide_parent/multi_agent_ide_parent/` instead of its worktree at `/Users/hayde/.multi-agent-ide/worktrees/f594bc08-...`.

**Root cause:** `LlmDataBindingProperties` retries on `MismatchedInputException: No content to map due to end-of-input`. The retry sends the full conversation history back to the LLM, which interprets it as "continue working" rather than "produce the structured JSON output now." The LLM then generates more tool-use calls with degraded path context.

**Workaround:** The code changes are already committed before the routing retry starts, so the redundant edits typically don't damage the repo (working tree is clean). But the retries waste tokens and time.

**Fix needed:** The retry mechanism should (a) strip prior tool-use turns from the retry prompt and only include the structured-output instruction, or (b) add a clear "produce JSON only, no tool calls" directive to the retry prompt, or (c) set `tool_choice: none` on retry attempts for routing/result bindings.

## 47. Replaced search_log.py with structured error_search.py + error_patterns.csv

**Problem:** `search_log.py` did not work at all — it failed silently or produced no useful output. Controller sessions had no reliable way to search runtime logs for known error patterns.

**Fix applied:** Removed `search_log.py`. Created `error_patterns.csv` (known error grep expressions with descriptions, 20 initial patterns) and `error_search.py` (primary error search tool). Summary mode (default) shows aggregate count, first/last timestamp, and description for each active pattern — avoids context overflow from large error dumps. Detail mode (`--type`) shows last N matches for a specific pattern. Raw mode (`--raw`) for ad-hoc grep. `--acp` flag for ACP error log. Updated all skill files (`debug/SKILL.md`, `SKILL_PARENT.md`, `controller/SKILL.md`, `standard_workflow.md`) to reference the new tool.

**How to maintain:** Add new rows to `error_patterns.csv` when recurring errors are discovered. Always use summary mode first to avoid context overflow, then drill into specific patterns with `--type`.

## 48. poll.py --subscribe did not return on activity — sat for full timeout

**Problem:** `poll.py --subscribe 120` ran for the full 120 seconds without detecting pending permissions, even though the `/api/ui/activity-check` endpoint returned `hasActivity: true` with 3 pending permissions when called manually.

**Root cause:** The subscribe loop on activity detection would poll, reset `elapsed = 0`, sleep, and loop again — never returning control to the caller. If activity persisted (e.g., unresolved permissions), it would loop indefinitely printing full polls. If the activity appeared briefly, the 5s tick could miss it entirely.

**Fix applied:** Changed subscribe loop to `return` immediately after detecting activity and running a full poll. The caller can then take action (approve permissions, review propagations) and restart subscribe for the next window. This matches the intended workflow: subscribe detects → poll prints → caller acts → caller restarts subscribe.

## 49. MCP self-server registers zero tools — topology tools not visible to ACP agents

**Problem:** `call_controller`, `list_agents`, and `call_agent` (from `AgentTopologyTools`) are not visible to ACP agents (Claude Code). Integration test confirmed: agent listed all available tools and none of the topology tools appeared. Production log also shows `"No tool methods found in the provided tool objects: []"`.

**Root cause:** `SpringMcpConfig.tools()` bean injects `List<ToolCarrier>` and filters with `hasToolMethod()` using `getDeclaredMethods()`. The filtered list is empty — meaning either the `ToolCarrier` beans aren't being injected or `hasToolMethod()` is rejecting them (possibly due to CGLIB proxy subclassing where `getDeclaredMethods()` misses annotations on the superclass). Diagnostic logs added to `SpringMcpConfig.tools()` to identify which case.

**Impact:** Critical — no agent can call `call_controller` for justification dialogues. The entire review/justification workflow is broken.

**Diagnostic logs added:**
- `SpringMcpConfig.tools()`: logs count and class names of injected `ToolCarrier` beans, and count after `hasToolMethod` filter
- `DefaultLlmRunner.applyToolContext()`: logs all tools in the `ToolContext` per LLM call
- `AgentTopologyTools.callController()`: logs START/END with sessionId

**Fix needed:** Determine why `hasToolMethod` returns false for `AgentTopologyTools`. If CGLIB proxy issue, change `getDeclaredMethods()` to `getMethods()` or use `AopUtils.getTargetClass()`. If injection issue, check Spring bean ordering.

## 50. Discovery agent returns prose instead of JSON after call_controller — retry loop

**Problem:** After the discovery agent's `call_controller` permission is approved and the tool executes, the LLM returns prose text (`"I'll conduct a comprehensive discovery analysis of the Java Worktree Infrastructure..."`) instead of the required `DiscoveryAgentRouting` JSON. The `FilteringJacksonOutputConverter` fails to parse this, triggering retry logic (attempt 1 of 10). On retry, the agent gets a fresh prompt context and starts over — calling `call_controller` again with an empty sessionId, which creates a second conversation that doesn't get a controller response.

**Log evidence:**
```
18:00:24.663 ERROR FilteringJacksonOutputConverter - Could not parse the given text to the desired target type: "I'll conduct a comprehensive discovery analysis..." into class AgentModels$DiscoveryAgentRouting
18:00:24.664 WARN  LlmDataBindingProperties - LLM invocation DiscoveryDispatchSubagent.runDiscoveryAgent-DiscoveryAgentRouting: Retry attempt 1 of 10 due to: Invalid LLM return
17:59:49.044 INFO  AgentTopologyTools - call_controller START — sessionId= justification=## Discovery Analysis Justification
```

**Root cause:** Same class of issue as the orchestrator prose-output bug fixed in `_review_justification.jinja`. The discovery agent's prompt context after `call_controller` completes doesn't clearly instruct the LLM to return structured JSON. The jinja fix helps for the justification conversation itself, but the underlying issue is that after `call_controller` returns (as a tool result), the LLM sees the tool result and produces a text response rather than the required structured output.

**Impact:** Discovery agent gets stuck in retry loop. Each retry re-invokes the full agent action, which calls `call_controller` again, creating orphaned conversations.

**Workaround:** None currently — the retry will eventually exhaust (10 attempts) and the action will fail.

**Fix needed:** Investigate why the LLM produces text after receiving the `call_controller` tool result. Possible fixes: (1) add explicit system-level instruction in the discovery agent prompt that tool results should not change the output format obligation, (2) ensure `call_controller` tool result includes a reminder about required output format, (3) investigate whether the retry mechanism properly preserves the conversation context including the `call_controller` exchange.
