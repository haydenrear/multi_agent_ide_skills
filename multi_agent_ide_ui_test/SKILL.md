---
name: multi_agent_ide_ui_test
description: UI testing skill for multi_agent_ide — test the shared UI abstraction by calling state and action endpoints directly, verifying UI behavior as it would render on TUI or other frontends.
---

Use this skill to test UI behavior in `multi_agent_ide` through the shared UI abstraction layer. The application has a common unifying abstraction for UI state — renderers (TUI, web, etc.) are swappable, but the underlying state model is shared. This means you can test how events render, how focus and navigation behave, and how chat/session state evolves by calling the API endpoints directly, without needing a live TUI or frontend.

This skill is rarely needed for standard controller workflows. Load it only when you need to:
- Verify how the UI state snapshot looks for a specific node (as it would appear on TUI or any renderer)
- Trigger UI-level actions (focus, scroll, search, session selection) and observe their effect on state
- Debug rendering or state management issues in the shared UI abstraction

For agent-level actions (start-goal, send-message, resolve-permission) and all other API operations, see `multi_agent_ide_api` skill. Use Swagger UI or `api_schema.py --level 3 --tag "Debug UI"` for full request/response shapes.

## UI architecture

The UI layer is built on a **shared state abstraction** (`UiStateSnapshot`) that captures the full UI state for a node scope: active panel focus, event stream position, chat input/search state, and session list. Concrete renderers (the Textual TUI, future web UI, etc.) consume and render this state — but the state itself is managed server-side and accessible via REST.

This means:
- You can inspect exactly what any renderer would show by calling `POST /api/ui/nodes/state`
- You can simulate user interactions (focus changes, scrolling, text input, session switching) by calling `POST /api/ui/nodes/actions`
- Test results are renderer-agnostic — if the state is correct, any renderer will display it correctly

## Endpoints

Use these endpoints directly via `curl`, `httpie`, or Swagger UI. Discover full request/response shapes with `api_schema.py --level 3 --tag "Debug UI"`.

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/ui/nodes/state` | Get current `UiStateSnapshot` for a node — active panel, chat state, event stream position, session list |
| POST | `/api/ui/nodes/actions` | Dispatch a UI action event — focus, scroll, search, input, session operations |

## Swagger tags

These endpoints are part of the **Debug UI** tag in Swagger. Other tags you may interact with when testing UI behavior:
- **Debug UI** — state snapshots, actions, event polling, workflow graph
- **Permissions** — if testing permission prompt rendering
- **Interrupts** — if testing interrupt/review rendering
