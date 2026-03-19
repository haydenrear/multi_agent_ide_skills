#!/usr/bin/env python3
"""
register_propagator.py — Register or list propagator registrations.

List existing propagators on a layer, or register new AI_TEXT propagators
for missing action layers.

Usage:
    python register_propagator.py --list <layerId>
    python register_propagator.py --list-all
    python register_propagator.py --register <layerId> --stage ACTION_REQUEST
    python register_propagator.py --register <layerId> --stage ACTION_RESPONSE
    python register_propagator.py --check-missing    # find layers with 0 propagators

NOTE: Manual registration via the API currently fails with "Name is null"
(see outstanding.md #29). This script is ready for when that bug is fixed.
"""
import argparse
import json
import sys
import urllib.request
import urllib.error


def get(host, path):
    try:
        with urllib.request.urlopen(f"{host}{path}") as r:
            return json.load(r)
    except urllib.error.URLError as e:
        print(f"ERROR: {path} — {e}", file=sys.stderr)
        return None


def post(host, path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{host}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.URLError as e:
        body_text = ""
        if hasattr(e, "read"):
            body_text = e.read().decode()
        print(f"ERROR: {path} — {e} {body_text}", file=sys.stderr)
        return None


def list_layer(host, layer_id):
    result = post(host, "/api/propagators/registrations/by-layer", {"layerId": layer_id})
    if not result:
        return
    print(f"Layer: {result.get('layerId', '?')}  totalCount={result.get('totalCount', 0)}")
    for p in result.get("propagators", []):
        print(f"  [{p.get('status','?')}] {p.get('name','?')}  kind={p.get('propagatorKind','?')}  priority={p.get('priority','?')}")
        print(f"    id={p.get('registrationId','?')}")


def list_all_attachables(host):
    result = get(host, "/api/propagators/attachables")
    if not result:
        return
    actions = result.get("actions", [])
    print(f"Total attachable layers: {len(actions)}\n")
    for a in actions:
        layer = a.get("layerId", "?")
        stages = a.get("stages", [])
        # Check registration count
        reg = post(host, "/api/propagators/registrations/by-layer", {"layerId": layer})
        count = reg.get("totalCount", 0) if reg else "?"
        marker = " *** MISSING ***" if count == 0 else ""
        print(f"  {layer}  stages={stages}  propagators={count}{marker}")


def check_missing(host):
    result = get(host, "/api/propagators/attachables")
    if not result:
        return
    actions = result.get("actions", [])
    missing = []
    for a in actions:
        layer = a.get("layerId", "?")
        reg = post(host, "/api/propagators/registrations/by-layer", {"layerId": layer})
        count = reg.get("totalCount", 0) if reg else 0
        if count == 0:
            missing.append({"layerId": layer, "stages": a.get("stages", [])})

    if missing:
        print(f"Found {len(missing)} layer(s) with NO propagators:\n")
        for m in missing:
            print(f"  {m['layerId']}  stages={m['stages']}")
            for stage in m["stages"]:
                print(f"    → python register_propagator.py --register \"{m['layerId']}\" --stage {stage}")
    else:
        print("All attachable layers have at least one propagator.")


def register(host, layer_id, stage, name=None, kind="AI_TEXT", priority=100):
    if not name:
        safe_layer = layer_id.replace("/", "-")
        name = f"ai-prop-{safe_layer}-{stage.lower().replace('_', '-')}"

    body = {
        "name": name,
        "description": f"AI propagator for {layer_id} [{stage}]",
        "sourcePath": layer_id,
        "propagatorKind": kind,
        "priority": priority,
        "activate": True,
        "isInheritable": False,
        "isPropagatedToParent": False,
        "layerBindings": [{
            "layerId": layer_id,
            "matchOn": stage,
            "enabled": True,
            "includeDescendants": False,
            "isInheritable": False,
            "isPropagatedToParent": False
        }]
    }

    result = post(host, "/api/propagators/registrations", body)
    if result:
        ok = result.get("ok", False)
        rid = result.get("registrationId")
        msg = result.get("message", "")
        if ok:
            print(f"OK: {name} → registrationId={rid}")
        else:
            print(f"FAILED: {name} — {msg}")
            print(f"  (See outstanding.md #29 — manual registration may be broken)")
    else:
        print(f"FAILED: {name} — no response")


def main():
    parser = argparse.ArgumentParser(description="Propagator registration manager")
    parser.add_argument("--list", metavar="LAYER_ID", help="List propagators for a specific layer")
    parser.add_argument("--list-all", action="store_true", help="List all attachable layers with propagator counts")
    parser.add_argument("--check-missing", action="store_true", help="Find layers with 0 propagators")
    parser.add_argument("--register", metavar="LAYER_ID", help="Register a new AI_TEXT propagator for a layer")
    parser.add_argument("--stage", default="ACTION_REQUEST", help="Stage to bind to (default: ACTION_REQUEST)")
    parser.add_argument("--name", help="Custom propagator name (auto-generated if omitted)")
    parser.add_argument("--host", default="http://localhost:8080")
    args = parser.parse_args()

    if args.list:
        list_layer(args.host, args.list)
    elif args.list_all:
        list_all_attachables(args.host)
    elif args.check_missing:
        check_missing(args.host)
    elif args.register:
        register(args.host, args.register, args.stage, args.name)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
