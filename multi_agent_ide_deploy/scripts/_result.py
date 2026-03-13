import json
from typing import Any


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def success(data: Any) -> int:
    emit({"ok": True, "data": data})
    return 0


def failure(error: Any, status: int | None = None) -> int:
    emit({"ok": False, "status": status, "error": error})
    return 1
