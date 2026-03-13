# Prompt Architecture and Evolution Guide

Use this guide when debugging loops/stalls and deciding where to change prompt behavior.

## Prompt file locations

- Workflow templates:
  - `multi_agent_ide_java_parent/multi_agent_ide/src/main/resources/prompts/workflow`
- Base prompt resource root:
  - `multi_agent_ide_java_parent/multi_agent_ide/src/main/resources/prompts`
- Prompt contracts/context classes:
  - `multi_agent_ide_java_parent/multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/prompt`
- Prompt contributor factories and contributors:
  - `multi_agent_ide_java_parent/multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/prompt/contributor`
  - `multi_agent_ide_java_parent/multi_agent_ide/src/main/java/com/hayden/multiagentide/prompt/contributor`
- Prompt context decorators:
  - `multi_agent_ide_java_parent/multi_agent_ide/src/main/java/com/hayden/multiagentide/agent/decorator/prompt`

## Prompt assembly pipeline

1. Agent action selects a template name (for example `workflow/planning_orchestrator`) in `AgentInterfaces`.
2. `PromptContextFactory` builds `PromptContext` from the current `AgentModels.AgentRequest`:
   - sets `currentRequest`, `previousRequest`, `blackboardHistory`, upstream/previous contexts, model map.
3. `PromptContributorService` gathers contributors:
   - static contributors from `PromptContributorRegistry` (`PromptContributor` beans),
   - dynamic contributors from every `PromptContributorFactory` bean.
4. Contributors are sorted by `priority()` and adapted as prompt elements.
5. `AgentInterfaces.decoratePromptContext(...)` applies `PromptContextDecorator` chain in `order()`.
6. `DefaultLlmRunner.runWithTemplate(...)` executes template rendering + injected contributors.

## Workflow guidance already embedded in prompts

- The workflow-position contributor renders:
  - full graph spine (orchestrator -> discovery -> planning -> ticket -> orchestrator collector),
  - side-node routes (review, merger, context manager),
  - branch-level routing options for the current request type,
  - execution history and loop warning hints.
- Collector branch semantics are part of guidance:
  - `ADVANCE_PHASE`: move to next major phase,
  - `ROUTE_BACK`: repeat/refine current phase,
  - `STOP`: terminate/return at collector boundary.
- Interrupt and context-manager guidance is appended for all request types.

## How to add dynamic prompt guidance

Use this pattern when you need new context injected at runtime.

Reference example:
- `multi_agent_ide_java_parent/multi_agent_ide_lib/src/main/java/com/hayden/multiagentidelib/prompt/contributor/ArtifactKeyPromptContributorFactory.java`
- Pattern: factory class + inner `PromptContributor` record, returned from `create(PromptContext)`.

1. Add a `@Component` implementing `PromptContributorFactory`.
2. In `create(PromptContext context)`, return `List<PromptContributor>` when applicable.
3. Implement contributor as an inner `record` or class implementing `PromptContributor`.
4. Set `priority()` so it appears in the intended order.
5. Use `include(...)` or factory conditions to scope contribution by request type/metadata.

No manual wiring is required. Spring collects factories and contributors automatically.

### Minimal pattern

```java
@Component
public class ExamplePromptContributorFactory implements PromptContributorFactory {
    @Override
    public List<PromptContributor> create(PromptContext context) {
        if (context == null || context.currentRequest() == null) return List.of();
        return List.of(new ExampleContributor());
    }

    record ExampleContributor() implements PromptContributor {
        public String name() { return "example-guidance"; }
        public boolean include(PromptContext ctx) { return true; }
        public String contribute(PromptContext ctx) { return template(); }
        public String template() { return "Example guidance text"; }
        public int priority() { return 500; }
    }
}
```

## When to edit template vs contributor vs decorator

- Edit a `.jinja` template when base task instructions for one node need to change.
- Add/edit a `PromptContributor` when context should be injected dynamically by request/history/tool state.
- Add/edit a `PromptContextDecorator` when `PromptContext` itself must be transformed before LLM execution.

## Loop-debugging prompt strategy

1. Use `quick_action.py poll-events` and `quick_action.py event-detail` to identify where routing repeats.
2. Map current request type to expected branches via `references/we_are_here_prompt.md`.
3. If base instructions are weak, update the corresponding `workflow/*.jinja`.
4. If missing context caused the loop, add a targeted contributor factory.
5. Redeploy with `deploy_restart.py`, run again, compare route progression and interruptions.
