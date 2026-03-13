---
name: multi_agent_ide_validate_schema
description: Centralized reference for API schemas that cannot be retrieved from OpenAPI — filter instruction contracts, resolution type enums, and internal shapes. Provides source provenance and validation instructions to keep schemas in sync.
---

Use this skill to retrieve and validate schemas that are **not available from the OpenAPI/Swagger endpoint**. For all REST endpoint schemas (paths, request/response bodies), use the live Swagger UI at `http://localhost:8080/swagger-ui.html` or `api_schema.py` from the `multi_agent_ide_api` skill instead.

## Overriding principle

**Validate before use, update if out of sync.** Every schema documented in this skill's `references/` files includes the source file it was derived from. Before relying on any documented shape or enum:

1. Read the source file listed in the schema reference
2. Compare against the documented values
3. If they differ, **update the schema reference file to match the source**, then proceed
4. Do not silently use stale schemas — they will cause runtime failures

This principle applies to every `references/*.schema.md` file in this skill.

## What belongs here (and what doesn't)

**Belongs here** — schemas that cannot be discovered from the running OpenAPI spec:
- The `Instruction` sealed interface contract for Python/binary filter executors
- Kotlin/Java enum values that may not be fully documented in OpenAPI `@Schema` annotations
- Internal data shapes used in serialized JSON strings (e.g. `InterruptResolution` serialized inside `resolutionNotes`)
- Semantic meaning of enum values that OpenAPI can list but not explain (e.g. `matcherKey` behavior)

**Does not belong here** — use Swagger/OpenAPI for:
- REST endpoint paths, methods, request/response body shapes
- Controller-level documentation
- Anything the live `/v3/api-docs` endpoint can provide

## Schema references

| Reference file | What it covers | Key source files |
|---------------|----------------|-----------------|
| `references/filter_instruction_contract.schema.md` | `Instruction` JSON schema for Python executor scripts, path types, matcher types | `Instruction.java`, `FilterEnums.java`, `Path.java` |
| `references/resolution_types.schema.md` | Resolution type enums (interrupt, permission, propagation), `InterruptResult` shape, AI propagator answer shape, filter layer binding enums | `IPermissionGate.kt`, `PropagationResolutionType.java`, `Events.java`, `AgentModels.java` |

## Source file locations

All paths relative to `multi_agent_ide_java_parent/`:

| Source | Path |
|--------|------|
| `Instruction.java` | `acp-cdc-ai/src/main/java/com/hayden/acp_cdc_ai/acp/filter/Instruction.java` |
| `FilterEnums.java` | `acp-cdc-ai/src/main/java/com/hayden/acp_cdc_ai/acp/filter/FilterEnums.java` |
| `Path.java` | `acp-cdc-ai/src/main/java/com/hayden/acp_cdc_ai/acp/filter/path/Path.java` |
| `InstructionMatcher.java` | `acp-cdc-ai/src/main/java/com/hayden/acp_cdc_ai/acp/filter/InstructionMatcher.java` |
| `IPermissionGate.kt` | `acp-cdc-ai/src/main/kotlin/com/hayden/acp_cdc_ai/permission/IPermissionGate.kt` |
| `Events.java` | `acp-cdc-ai/src/main/java/com/hayden/acp_cdc_ai/acp/events/Events.java` |
| `PropagationResolutionType.java` | `multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/propagation/model/PropagationResolutionType.java` |
| `AgentModels.java` | `multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/agent/AgentModels.java` |
