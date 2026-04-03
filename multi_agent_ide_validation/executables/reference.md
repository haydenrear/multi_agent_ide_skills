# Validation Executables Reference

Scripts in this directory are written and maintained during validation sessions. Before writing a new script, check this index — if a matching script exists, use it (and improve it if needed).

## Key File Locations

| File | Path | Purpose |
|------|------|---------|
| SURFACE.md | `multi_agent_ide_java_parent/multi_agent_ide/src/test/resources/SURFACE.md` | All user-facing application behaviors — the complete behavioral surface |
| INVARIANTS.md | `multi_agent_ide_java_parent/multi_agent_ide/src/test/resources/INVARIANTS.md` | Recursive invariant decomposition of each surface behavior |
| EXPLORATION.md | `multi_agent_ide_java_parent/multi_agent_ide/src/test/resources/EXPLORATION.md` | Investigation entry points for unknown unknowns |
| Test traces | `multi_agent_ide_java_parent/multi_agent_ide/test_work/` | Markdown trace dumps (graphs, events, blackboard) |
| Validation test script | `multi_agent_ide_java_parent/tests-multi-agent-ide-validation.sh` | **~30 min.** Full pipeline with validation logging |
| Validation log | `<PARENT_DIR>/multi-agent-ide-validation.log` | Tail to monitor test progress |
| Logback config | `multi_agent_ide_java_parent/multi_agent_ide/src/main/resources/logback-multi-agent-ide-validation.xml` | Validation logback, writes to `multi-agent-ide-validation.log` |

## Scripts

| Script | Description |
|--------|-------------|
| — | *No scripts yet. Add validation analysis scripts here as they are developed during sessions.* |

### Planned scripts (add these as needed during validation sessions)

- **surface_diff.py** — Compare current code changes against SURFACE.md, identify new behaviors not yet captured as scenarios
- **invariant_check.py** — Parse trace data from `test_work/` and validate invariants from INVARIANTS.md against the traces
- **exploration_scan.py** — For each EXPLORATION.md entry point, scan trace data and report findings
- **coverage_report.py** — Cross-reference SURFACE.md coverage status against actual test files, produce a gap report
