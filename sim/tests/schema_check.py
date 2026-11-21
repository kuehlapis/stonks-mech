"""Minimal JSON Schema (draft-07 subset) validator for mechfight.schema.json, stdlib only.

Supports what the schema uses: $ref (local), type (incl. lists), const, enum, required, properties,
additionalProperties (schema or bool), items, minItems, maxItems, anyOf, oneOf, pattern, minimum, maximum.
"""
import json
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
with open(os.path.join(REPO, "mechfight.schema.json"), encoding="utf-8") as _f:
    SCHEMA = json.load(_f)

_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def _resolve(ref):
    node = SCHEMA
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node


def errors(value, schema, path="$"):
    """List of error strings (empty = valid)."""
    if "$ref" in schema:
        return errors(value, _resolve(schema["$ref"]), path)
    out = []
    t = schema.get("type")
    if t is not None:
        ts = t if isinstance(t, list) else [t]
        if not any(_TYPES[x](value) for x in ts):
            return [f"{path}: {value!r} is not {t}"]
    if "const" in schema and value != schema["const"]:
        out.append(f"{path}: {value!r} != const {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        out.append(f"{path}: {value!r} not in {schema['enum']}")
    if "pattern" in schema and isinstance(value, str) and not re.search(schema["pattern"], value):
        out.append(f"{path}: {value!r} does not match {schema['pattern']}")
    if "minimum" in schema and _TYPES["number"](value) and value < schema["minimum"]:
        out.append(f"{path}: {value} < {schema['minimum']}")
    if "maximum" in schema and _TYPES["number"](value) and value > schema["maximum"]:
        out.append(f"{path}: {value} > {schema['maximum']}")
    if isinstance(value, dict):
        for k in schema.get("required", []):
            if k not in value:
                out.append(f"{path}: missing {k}")
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for k, v in value.items():
            if k in props:
                out += errors(v, props[k], f"{path}.{k}")
            elif extra is False:
                out.append(f"{path}: unexpected {k}")
            elif isinstance(extra, dict):
                out += errors(v, extra, f"{path}.{k}")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            out.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            out.append(f"{path}: more than {schema['maxItems']} items")
        if isinstance(schema.get("items"), dict):
            for i, v in enumerate(value):
                out += errors(v, schema["items"], f"{path}[{i}]")
    for key in ("anyOf", "oneOf"):
        if key in schema:
            ok = [s for s in schema[key] if not errors(value, s, path)]
            if not ok or (key == "oneOf" and len(ok) > 1):
                out.append(f"{path}: {key} matched {len(ok)} branches for {json.dumps(value)[:200]}")
    return out


def obs_errors(obs):
    out = errors(obs, {"$ref": "#/definitions/Observation"})
    # the GameEvent anyOf accepts any object with the right keys; check each event against its own type too
    names = {"damaged": "DamagedEvent", "hit": "HitEvent", "effect": "EffectEvent", "drop": "DropEvent",
             "kill": "KillEvent", "pickup": "PickupEvent", "upgrade": "UpgradeEvent", "took": "TookEvent",
             "dropped": "DroppedEvent", "take_failed": "TakeFailedEvent"}
    for i, e in enumerate(obs.get("events", [])):
        n = names.get(e.get("type"))
        if n is None:
            out.append(f"$.events[{i}]: unknown type {e.get('type')!r}")
        else:
            out += errors(e, {"$ref": f"#/definitions/{n}"}, f"$.events[{i}]")
    # protocol §6: optional event flags are omitted, never false/null
    for i, e in enumerate(obs.get("events", [])):
        for k in ("rear", "effect"):
            if k in e and not e[k]:
                out.append(f"$.events[{i}].{k} present but falsy")
    return out
