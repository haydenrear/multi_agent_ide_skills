import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def resolve_base_url(base_url: str | None) -> str:
    value = base_url or os.environ.get("MAI_DEBUG_BASE_URL") or "http://localhost:8080"
    return value.rstrip("/")


def build_url(
    base_url: str | None, path: str, query: dict[str, Any] | None = None
) -> str:
    base = resolve_base_url(base_url)
    full = f"{base}{path}"
    if query:
        encoded = urllib.parse.urlencode(
            {k: v for k, v in query.items() if v is not None}
        )
        if encoded:
            full = f"{full}?{encoded}"
    return full


def request_json(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
    base_url: str | None = None,
    timeout: int = 30,
    dry_run: bool = False,
) -> dict[str, Any]:
    url = build_url(base_url, path, query)
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "request": {
                "method": method,
                "url": url,
                "payload": payload,
            },
        }

    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url=url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            if raw:
                try:
                    body = json.loads(raw)
                except json.JSONDecodeError:
                    body = raw
            else:
                body = None
            return {
                "ok": True,
                "status": response.status,
                "data": body,
            }
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8") if error.fp else ""
        try:
            body = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            body = raw
        return {
            "ok": False,
            "status": error.code,
            "error": body or str(error),
        }
    except urllib.error.URLError as error:
        return {
            "ok": False,
            "status": None,
            "error": str(error.reason),
        }
