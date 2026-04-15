#!/usr/bin/env python3
"""
api_schema.py — Progressive disclosure of the multi-agent-ide OpenAPI schema.

Path hierarchy
--------------
Controller endpoints are organised under a common path prefix hierarchy:

  /api/ui/*            — workflow graph, node events, quick-actions, event detail
  /api/agents/*        — pause, stop, resume, prune, branch, delete, review
  /api/permissions/*   — list pending, resolve, detail
  /api/interrupts/*    — request, resolve, status, detail
  /api/orchestrator/*  — start goal, onboarding runs
  /api/propagations/*  — propagation items + records
  /api/transformations/*— transformation records
  /api/filters/*       — filter policy CRUD
  /api/propagators/*   — propagator registration
  /api/transformers/*  — transformer registration
  /api/llm-debug/*     — extended debug UI (nodes, events, actions)

Use --path to focus on any prefix in this hierarchy, e.g.:
  --path /api/ui          → everything under /api/ui/
  --path /api/permissions → just the permissions group

Levels
------
  1  groups     — tag names + path prefixes seen under each tag (default)
  2  endpoints  — tag + method + path + summary for each operation
  3  detail     — endpoints + request/response schema shapes
  4  full       — raw /v3/api-docs JSON dump

Usage:
  python api_schema.py [--level 1|2|3|4] [--tag TAGNAME] [--path /api/ui]
                       [--base-url URL]

  --path and --tag can both be provided; both filters apply (AND).

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

def path_matches(path: str, path_filter: str | None) -> bool:
    """Return True if path starts with path_filter (normalised, case-insensitive)."""
    if not path_filter:
        return True
    prefix = path_filter.rstrip("/")
    p = path.rstrip("/")
    return p == prefix or p.startswith(prefix + "/")


def render_groups(docs: dict[str, Any], path_filter: str | None = None) -> dict[str, Any]:
    """Level 1: tag names with the distinct path prefixes observed under each tag."""
    tag_paths: dict[str, set[str]] = {}
    for path, path_item in docs.get("paths", {}).items():
        if not path_matches(path, path_filter):
            continue
        for op in path_item.values():
            if not isinstance(op, dict):
                continue
            for tag in op.get("tags", ["(untagged)"]):
                tag_paths.setdefault(tag, set()).add(path)

    # fall back to declared tags if no paths matched (e.g. no path_filter applied)
    declared = {t.get("name"): t.get("description", "") for t in docs.get("tags", [])}

    groups = []
    for tag in sorted(tag_paths):
        paths = sorted(tag_paths[tag])
        # derive common prefix for display
        entry: dict[str, Any] = {"tag": tag}
        if tag in declared and declared[tag]:
            entry["description"] = declared[tag]
        entry["paths"] = paths
        groups.append(entry)
    return {"groups": groups}


def render_endpoints(docs: dict[str, Any], tag_filter: str | None,
                     path_filter: str | None) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for path, path_item in docs.get("paths", {}).items():
        if not path_matches(path, path_filter):
            continue
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


def render_detail(docs: dict[str, Any], tag_filter: str | None,
                  path_filter: str | None) -> dict[str, Any]:
    components = docs.get("components", {})
    groups: dict[str, list[dict[str, Any]]] = {}
    for path, path_item in docs.get("paths", {}).items():
        if not path_matches(path, path_filter):
            continue
        for method, op in path_item.items():
            if not isinstance(op, dict):
                continue
            tags = op.get("tags", ["(untagged)"])
            for tag in tags:
                if tag_filter and tag.lower() != tag_filter.lower():
                    continue
                entry: dict[str, Any] = {
                    "method": method.upper(),
                    "path": path,
                    "summary": op.get("summary", ""),
                }
                desc = op.get("description", "")
                if desc:
                    entry["description"] = desc
                params = op.get("parameters", [])
                if params:
                    entry["parameters"] = [
                        {
                            "name": p.get("name"),
                            "in": p.get("in"),
                            "required": p.get("required", False),
                            "description": p.get("description", ""),
                            "schema": schema_shape(p.get("schema")),
                        }
                        for p in params if isinstance(p, dict)
                    ]
                req = body_shape(op, components)
                if req is not None:
                    entry["request"] = req
                resp = response_shape(op, components)
                if resp is not None:
                    entry["response"] = resp
                groups.setdefault(tag, []).append(entry)
    return {"endpoints": groups}


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Progressive OpenAPI schema explorer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Path hierarchy examples:
  --path /api/ui              all UI endpoints (workflow-graph, events, quick-actions)
  --path /api/permissions     permission listing and resolution
  --path /api/interrupts      interrupt request, resolve, detail
  --path /api/agents          pause/stop/resume/prune/branch/delete/review
  --path /api/propagations    propagation items and records
  --path /api/transformations transformation records
  --path /api/filters         filter policy CRUD
  --path /api/orchestrator    goal start and onboarding runs

Combine with --level for focused discovery:
  --level 3 --path /api/ui            full shapes for all /api/ui/* endpoints
  --level 2 --tag "Permissions"       endpoint list for the Permissions tag
  --level 3 --path /api/ui --tag "Debug UI"  intersection of path + tag
""",
    )
    parser.add_argument("--level", type=int, default=1, choices=[1, 2, 3, 4],
                        help="Detail level: 1=groups, 2=endpoints, 3=detail, 4=full (default: 1)")
    parser.add_argument("--tag", default=None,
                        help="Filter output to a single tag/group name (case-insensitive, levels 2-3)")
    parser.add_argument("--path", default=None,
                        help="Filter to endpoints at or below this path prefix, e.g. /api/ui")
    parser.add_argument("--base-url", default=None,
                        help="Override base URL (default: MAI_DEBUG_BASE_URL or http://localhost:8080)")
    args = parser.parse_args()

    docs = fetch_api_docs(args.base_url)

    if args.level == 1:
        output = render_groups(docs, args.path)
    elif args.level == 2:
        output = render_endpoints(docs, args.tag, args.path)
    elif args.level == 3:
        output = render_detail(docs, args.tag, args.path)
    else:
        output = render_full(docs, args.tag, args.path)

    print(json.dumps(output, indent=2))


def collect_refs(schema: Any, refs: set[str]) -> None:
    """Recursively collect all $ref targets from a schema."""
    if not isinstance(schema, dict):
        return
    if "$ref" in schema:
        refs.add(schema["$ref"].split("/")[-1])
    for v in schema.values():
        if isinstance(v, dict):
            collect_refs(v, refs)
        elif isinstance(v, list):
            for item in v:
                collect_refs(item, refs)


def render_full(docs: dict[str, Any], tag_filter: str | None,
                path_filter: str | None) -> dict[str, Any]:
    """Level 4: filtered paths + only the referenced component schemas."""
    if not tag_filter and not path_filter:
        return docs

    filtered_paths: dict[str, Any] = {}
    for path, path_item in docs.get("paths", {}).items():
        if not path_matches(path, path_filter):
            continue
        if tag_filter:
            filtered_ops = {}
            for method, op in path_item.items():
                if not isinstance(op, dict):
                    filtered_ops[method] = op
                    continue
                tags = op.get("tags", ["(untagged)"])
                if any(t.lower() == tag_filter.lower() for t in tags):
                    filtered_ops[method] = op
            if filtered_ops:
                filtered_paths[path] = filtered_ops
        else:
            filtered_paths[path] = path_item

    # collect all referenced schemas transitively
    refs: set[str] = set()
    collect_refs(filtered_paths, refs)
    all_schemas = docs.get("components", {}).get("schemas", {})
    # resolve transitively
    seen: set[str] = set()
    queue = list(refs)
    while queue:
        name = queue.pop()
        if name in seen:
            continue
        seen.add(name)
        if name in all_schemas:
            child_refs: set[str] = set()
            collect_refs(all_schemas[name], child_refs)
            queue.extend(child_refs - seen)

    filtered_schemas = {k: v for k, v in all_schemas.items() if k in seen}

    result: dict[str, Any] = {
        "openapi": docs.get("openapi"),
        "paths": filtered_paths,
    }
    if filtered_schemas:
        result["components"] = {"schemas": filtered_schemas}
    return result


if __name__ == "__main__":
    main()
