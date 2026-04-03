---
name: multi_agent_ide_validation
description: Validation skill for test surface analysis, invariant checking, and exploration-driven testing. Used by the ticket collector during the validation phase and by the controller for test execution oversight.
---

## Purpose

This skill drives the validation phase of the controller workflow. It is loaded by the **ticket collector** after ticket agents have completed their work, and by the **controller** when overseeing test execution and reviewing proposed test changes.

The validation process treats testing as a **tensor decomposition** problem: SURFACE.md defines all user-facing behaviors of the application (what the application does), INVARIANTS.md recursively decomposes each behavior into testable invariants (each invariant further decomposable into sub-invariants), and EXPLORATION.md identifies unknown unknowns through targeted investigation of trace data. Tests are then written to cover the invariants, and validated by logging and analyzing trace data.

---

## Key Files

| File | Location | Purpose |
|------|----------|---------|
| SURFACE.md | `multi_agent_ide_java_parent/multi_agent_ide/src/test/resources/SURFACE.md` | All user-facing behaviors of the application — the complete behavioral surface, not test cases |
| INVARIANTS.md | `multi_agent_ide_java_parent/multi_agent_ide/src/test/resources/INVARIANTS.md` | Recursive decomposition of each surface behavior into testable invariants, each invariant further decomposable into sub-invariants |
| EXPLORATION.md | `multi_agent_ide_java_parent/multi_agent_ide/src/test/resources/EXPLORATION.md` | Investigation entry points for discovering things we don't know we don't know |
| Test traces | `multi_agent_ide_java_parent/multi_agent_ide/test_work/` | Markdown trace dumps from integration test runs (graphs, events, blackboard) |
| Validation test script | `multi_agent_ide_java_parent/tests-multi-agent-ide-validation.sh` | **~30 minutes.** Full pipeline test runner with validation logging. Logs to `multi-agent-ide-validation.log` |
| Validation log | `<PARENT_DIR>/multi-agent-ide-validation.log` | Tail this file to monitor test progress while the validation script runs |
| Logback config | `multi_agent_ide_java_parent/multi_agent_ide/src/main/resources/logback-multi-agent-ide-validation.xml` | Validation-specific logback config, writes to `multi-agent-ide-validation.log` |

## Executables

See `executables/reference.md` for the full index of validation scripts and key file locations.

Before writing any inline analysis code, check `executables/reference.md` — if a matching script exists, use it. If no match exists, write a new script to `executables/`, add a row to `reference.md`, then invoke it.

## Workflows

See `workflows/reference.md` for the workflow index.

**Follow `workflows/validation_workflow.md` for the canonical step-by-step validation process.** This is the ticket collector's playbook — it covers surface review, invariant mapping, exploration, test analysis, yielding proposals to the controller via `call_controller`, applying approved changes, running tests, post-test analysis, and yielding the final analysis back to the controller.

---

## Testing Matrix

**In the normal validation workflow, run the validation test script.** It runs the full pipeline with dedicated logging and takes approximately 30 minutes:

| Test suite | Command | Approximate duration | Bash timeout |
|------------|---------|---------------------|--------------|
| **Validation pipeline (default)** | `cd multi_agent_ide_java_parent && ./tests-multi-agent-ide-validation.sh` | **~30 minutes** | 900000ms |
| Unit tests only | `LOGGING_CONFIG=classpath:logback-multi-agent-ide-validation.xml ./gradlew :multi_agent_ide_java_parent:multi_agent_ide:test` | ~3 minutes | 180000ms |
| Spring integration only | `LOGGING_CONFIG=classpath:logback-multi-agent-ide-validation.xml ./gradlew :multi_agent_ide_java_parent:multi_agent_ide:test -Pprofile=integration` | ~5-10 minutes | 600000ms |
| ACP integration | `LOGGING_CONFIG=classpath:logback-multi-agent-ide-validation.xml ./gradlew :multi_agent_ide_java_parent:multi_agent_ide:test -Pprofile=acp-integration` | ~60 minutes | 3600000ms |
| ACP chat model | `LOGGING_CONFIG=classpath:logback-multi-agent-ide-validation.xml ./gradlew :multi_agent_ide_java_parent:acp-cdc-ai:test -Pprofile=acp-integration` | ~3 minutes | 3600000ms |

The validation script (`tests-multi-agent-ide-validation.sh`) sets `LOGGING_CONFIG=classpath:logback-multi-agent-ide-validation.xml` and runs unit + integration tests across all modules. All output goes to `<PARENT_DIR>/multi-agent-ide-validation.log`. Tail this file to monitor progress while the script runs:

```bash
tail -f <PARENT_DIR>/multi-agent-ide-validation.log
```

For individual (targeted) runs, prepend `LOGGING_CONFIG=classpath:logback-multi-agent-ide-validation.xml` to the Gradle command as shown above.

### Notes

- ACP chat model tests matter only when working on base-level ACP/Claude Code or Codex.
- Skip tests that don't cover your change surface.
- For `multi_agent_ide` integration tests: must use `-Pprofile=integration`, otherwise `**/integration/**` is excluded.
- For ACP chat model tests in `acp-cdc-ai`: must use `-Pprofile=acp-integration`.
- Do not run in parallel sub-agents, with async tasks, or as background tasks — poll manually every 5-10 mins when running long-running tests.

### CRITICAL: Use `--info` only when piping Gradle output to a file
Do not add `--info` for interactive runs. Use it only when redirecting to a log file.

---

## The Validation Framework

### Surface → Invariants → Tests

SURFACE.md captures all user-facing behaviors of the application — what the application does from a user perspective. This is the complete behavioral surface, not a list of test cases.

INVARIANTS.md recursively decomposes each surface behavior into testable invariants. Each invariant is a property that must hold for that behavior to be correct. Each invariant can be further decomposed into sub-invariants, forming a test tensor — a multi-dimensional breakdown of behavior into finer and finer grained testable properties.

Tests are then written to cover the leaf invariants. We validate by logging trace data during test execution and analyzing it against the invariants.

```
SURFACE.md (application behaviors — what the application does from a user perspective)
  └── INVARIANTS.md (invariants per behavior — testable properties that must hold)
       └── Sub-invariants (finer-grained invariants decomposed from the parent)
            └── ... (recursive until desired granularity)
                 └── Tests (code that covers and validates the leaf invariants)
```

### Exploration

EXPLORATION.md defines entry points for discovering things we don't know we don't know. Each entry point describes where to look in the trace data, what question to ask, and what a finding might lead to.

Exploration is a feedback loop: findings from exploration feed back into SURFACE.md (new behaviors discovered) and INVARIANTS.md (new invariants needed). This means the validation process is iterative — exploration can expand the surface, which expands the invariants, which may reveal new exploration points.

```
EXPLORATION.md (cross-cutting probes for unknown unknowns)
  └── Findings feed back into SURFACE.md and INVARIANTS.md
```

### Trace Data

Integration tests produce markdown trace dumps to `test_work/` — graphs, events, and blackboard snapshots. These traces are the evidence used to validate invariants and investigate exploration points. The tracing code (the code that captures data during test execution) must be sufficient to cover all invariants and exploration entry points. If it isn't, trace writer changes are proposed before running tests.

### Adding New Dimensions

When adding a new dimension to an existing invariant, consider whether it should be:
- A refinement of the existing invariant (update in place)
- A new sub-invariant (new entry referencing the parent)
- A new exploration entry point (if the dimension is speculative)

---

## Ticket Collector Validation Workflow

**Follow `workflows/validation_workflow.md` for the step-by-step process.** The workflow covers: surface review → invariant mapping → exploration → test analysis → yield proposals to controller via `call_controller` → apply approved changes → run tests → post-test analysis → yield final analysis.

## Controller Review Gates

Controller review gates for the validation phase are defined in the ticket collector checklist: `multi_agent_ide_controller/conversational-topology/checklist-ticket-collector.md` (steps 15–22).
