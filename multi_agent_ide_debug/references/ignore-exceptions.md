# Ignored Exceptions

Exceptions listed here are known, benign, and should **not** consume investigation time. Before triaging any exception, check this file first — if it matches an entry here, skip it.

When you encounter a new exception that is confirmed safe to ignore, add it here with a short rationale.

| Exception / Pattern | Why it's ignored |
|---------------------|-----------------|
| `multi_agent_ide_python_parent` submodule clone failure | Submodule does not exist on GitHub — expected in all environments |
<!-- Add entries as exceptions are confirmed ignorable -->
