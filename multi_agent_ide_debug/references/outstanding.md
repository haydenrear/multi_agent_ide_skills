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

**Problem:** Sending `SEND_MESSAGE` with "STOP" to an agent node doesn't reliably stop it. The LLM may return immediately with an unparseable response, causing the framework to retry.

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
