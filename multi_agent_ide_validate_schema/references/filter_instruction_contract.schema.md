# Filter Instruction Contract (Python Executor)

This is a contract between the Java `PathFilter` and external Python/binary executor scripts. It is **not** exposed via OpenAPI — this is the only authoritative documentation.

## Overriding principle

**Validate before use, update if out of sync.** Before relying on any shape documented here, read the source files listed below. If the source has diverged, update this file to match, then proceed.

## Source files

| Type | Source file |
|------|-----------|
| `Instruction` (sealed interface, JSON discriminator `op`) | `acp-cdc-ai/src/main/java/com/hayden/acp_cdc_ai/acp/filter/Instruction.java` |
| `FilterEnums` (InstructionOp, PathType, MatcherType) | `acp-cdc-ai/src/main/java/com/hayden/acp_cdc_ai/acp/filter/FilterEnums.java` |
| `Path` (sealed interface, discriminator `pathType`) | `acp-cdc-ai/src/main/java/com/hayden/acp_cdc_ai/acp/filter/path/Path.java` |
| `InstructionMatcher` | `acp-cdc-ai/src/main/java/com/hayden/acp_cdc_ai/acp/filter/InstructionMatcher.java` |

## Instruction JSON schema

External Python filter scripts must return a bare JSON array of instructions (not wrapped in an envelope). `[]` means passthrough/no-op.

```json
[
  {
    "op": "REMOVE | REPLACE | SET | REPLACE_IF_MATCH | REMOVE_IF_MATCH",
    "targetPath": { "pathType": "REGEX | JSON_PATH | MARKDOWN_PATH", "expression": "string" },
    "matcher": { "matcherType": "REGEX | EQUALS", "value": "required for *_IF_MATCH ops" },
    "value": "required for REPLACE/SET/REPLACE_IF_MATCH",
    "order": 0
  }
]
```

## Enum values

| Enum | Values | Source field |
|------|--------|------------|
| `InstructionOp` | `REPLACE`, `SET`, `REMOVE`, `REPLACE_IF_MATCH`, `REMOVE_IF_MATCH` | `FilterEnums.InstructionOp` |
| `PathType` | `REGEX`, `JSON_PATH`, `MARKDOWN_PATH` | `FilterEnums.PathType` |
| `MatcherType` | `REGEX`, `EQUALS` | `FilterEnums.MatcherType` |

## Instruction subtypes (from `@JsonSubTypes`)

| `op` value | Record fields | Notes |
|-----------|---------------|-------|
| `REPLACE` | `targetPath`, `value`, `order` | Replaces value at path |
| `SET` | `targetPath`, `value`, `order` | Sets value, creating if needed |
| `REMOVE` | `targetPath`, `order` | Removes content at path |
| `REPLACE_IF_MATCH` | `targetPath`, `matcher`, `value`, `order` | Conditional replace |
| `REMOVE_IF_MATCH` | `targetPath`, `matcher`, `order` | Conditional remove |

## Path semantics

- `REGEX` — Java regex against the raw string payload
- `JSON_PATH` — standard JsonPath; root is `$`
- `MARKDOWN_PATH` — heading-scope selectors like `#`, `## Section`, `### Subsection`; root is `#`

## Executor environment

- External `PYTHON` and `BINARY` executors launch with `filter.bins` as subprocess cwd
- In the tmp-repo workflow, `filter.bins` resolves to `<tmp-repo>/multi_agent_ide_java_parent/multi_agent_ide/bin` (from `{{PROJ_DIR}}`)
- Create that directory before testing external executors
