#!/usr/bin/env python3
"""Fail-closed static coverage audit for ZaeREo's JSON-save surface.

The Rerelease save system registers data members through the FIELD_* macros and
callbacks/mmoves through the save-data macros in g_local.h.  This audit does not
claim a runtime round trip; it prevents the current port-owned save surface from
quietly drifting out of those registration mechanisms.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

from audit_common import stable_json_text


ROOT = Path(__file__).resolve().parents[1]
STRUCTS = (
    "level_locals_t",
    "monsterinfo_t",
    "client_persistant_t",
    "gclient_t",
    "edict_t",
)
CALLBACK_MACROS = (
    "THINK",
    "TOUCH",
    "USE",
    "PAIN",
    "DIE",
    "MONSTERINFO_STAND",
    "MONSTERINFO_IDLE",
    "MONSTERINFO_SEARCH",
    "MONSTERINFO_WALK",
    "MONSTERINFO_RUN",
    "MONSTERINFO_DODGE",
    "MONSTERINFO_ATTACK",
    "MONSTERINFO_MELEE",
    "MONSTERINFO_SIGHT",
    "MONSTERINFO_CHECKATTACK",
    "MONSTERINFO_SETSKIN",
    "MONSTERINFO_BLOCKED",
    "MONSTERINFO_PHYSCHANGED",
    "MONSTERINFO_DUCK",
    "MONSTERINFO_UNDUCK",
    "MONSTERINFO_SIDESTEP",
    "MMOVE_T",
)
INTEGRATION_CALLBACK_SOURCES = (
    "g_func.cpp",
    "g_items.cpp",
    "g_misc.cpp",
    "g_monster.cpp",
    "g_target.cpp",
    "g_trigger.cpp",
    "m_hover.cpp",
)


class SaveSurfaceAuditError(RuntimeError):
    """The port's declared JSON-save surface is incomplete or ambiguous."""


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _struct_body(source: str, name: str) -> str:
    match = re.search(rf"\bstruct\s+{re.escape(name)}\s*\{{", source)
    if not match:
        raise SaveSurfaceAuditError(f"could not find struct {name}")
    opening = source.index("{", match.start())
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1 : index]
    raise SaveSurfaceAuditError(f"unterminated struct {name}")


def _zaero_fields(source: str, struct_name: str) -> list[str]:
    fields: set[str] = set()
    for raw_line in _struct_body(source, struct_name).splitlines():
        line = raw_line.split("//", 1)[0]
        # A declaration's identifier precedes either a semicolon or an inline
        # initializer. This deliberately ignores enum/type spellings and
        # comments, which are not serialized members.
        match = re.search(r"\b(zaero_[A-Za-z0-9_]+)\s*(?:;|=)", line)
        if match:
            fields.add(match.group(1))
    return sorted(fields)


def _field_is_registered(save_source: str, struct_name: str, field: str) -> bool:
    prefix = "monsterinfo\." if struct_name == "monsterinfo_t" else ""
    pattern = rf"FIELD_AUTO\s*\(\s*{prefix}{re.escape(field)}\s*\)"
    return re.search(pattern, save_source) is not None


def _callback_definitions(path: Path, *, zaero_only: bool) -> list[dict[str, str]]:
    source = _read(path)
    macro_pattern = "|".join(re.escape(macro) for macro in CALLBACK_MACROS)
    pattern = re.compile(rf"\b(?P<macro>{macro_pattern})\s*\(\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\)")
    definitions: list[dict[str, str]] = []
    for match in pattern.finditer(source):
        name = match.group("name")
        if zaero_only and "zaero" not in name.lower():
            continue
        definitions.append({"macro": match.group("macro"), "name": name})
    return definitions


def _callback_sources(source_root: Path) -> list[tuple[Path, bool]]:
    sources = [(path, False) for path in sorted((source_root / "zaero").glob("*.cpp"))]
    sources.extend((source_root / filename, True) for filename in INTEGRATION_CALLBACK_SOURCES)
    missing = [str(path) for path, _ in sources if not path.is_file()]
    if missing:
        raise SaveSurfaceAuditError("callback source missing: " + ", ".join(missing))
    return sources


def _callback_macro_contract(header: str) -> dict[str, bool]:
    contracts: dict[str, bool] = {}
    for macro in CALLBACK_MACROS:
        macro_match = re.search(rf"#define\s+{re.escape(macro)}\s*\(", header)
        if not macro_match:
            contracts[macro] = False
            continue
        end = header.find("\n\n", macro_match.start())
        definition = header[macro_match.start() : end if end >= 0 else len(header)]
        contracts[macro] = "save_data_list_t" in definition or "SAVE_DATA_FUNC" in definition
    return contracts


def build_save_surface_report(
    source_root: Path = ROOT / "src", *, local_source: str | None = None, save_source: str | None = None
) -> dict[str, Any]:
    source_root = source_root.resolve()
    local = _read(source_root / "g_local.h") if local_source is None else local_source
    save = _read(source_root / "g_save.cpp") if save_source is None else save_source

    field_rows: list[dict[str, Any]] = []
    for struct_name in STRUCTS:
        for field in _zaero_fields(local, struct_name):
            field_rows.append(
                {
                    "struct": struct_name,
                    "field": field,
                    "registration": "FIELD_AUTO",
                    "registered": _field_is_registered(save, struct_name, field),
                }
            )

    macro_contracts = _callback_macro_contract(local)
    callback_rows: list[dict[str, Any]] = []
    for path, zaero_only in _callback_sources(source_root):
        for definition in _callback_definitions(path, zaero_only=zaero_only):
            callback_rows.append(
                {
                    "source": path.relative_to(source_root).as_posix(),
                    **definition,
                    "registered_by_macro": macro_contracts[definition["macro"]],
                }
            )

    missing_fields = [row for row in field_rows if not row["registered"]]
    missing_callbacks = [row for row in callback_rows if not row["registered_by_macro"]]
    if not field_rows:
        raise SaveSurfaceAuditError("no Zaero-owned fields were discovered")
    if not callback_rows:
        raise SaveSurfaceAuditError("no Zaero-owned callbacks or mmoves were discovered")

    return {
        "schema": "zaereo.save-surface-audit/v1",
        "source_root": "src",
        "field_registrations": field_rows,
        "callback_registrations": callback_rows,
        "macro_contracts": macro_contracts,
        "missing_fields": missing_fields,
        "missing_callbacks": missing_callbacks,
        "summary": {
            "field_count": len(field_rows),
            "callback_count": len(callback_rows),
            "field_registration_count": len(field_rows) - len(missing_fields),
            "callback_registration_count": len(callback_rows) - len(missing_callbacks),
            "complete": not missing_fields and not missing_callbacks and all(macro_contracts.values()),
        },
    }


def require_complete(report: dict[str, Any]) -> None:
    if not report["summary"]["complete"]:
        raise SaveSurfaceAuditError(
            f"incomplete registration: fields={len(report['missing_fields'])} "
            f"callbacks={len(report['missing_callbacks'])}"
        )


def save_surface_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# ZaeREo JSON save-surface audit",
        "",
        "This file is generated by `tools/audit_save_surface.py`; do not edit it by hand.",
        "It is static registration evidence only; live save/load round trips remain required.",
        "",
        "## Summary",
        "",
        f"- Zaero-owned fields: `{summary['field_count']}`",
        f"- Registered fields: `{summary['field_registration_count']}`",
        f"- Zaero-owned callbacks/mmoves: `{summary['callback_count']}`",
        f"- Macro-registered callbacks/mmoves: `{summary['callback_registration_count']}`",
        f"- Complete: `{str(summary['complete']).lower()}`",
        "",
        "## Fields",
        "",
        "| Owner structure | Field | JSON registration |",
        "| --- | --- | --- |",
    ]
    for row in report["field_registrations"]:
        lines.append(f"| `{row['struct']}` | `{row['field']}` | `{row['registration']}` |")

    lines.extend(["", "## Callback/mmove registration", "", "| Source | Macro | Name |", "| --- | --- | --- |"])
    for row in report["callback_registrations"]:
        lines.append(f"| `{row['source']}` | `{row['macro']}` | `{row['name']}` |")
    lines.append("")
    return "\n".join(lines)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=ROOT / "src")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--check", action="store_true", help="Check outputs instead of writing them.")
    args = parser.parse_args()

    try:
        report = build_save_surface_report(args.source_root)
        require_complete(report)
        outputs = ((args.json_output, stable_json_text(report)), (args.markdown_output, save_surface_markdown(report)))
        for path, text in outputs:
            if path is None:
                continue
            if args.check:
                if not path.is_file() or path.read_text(encoding="utf-8") != text:
                    raise SaveSurfaceAuditError(f"generated output is stale: {path}")
            else:
                _write(path, text)
    except (OSError, SaveSurfaceAuditError) as error:
        print(f"audit_save_surface.py: {error}", file=sys.stderr)
        return 2

    print(
        "save surface complete: "
        f"fields={report['summary']['field_count']} callbacks={report['summary']['callback_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
