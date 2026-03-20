# Debug Executables Reference

Scripts in this directory are written and maintained during debug sessions. Before writing a new script, check this index — if a matching script exists, use it (and improve it if needed).

| Script | Description |
|--------|-------------|
| `search_log.py [query]` | Search runtime or build logs with named presets. Presets: `errors` (default), `node <nodeId>`, `goal`, `permission`, `propagation`, `overflow`, `acp`, `interrupt`. Pass any string for a raw grep. Use `--follow` to tail live. Use `--build` for the Gradle log. |
| `search_interrupt.py` | Trace the full interrupt lifecycle in logs. Phases: `--phase publish` (publishInterrupt/await), `--phase resolve` (resolveInterrupt/resolution), `--phase feedback` (Handling/Resolved feedback), `--phase review` (AI review agent), `--phase template` (review_resolution template), `--phase error` (errors near interrupt). Use `--node <id>` to filter to a run. Use `--context N` for surrounding lines. |
