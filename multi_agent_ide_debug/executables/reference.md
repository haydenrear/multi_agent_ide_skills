# Debug Executables Reference

Scripts in this directory are written and maintained during debug sessions. Before writing a new script, check this index — if a matching script exists, use it (and improve it if needed).

| Script | Description |
|--------|-------------|
| `error_search.py` | **Primary error search tool.** Uses `error_patterns.csv` to search for known error types. Default (no args): prints aggregate summary — count, time window, description for each active pattern. `--type <name\|index>`: prints last N matches for a specific pattern. `--raw <pattern>`: ad-hoc grep. `--acp`: search ACP error log. `--limit N`: control detail output (default 5). |
| `error_patterns.csv` | Known error patterns with grep expressions and descriptions. Add new rows when you discover a recurring error. Referenced by `error_search.py` and documented in `outstanding.md`. |
| `search_interrupt.py` | Trace the full interrupt lifecycle in logs. Phases: `--phase publish` (publishInterrupt/await), `--phase resolve` (resolveInterrupt/resolution), `--phase feedback` (Handling/Resolved feedback), `--phase review` (AI review agent), `--phase template` (review_resolution template), `--phase error` (errors near interrupt). Use `--node <id>` to filter to a run. Use `--context N` for surrounding lines. |
