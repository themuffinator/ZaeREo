#!/usr/bin/env python3
"""Generate editor entity definitions from the canonical Zaero schema.

The generated files are intentionally checked in.  Run this tool after changing
``editor/entities.json`` and use ``--check`` in CI to detect stale output.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "editor" / "entities.json"
OUTPUTS = (
    ROOT / "editor" / "common" / "ZaeREo.fgd",
    ROOT / "editor" / "netradiant-custom" / "ZaeREo.fgd",
    ROOT / "editor" / "trenchbroom" / "ZaeREo.fgd",
)

CLASSNAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
PROPERTY_TYPES = {
    "angle",
    "choices",
    "color255",
    "float",
    "integer",
    "sound",
    "string",
    "studio",
    "target_destination",
    "target_source",
    "vector",
}


class SchemaError(ValueError):
    """Raised when editor/entities.json violates its stable contract."""


@dataclass(frozen=True)
class Entity:
    classname: str
    title: str
    description: str
    kind: str
    color: tuple[int, int, int]
    mins: tuple[int, int, int] | None
    maxs: tuple[int, int, int] | None
    model: str | None
    properties: tuple[dict[str, Any], ...]
    spawnflags: tuple[dict[str, Any], ...]


def _triple(value: Any, label: str) -> tuple[int, int, int]:
    if not isinstance(value, list) or len(value) != 3 or not all(isinstance(v, int) for v in value):
        raise SchemaError(f"{label} must be an array of three integers")
    return tuple(value)


def _safe_runtime_path(value: str, label: str) -> str:
    if "\\" in value:
        raise SchemaError(f"{label} must use forward slashes")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise SchemaError(f"{label} must be a relative runtime path")
    return value


def load_schema(path: Path) -> tuple[Entity, ...]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SchemaError(f"unable to read {path}: {exc}") from exc

    if raw.get("schema_version") != 1 or not isinstance(raw.get("entities"), list):
        raise SchemaError("schema_version must be 1 and entities must be an array")

    result: list[Entity] = []
    seen: set[str] = set()
    for index, item in enumerate(raw["entities"]):
        label = f"entities[{index}]"
        if not isinstance(item, dict):
            raise SchemaError(f"{label} must be an object")
        classname = item.get("classname")
        if not isinstance(classname, str) or not CLASSNAME_RE.fullmatch(classname):
            raise SchemaError(f"{label}.classname is invalid")
        if classname in seen:
            raise SchemaError(f"duplicate classname: {classname}")
        seen.add(classname)

        kind = item.get("kind", "point")
        if kind not in {"point", "solid"}:
            raise SchemaError(f"{classname}.kind must be point or solid")
        mins = _triple(item["mins"], f"{classname}.mins") if "mins" in item else None
        maxs = _triple(item["maxs"], f"{classname}.maxs") if "maxs" in item else None
        if kind == "point" and (mins is None or maxs is None):
            raise SchemaError(f"{classname} point entities require mins and maxs")
        if kind == "solid" and (mins is not None or maxs is not None):
            raise SchemaError(f"{classname} solid entities must not define bounds")

        model = item.get("model")
        if model is not None:
            if not isinstance(model, str):
                raise SchemaError(f"{classname}.model must be a string")
            model = _safe_runtime_path(model, f"{classname}.model")

        properties = item.get("properties", [])
        if not isinstance(properties, list):
            raise SchemaError(f"{classname}.properties must be an array")
        property_names: set[str] = set()
        for prop in properties:
            if not isinstance(prop, dict):
                raise SchemaError(f"{classname} property must be an object")
            name = prop.get("name")
            ptype = prop.get("type")
            if not isinstance(name, str) or not KEY_RE.fullmatch(name) or name in property_names:
                raise SchemaError(f"{classname} has an invalid or duplicate property")
            if ptype not in PROPERTY_TYPES:
                raise SchemaError(f"{classname}.{name} has unsupported type {ptype!r}")
            property_names.add(name)

        spawnflags = item.get("spawnflags", [])
        if not isinstance(spawnflags, list):
            raise SchemaError(f"{classname}.spawnflags must be an array")
        bits: set[int] = set()
        for flag in spawnflags:
            if not isinstance(flag, dict) or not isinstance(flag.get("bit"), int):
                raise SchemaError(f"{classname} spawnflag must have an integer bit")
            bit = flag["bit"]
            if bit <= 0 or bit & (bit - 1) or bit in bits:
                raise SchemaError(f"{classname} spawnflag bits must be unique powers of two")
            bits.add(bit)

        result.append(
            Entity(
                classname=classname,
                title=str(item.get("title", classname)),
                description=str(item.get("description", "")),
                kind=kind,
                color=_triple(item.get("color", [128, 128, 255]), f"{classname}.color"),
                mins=mins,
                maxs=maxs,
                model=model,
                properties=tuple(properties),
                spawnflags=tuple(spawnflags),
            )
        )

    if [entity.classname for entity in result] != sorted(seen):
        raise SchemaError("entities must be sorted by exact classname")
    return tuple(result)


def _quote(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\r", " ").replace("\n", " ")


def render_fgd(entities: tuple[Entity, ...]) -> str:
    lines = [
        "// Generated by tools/generate_editor_defs.py; do not edit by hand.",
        "// Canonical input: editor/entities.json",
        "// Zaero names, key spellings, and spawnflag values are map compatibility ABI.",
        "",
    ]
    for entity in entities:
        base = "@SolidClass" if entity.kind == "solid" else "@PointClass"
        clauses = [f"color({entity.color[0]} {entity.color[1]} {entity.color[2]})"]
        if entity.mins is not None and entity.maxs is not None:
            bounds = (*entity.mins, *entity.maxs)
            clauses.append("size(" + " ".join(str(v) for v in bounds) + ")")
        if entity.model:
            clauses.append(f'studio("{_quote(entity.model)}")')
        lines.append(
            f'{base} {" ".join(clauses)} = {entity.classname} : "{_quote(entity.title)}" : "{_quote(entity.description)}"'
        )
        lines.append("[")
        for prop in entity.properties:
            default = prop.get("default")
            suffix = "" if default is None else f' : "{_quote(default)}"'
            lines.append(
                f'    {prop["name"]}({prop["type"]}) : "{_quote(prop.get("description", prop["name"]))}"{suffix}'
            )
        if entity.spawnflags:
            lines.append('    spawnflags(flags) =')
            lines.append("    [")
            for flag in sorted(entity.spawnflags, key=lambda item: item["bit"]):
                enabled = 1 if flag.get("default", False) else 0
                lines.append(f'        {flag["bit"]} : "{_quote(flag.get("name", flag["bit"]))}" : {enabled}')
            lines.append("    ]")
        lines.append("]")
        lines.append("")
    return "\n".join(lines)


def update_outputs(content: str, outputs: tuple[Path, ...], check: bool) -> list[Path]:
    stale: list[Path] = []
    for output in outputs:
        current = output.read_text(encoding="utf-8") if output.exists() else None
        if current == content:
            continue
        stale.append(output)
        if not check:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(content, encoding="utf-8", newline="\n")
    return stale


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--check", action="store_true", help="fail if checked-in outputs are stale")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        content = render_fgd(load_schema(args.schema))
        stale = update_outputs(content, OUTPUTS, args.check)
    except SchemaError as exc:
        print(f"editor definition error: {exc}", file=sys.stderr)
        return 2
    if args.check and stale:
        for path in stale:
            print(f"stale generated editor definition: {path.relative_to(ROOT)}", file=sys.stderr)
        return 1
    action = "checked" if args.check else "generated"
    print(f"{action} {len(OUTPUTS)} editor definition files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
