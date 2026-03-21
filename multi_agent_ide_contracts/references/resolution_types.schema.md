# Resolution Type Enums and Shapes

These types are used in request/response bodies but their enum values are not always fully discoverable from OpenAPI alone (they live in Kotlin/Java enums that may not have `@Schema` enum documentation). This file is the fallback reference.

## Overriding principle

**Validate before use, update if out of sync.** Before relying on any enum or shape documented here, read the source file listed. If the source has diverged, update this file to match, then proceed.

## Interrupt resolution types

| Source file | `acp-cdc-ai/src/main/kotlin/com/hayden/acp_cdc_ai/permission/IPermissionGate.kt` (line ~17, `enum class ResolutionType`) |
|------------|---|

Values: `APPROVED`, `REJECTED`, `CANCELLED`, `FEEDBACK`, `RESOLVED`

Used by: `POST /api/interrupts/resolve` (`resolutionType` field)

## Permission option types

| Source file | `com.agentclientprotocol.model.PermissionOptionKind` (ACP SDK — external dependency) |
|------------|---|

Values: `ALLOW_ONCE`, `ALLOW_ALWAYS`, `REJECT_ONCE`, `REJECT_ALWAYS`

Used by: `POST /api/permissions/resolve` (`optionType` field, plus optional `note` string). Controller switch in `PermissionGateService.performPermissionResolution()`.

The `note` field (default `""`) is sent to the AI agent as a message when rejecting (`REJECT_ONCE`/`REJECT_ALWAYS`), explaining why the tool call was denied so the agent can adjust its approach.

## Propagation resolution types

| Source file | `multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/propagation/model/PropagationResolutionType.java` |
|------------|---|

Values: `ACKNOWLEDGED`, `APPROVED`, `REJECTED`, `DISMISSED`, `FEEDBACK`

Used by: `POST /api/propagations/items/{itemId}/resolve` (`resolutionType` field)

## Interrupt types

| Source file | `acp-cdc-ai/src/main/java/com/hayden/acp_cdc_ai/acp/events/Events.java` (line ~68, `enum InterruptType`) |
|------------|---|

Values: `HUMAN_REVIEW`, `AGENT_REVIEW`, `PAUSE`, `STOP`, `BRANCH`, `PRUNE`

Used by: `POST /api/interrupts` (`interruptType` field)

## InterruptResult (review result shape)

| Source file | `acp-cdc-ai/src/main/kotlin/com/hayden/acp_cdc_ai/permission/IPermissionGate.kt` (line ~46, `data class InterruptResult`) |
|------------|---|

```kotlin
data class InterruptResult(
    val contextId: ArtifactKey? = null,
    val assessmentStatus: ResolutionType? = null,
    val feedback: String? = null,
    val suggestions: List<String> = emptyList(),
    val contentLinks: List<String> = emptyList(),
    val output: String? = null
)
```

Used by: `POST /api/interrupts/resolve` (`reviewResult` field)

## AI propagator question answer shape

| Source file | `multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/agent/AgentModels.java` (line ~1015, `record InterruptResolution`) |
|------------|---|

```java
record InterruptResolution(
    Map<String, String> selectedChoices,
    Map<String, String> customInputs,
    Map<String, Boolean> confirmations
)
```

Used by: `POST /api/interrupts/resolve` — serialized as JSON string in the `resolutionNotes` field when answering AI propagator `AskUserQuestionTool` escalations.

## Filter layer binding enums

| Source | Not a single file — derived from `PolicyRegistrationRequest` and `FilterLayerBinding` model classes |
|--------|---|

These enums are used in filter registration request bodies. They may appear in OpenAPI but the semantic meaning is documented here:

| Enum field | Values | Meaning |
|-----------|--------|---------|
| `matcherKey` | `NAME`, `TEXT` | What field on the domain object to match against |
| `matcherType` | `REGEX`, `EQUALS` | How to compare `matcherText` |
| `matchOn` | `GRAPH_EVENT`, `PROMPT_CONTRIBUTOR` | Which domain object type |
| `layerType` | `WORKFLOW_AGENT`, `WORKFLOW_AGENT_ACTION`, `CONTROLLER`, `CONTROLLER_UI_EVENT_POLL` | Layer type metadata |

### matcherKey behavior

| Value | When `matchOn=GRAPH_EVENT` | When `matchOn=PROMPT_CONTRIBUTOR` |
|-------|---------------------------|----------------------------------|
| `NAME` | GraphEvent class simple name (e.g. `AddMessageEvent`) | Contributor bean/logical name (e.g. `debug-context`) |
| `TEXT` | String payload from invoking integration surface | Contributor template/static text content |
