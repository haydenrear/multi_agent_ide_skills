# Validation Workflow

This is the canonical workflow for the ticket collector's validation phase. It is injected by the controller at checklist step 15 (START_VALIDATION) in `checklist-ticket-collector.md`.

This workflow describes the ticket collector's responsibilities. Controller review gates and user approval steps are handled by the controller's checklist — not this document.

---

## Step 1 — Review the Surface

Read SURFACE.md, INVARIANTS.md, and EXPLORATION.md. Read the code changes from the ticket agents (worktree commits, `git diff`).

For each changed file or module:
1. Does the change introduce a new high-level behavior not yet in SURFACE.md?
2. Does the change modify an existing behavior whose surface scenario needs updating?
3. **Include `skills/multi_agent_ide_skills` in this review** — skill file changes (new checklists, new workflows, new executables) are surface too

Identify where holes exist in SURFACE.md — behaviors that are present in the code but missing from the surface.

---

## Step 2 — Map Surface Holes to Invariant Holes

For each surface gap identified in Step 1:
1. Check INVARIANTS.md — does a corresponding invariant exist?
2. If an invariant exists but is too coarse, **decompose it** into sub-invariants (test tensor expansion — break the behavior into finer-grained testable dimensions)
3. If no invariant exists, draft one with: the invariant statement, which surface scenario(s) it applies to, and where to search in the trace data

For each existing invariant affected by the changes:
1. Does the invariant still hold with the new code?
2. Does it need additional sub-dimensions to cover the new behavior?

---

## Step 3 — Add Exploration Points

For each gap or new invariant from Steps 1-2:
1. Is there an aspect where we don't know what we don't know?
2. Draft an exploration entry point with: where to look, what question to ask, what a finding might lead to, why it matters

For existing exploration entry points:
1. Do the code changes affect any NOT_YET_INVESTIGATED entry points?
2. Should any investigated entry points be re-investigated given the new changes?

**This step may loop back to Step 1** — if an exploration question reveals a new behavior, add it to the surface.

---

## Step 4 — Analyze Integration Tests

Read the existing integration tests, in the multi_agent_ide_java_parent/multi_agent_ide/src/test/java/com/hayden/multiagentide/integration package, and how we're writing the trace data.

1. **Map proposed surface/invariant changes to test changes** — which tests need new assertions, which need new test methods
2. **Check trace data logging** — for each proposed invariant, verify the trace writer captures the fields needed to validate it
3. **If trace data is insufficient** — propose specific trace writer changes (file path, what to add)
4. **Propose specific test changes** — file paths, test method names, assertions to add or modify

---

## Step 5 — Yield Proposals to Controller

Use `call_controller` to yield back to the controller with your proposals. Include:

- **Surface proposals**: new/modified scenarios for SURFACE.md (scenario ID, description, priority, subsystem)
- **Invariant proposals**: new/modified invariants for INVARIANTS.md (invariant ID, statement, applicable scenarios, search location)
- **Exploration proposals**: new entry points for EXPLORATION.md (entry ID, where to look, question, why it matters)
- **Test change proposals**: specific integration test changes (file path, method name, what to assert)
- **Trace writer proposals**: any trace data logging changes needed
- **Ambiguities**: anything unclear about the surface that needs clarification

**Do NOT apply any changes yet.** Wait for the controller to review and approve.

---

## Step 6 — Apply Approved Changes

After the controller approves (via `call_controller` response), apply the changes:

1. Update SURFACE.md with approved surface scenarios
2. Update INVARIANTS.md with approved invariants
3. Update EXPLORATION.md with approved exploration entry points
4. Modify integration test files with approved test changes
5. Modify trace writer if approved

**Do NOT run the tests yet.** Use `call_controller` to yield back to the controller for review of the applied changes.

---

## Step 7 — Run Tests

After the controller approves the applied changes (via `call_controller` response with the testing matrix), run the specified test suites.

The controller's approval message will include:
- Which test suites to run (from the testing matrix in SKILL.md)
- Approximate durations and bash timeouts
- Which suites to skip based on change surface

For each test suite:
1. Run the suite
2. **The full validation pipeline takes ~30 minutes.** It may appear hung — this is normal. To verify progress, tail the validation log file at `<project-root>/multi-agent-ide-validation.log` (the root `multi_agent_ide_parent` directory — the one containing `settings.gradle.kts`). If the log file is still being written to, the tests are still running.
3. If failures occur — analyze, fix, re-run
4. Record which tests passed, which failed, what was fixed

---

## Step 8 — Post-Test Analysis

After tests pass (or known failures are documented):

1. **Re-read SURFACE.md** — verify coverage status is current given the new test results
2. **Re-read INVARIANTS.md** — validate each invariant against the new trace data in `test_work/`
3. **Investigate EXPLORATION.md** — for each relevant entry point, scan the new trace data and record findings
4. **Test the invariants with the analysis** — for each invariant marked PASS, verify you actually checked the trace data (not just assumed it passed)
5. If any invariant fails or exploration reveals something unexpected — document it and note whether it requires a code fix or a surface/invariant update

---

## Step 9 — Yield Final Analysis to Controller

Use `call_controller` to yield back to the controller with the final analysis. Include:

- **Test results**: which suites ran, pass/fail counts, any failures fixed
- **Invariant validation**: PASS/FAIL/NOT_YET_VALIDATED for each invariant, with evidence from trace data
- **Exploration findings**: INVESTIGATED/NOT_YET_INVESTIGATED for each entry point, with findings
- **Surface coverage update**: updated coverage status for each scenario
- **Remaining gaps**: any follow-up items or known issues

The controller will review this analysis for rigor and determine if it's sufficient to close the validation phase.
