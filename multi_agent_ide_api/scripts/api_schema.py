#!/usr/bin/env python3
"""
api_schema.py — Progressive disclosure of the multi-agent-ide OpenAPI schema.

Levels:
  1  groups     — tag names only (default)
  2  endpoints  — tag + method + path + summary for each operation
  3  detail     — endpoints + request/response schema shapes
  4  full       — raw /v3/api-docs JSON dump

Usage:
  python api_schema.py [--level 1|2|3|4] [--tag TAGNAME] [--base-url URL]

Environment:
  MAI_DEBUG_BASE_URL — defaults to http://localhost:8080
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from _client import request_json


# ── helpers ──────────────────────────────────────────────────────────────────

def fetch_api_docs(base_url: str | None) -> dict[str, Any]:
    result = request_json("GET", "/v3/api-docs", base_url=base_url)
    if not result.get("ok"):
        print(json.dumps({"error": "Failed to fetch /v3/api-docs", "detail": result}, indent=2))
        sys.exit(1)
    return result["data"]


def schema_shape(schema: dict[str, Any] | None, depth: int = 0) -> Any:
    """Return a compact shape descriptor for a JSON Schema object."""
    if not schema or not isinstance(schema, dict):
        return None
    if "$ref" in schema:
        return schema["$ref"].split("/")[-1]
    stype = schema.get("type", "object")
    if stype == "object":
        props = schema.get("properties", {})
        if not props:
            return "{}"
        if depth > 1:
            return "{...}"
        return {k: schema_shape(v, depth + 1) for k, v in props.items()}
    if stype == "array":
        items = schema.get("items")
        return [schema_shape(items, depth + 1)]
    return stype


def resolve_ref(ref: str, components: dict[str, Any]) -> dict[str, Any]:
    parts = ref.lstrip("#/").split("/")
    node: Any = {"components": components}
    for p in parts[1:]:  # skip "components"
        node = node.get(p, {}) if isinstance(node, dict) else {}
    return node if isinstance(node, dict) else {}


def body_shape(op: dict[str, Any], components: dict[str, Any]) -> Any:
    rb = op.get("requestBody", {})
    content = rb.get("content", {})
    schema = (
        content.get("application/json", {}).get("schema")
        or content.get("*/*", {}).get("schema")
    )
    if not schema:
        return None
    if "$ref" in schema:
        schema = resolve_ref(schema["$ref"], components)
    return schema_shape(schema)


def response_shape(op: dict[str, Any], components: dict[str, Any]) -> Any:
    responses = op.get("responses", {})
    ok_resp = responses.get("200") or responses.get("201") or next(iter(responses.values()), {})
    content = ok_resp.get("content", {})
    schema = (
        content.get("application/json", {}).get("schema")
        or content.get("*/*", {}).get("schema")
        or content.get("text/event-stream", {}).get("schema")
    )
    if not schema:
        return None
    if "$ref" in schema:
        schema = resolve_ref(schema["$ref"], components)
    return schema_shape(schema)


# ── rendering ─────────────────────────────────────────────────────────────────

def render_groups(docs: dict[str, Any]) -> dict[str, Any]:
    tags = docs.get("tags", [])
    if not tags:
        # derive from operations
        tag_names: set[str] = set()
        for path_item in docs.get("paths", {}).values():
            for op in path_item.values():
                if isinstance(op, dict):
                    for t in op.get("tags", []):
                        tag_names.add(t)
        return {"groups": sorted(tag_names)}
    return {"groups": [t.get("name") for t in tags]}


def render_endpoints(docs: dict[str, Any], tag_filter: str | None) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for path, path_item in docs.get("paths", {}).items():
        for method, op in path_item.items():
            if not isinstance(op, dict):
                continue
            tags = op.get("tags", ["(untagged)"])
            for tag in tags:
                if tag_filter and tag.lower() != tag_filter.lower():
                    continue
                groups.setdefault(tag, []).append({
                    "method": method.upper(),
                    "path": path,
                    "summary": op.get("summary", ""),
                })
    return {"endpoints": groups}


def render_detail(docs: dict[str, Any], tag_filter: str | None) -> dict[str, Any]:
    components = docs.get("components", {})
    groups: dict[str, list[dict[str, Any]]] = {}
    for path, path_item in docs.get("paths", {}).items():
        for method, op in path_item.items():
            if not isinstance(op, dict):
                continue
            tags = op.get("tags", ["(untagged)"])
            for tag in tags:
                if tag_filter and tag.lower() != tag_filter.lower():
                    continue
                groups.setdefault(tag, []).append({
                    "method": method.upper(),
                    "path": path,
                    "summary": op.get("summary", ""),
                    "request": body_shape(op, components),
                    "response": response_shape(op, components),
                })
    return {"endpoints": groups}


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Progressive OpenAPI schema explorer")
    parser.add_argument("--level", type=int, default=1, choices=[1, 2, 3, 4],
                        help="Detail level: 1=groups, 2=endpoints, 3=detail, 4=full (default: 1)")
    parser.add_argument("--tag", default=None,
                        help="Filter output to a single tag/group name (levels 2-3)")
    parser.add_argument("--base-url", default=None,
                        help="Override base URL (default: MAI_DEBUG_BASE_URL or http://localhost:8080)")
    args = parser.parse_args()

    docs = fetch_api_docs(args.base_url)

    if args.level == 1:
        output = render_groups(docs)
    elif args.level == 2:
        output = render_endpoints(docs, args.tag)
    elif args.level == 3:
        output = render_detail(docs, args.tag)
    else:
        output = docs

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
