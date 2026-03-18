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

