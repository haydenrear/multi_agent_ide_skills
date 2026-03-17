# Debug Executables Reference

Scripts in this directory are written and maintained during debug sessions. Before writing a new script, check this index — if a matching script exists, use it (and improve it if needed).

| Script | Description |
|--------|-------------|
| `search_log.py [query]` | Search runtime or build logs with named presets. Presets: `errors` (default), `node <nodeId>`, `goal`, `permission`, `propagation`, `overflow`, `acp`. Pass any string for a raw grep. Use `--follow` to tail live. Use `--build` for the Gradle log. |
