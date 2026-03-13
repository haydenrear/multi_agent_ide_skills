# Multi-Agent IDE Skills

Skills for the multi_agent_ide system. Each skill is self-contained with a `SKILL.md`, and most include `references/`, `executables/`, and/or `workflows/` subdirectories.

Load skills on demand — they are designed to be narrow and composable. The controller skill is the canonical entry point for active workflows; it references the others.

## Skills

| Skill | Purpose |
|-------|---------|
| `multi_agent_ide_controller` | **Primary entry point.** Standard controller loop, polling, interrupt/permission resolution, propagation acknowledgement, review route-back. References the other skills for supporting context. |
| `multi_agent_ide_api` | Swagger/OpenAPI access, schema filtering via Python, quick reference for all REST endpoints. Fallback when an endpoint behaves unexpectedly. |
| `multi_agent_ide_debug` | Runtime debugging: log inspection, node error triage, exception knowledge base (ignore-exceptions, common-exceptions), reusable executables library. |
| `multi_agent_ide_deploy` | Clone/pull to `/tmp`, boot the application, manage profiles and deploy restarts. |
| `multi_agent_ide_ui_test` | UI state snapshot testing via `UiStateSnapshot`. Covers the shared server-side UI abstraction used by both TUI and web renderers. |
| `multi_agent_ide_contracts` | Internal contract reference for types that live below the OpenAPI surface: the `Instruction` sealed interface, resolution/permission enums, propagation resolution types, AI filter/propagator/transformer request shapes. Each reference includes source file provenance and must be kept in sync with the Java/Kotlin source. |

## Design notes

- **Executables as a promotion pipeline**: ad-hoc Python scripts in `executables/` are the first step toward promoting logic into filters (suppress/modify events), transformers (reshape API responses), or propagators (escalate OOD signals). Write to `executables/` first; promote when proven.
- **Propagators** extract out-of-domain signals from agent execution and escalate them. The QA tool (`QuestionAnswerInterruptRequest`) is the acknowledgement mechanism — the controller confirms awareness or provides structured input.
- **Filters, transformers, propagators** are all registered via REST (`/api/filters`, `/api/transformers`, `/api/propagators`) and their execution records are queryable. See `multi_agent_ide_api` for the full schema.
- **OpenAPI is the primary documentation source** for all REST endpoint shapes. `multi_agent_ide_contracts` covers only what OpenAPI cannot: sealed interfaces, internal enum semantics, and serialized sub-shapes.
