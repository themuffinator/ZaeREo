#!/usr/bin/env python3
"""Audit Zaero's zdmflags bits and eight-item deathmatch injection contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_common import (  # noqa: E402
    AuditError,
    checked_file,
    checked_root,
    sha256_file,
    stable_json_text,
    write_text,
)


ITEMS = (
    "weapon_soniccannon",
    "weapon_sniperrifle",
    "weapon_flaregun",
    "ammo_ired",
    "ammo_a2k",
    "ammo_flares",
    "ammo_empnuke",
    "ammo_plasmashield",
)

CANONICAL_MAPS = {
    "zbase1", "zbase2", "zdef1", "zdef2", "zdef3", "zdef4",
    "zwaste1", "zwaste2", "zwaste3", "ztomb1", "ztomb2", "ztomb3",
    "ztomb4", "zboss", "zdm1", "zdm2", "zdm3", "zdm4", "zdm5", "zdm6",
}


def _read(path: Path, encoding: str) -> str:
    return path.read_text(encoding=encoding)


def _identity(path: Path, root: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256_file(path),
        "size": path.stat().st_size,
    }


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _array_items(text: str, symbol: str) -> list[str]:
    match = re.search(
        rf"\b{re.escape(symbol)}\s*\[\s*\]\s*=\s*\{{(?P<body>.*?)\}}\s*;",
        text,
        re.DOTALL,
    )
    if not match:
        raise AuditError(f"could not find {symbol} array")
    return re.findall(r'"([^"\r\n]+)"', match.group("body"))


def _require_fragments(text: str, fragments: tuple[str, ...], label: str) -> None:
    compact = _compact(text)
    for fragment in fragments:
        if _compact(fragment) not in compact:
            raise AuditError(f"{label} no longer contains {fragment!r}")


def _load_bsp_maps(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise AuditError(f"invalid BSP audit JSON: {error}") from error
    maps = document.get("maps")
    if not isinstance(maps, list):
        raise AuditError("BSP audit maps must be a list")

    records: list[dict[str, Any]] = []
    for entry in maps:
        if not isinstance(entry, dict):
            raise AuditError("BSP audit map entry must be an object")
        name = entry.get("map_name")
        counts = entry.get("classname_counts")
        starts = entry.get("deathmatch_start_count")
        if not isinstance(name, str) or not isinstance(counts, dict):
            raise AuditError("BSP audit map name/classname counts are malformed")
        if not isinstance(starts, int) or starts < 0:
            raise AuditError(f"invalid deathmatch start count for {name}")
        item_counts = {item: int(counts.get(item, 0)) for item in ITEMS}
        if any(value < 0 for value in item_counts.values()):
            raise AuditError(f"negative item count for {name}")
        present = [item for item, count in item_counts.items() if count]
        records.append(
            {
                "deathmatch_start_count": starts,
                "injection_suppressed_by_existing_member": bool(present),
                "item_counts": item_counts,
                "map_kind": entry.get("map_kind"),
                "map_name": name,
                "missing_items": [item for item in ITEMS if item not in present],
                "present_item_classname_count": len(present),
                "present_item_entity_count": sum(item_counts.values()),
            }
        )
    records.sort(key=lambda item: item["map_name"].encode("utf-8"))
    return document, records


def build_report(zaero_root: Path, port_root: Path, bsp_audit_path: Path) -> dict[str, Any]:
    zaero_root = checked_root(zaero_root, "Zaero source root")
    port_root = checked_root(port_root, "ZaeREo source root")
    bsp_audit_path = checked_file(bsp_audit_path, "BSP entity audit")

    zaero_spawn = checked_file(zaero_root / "z_spawn.c", "Zaero z_spawn.c")
    zaero_local = checked_file(zaero_root / "g_local.h", "Zaero g_local.h")
    zaero_save = checked_file(zaero_root / "g_save.c", "Zaero g_save.c")
    port_dm = checked_file(port_root / "zaero" / "g_zaero_dm.cpp", "port DM source")
    port_dm_header = checked_file(
        port_root / "zaero" / "g_zaero_dm.h", "port DM header"
    )
    port_spawn = checked_file(port_root / "g_spawn.cpp", "port g_spawn.cpp")
    port_main = checked_file(port_root / "g_main.cpp", "port g_main.cpp")
    port_items = checked_file(port_root / "g_items.cpp", "port g_items.cpp")
    port_weapons = checked_file(
        port_root / "zaero" / "g_zaero_weapons.cpp", "port Zaero weapons"
    )
    port_project = checked_file(port_root / "game.vcxproj", "port project")

    zaero_spawn_text = _read(zaero_spawn, "latin-1")
    zaero_local_text = _read(zaero_local, "latin-1")
    zaero_save_text = _read(zaero_save, "latin-1")
    port_dm_text = _read(port_dm, "utf-8")
    port_header_text = _read(port_dm_header, "utf-8")
    port_spawn_text = _read(port_spawn, "utf-8")
    port_main_text = _read(port_main, "utf-8")
    port_items_text = _read(port_items, "utf-8")
    port_weapons_text = _read(port_weapons, "utf-8")
    port_project_text = _read(port_project, "utf-8")

    legacy_items = _array_items(zaero_spawn_text, "items")
    port_items_order = _array_items(port_dm_text, "ZAERO_DEATHMATCH_ITEMS")
    if legacy_items != list(ITEMS):
        raise AuditError(f"legacy item order changed: {legacy_items}")
    if port_items_order != legacy_items:
        raise AuditError(f"port item order differs from legacy: {port_items_order}")

    _require_fragments(
        zaero_local_text,
        (
            "#define ZDM_NO_GL_POLYBLEND_DAMAGE 1",
            "#define ZDM_ZAERO_ITEMS 2",
        ),
        "Zaero zdmflags definitions",
    )
    _require_fragments(
        zaero_save_text,
        ('zdmflags = gi.cvar ("zdmflags", "0", CVAR_SERVERINFO);',),
        "Zaero cvar registration",
    )
    _require_fragments(
        zaero_spawn_text,
        (
            "if (!deathmatch->value) return;",
            "if ((int)zdmflags->value & ZDM_ZAERO_ITEMS) return;",
            "if (e != NULL) return;",
            "for (j = 0; j < 4; j++)",
            "start[2] += 16;",
            "ang += 15",
            "VectorMA(start, 128, forward, end);",
            "MASK_SHOT",
            "ent->movetype = MOVETYPE_BOUNCE;",
            'gi.dprintf ("%i Zaero entities added\\n", added);',
        ),
        "Zaero injection source",
    )

    _require_fragments(
        port_header_text,
        (
            "ZAERO_DMFLAG_DISABLE_FLARE_POLYBLEND_DAMAGE = 1 << 0",
            "ZAERO_DMFLAG_DISABLE_ITEM_INJECTION = 1 << 1",
        ),
        "port zdmflags definitions",
    )
    _require_fragments(
        port_main_text,
        ('zdmflags = gi.cvar("zdmflags", "0", CVAR_SERVERINFO);',),
        "port cvar registration",
    )
    _require_fragments(
        port_dm_text,
        (
            "if (!deathmatch->integer) return;",
            "if (zdmflags->integer & ZAERO_DMFLAG_DISABLE_ITEM_INJECTION) return;",
            "ZAERO_ITEM_PLACEMENT_ATTEMPTS = 4",
            "ZAERO_ITEM_ANGLE_STEP = 15",
            "ZAERO_ITEM_PLACEMENT_RADIUS = 128.0f",
            "ZAERO_ITEM_PLACEMENT_HEIGHT = 16.0f",
            "ent->movetype = MOVETYPE_BOUNCE;",
            "ED_CallSpawn(ent);",
            "if (!ent->inuse) return false;",
            "gi.trace(start, ent->mins, ent->maxs, end, nullptr, MASK_SHOT)",
            "G_FreeEdict(ent);",
            'gi.Com_PrintFmt("{} Zaero entities added\\n", added);',
        ),
        "port injection source",
    )
    if "level.is_zaero" in port_dm_text:
        raise AuditError("DM injection is incorrectly gated by mapper classification")
    if "ZDM_ZAERO_ITEMS" in port_header_text + port_dm_text + port_weapons_text:
        raise AuditError("port retains the misleading legacy bit-2 symbol")
    if "ZDM_NO_GL_POLYBLEND_DAMAGE" in port_header_text + port_dm_text + port_weapons_text:
        raise AuditError("port retains the unclear legacy bit-1 symbol")
    if "ZAERO_DMFLAG_DISABLE_FLARE_POLYBLEND_DAMAGE" not in port_weapons_text:
        raise AuditError("flare compensation is not using the shared bit-1 name")

    team_index = port_spawn_text.index("G_FindTeams();")
    injection_index = port_spawn_text.index("Zaero_SpawnDeathmatchItems();")
    ctf_index = port_spawn_text.index("CTFSpawn();")
    if not team_index < injection_index < ctf_index:
        raise AuditError("port injection hook is not after teams and before CTF setup")
    for project_entry in (
        'ClInclude Include="zaero\\g_zaero_dm.h"',
        'ClCompile Include="zaero\\g_zaero_dm.cpp"',
    ):
        if project_entry not in port_project_text:
            raise AuditError(f"project is missing {project_entry}")
    for native_fragment in (
        "THINK(droptofloor)",
        "TOUCH(Touch_Item)",
        "ent->think = droptofloor;",
    ):
        if native_fragment not in port_items_text:
            raise AuditError(f"native item lifecycle is missing {native_fragment}")

    _, map_records = _load_bsp_maps(bsp_audit_path)
    map_names = {entry["map_name"] for entry in map_records}
    if map_names != CANONICAL_MAPS:
        raise AuditError(
            f"supplied map set changed: missing={sorted(CANONICAL_MAPS - map_names)}, "
            f"extra={sorted(map_names - CANONICAL_MAPS)}"
        )
    total_starts = sum(entry["deathmatch_start_count"] for entry in map_records)
    if total_starts != 230:
        raise AuditError(f"supplied deathmatch start total changed: {total_starts}")
    if any(not entry["injection_suppressed_by_existing_member"] for entry in map_records):
        raise AuditError("a supplied map contains none of the eight injection items")
    dedicated = [entry for entry in map_records if entry["map_kind"] == "deathmatch"]
    if {entry["map_name"] for entry in dedicated} != {
        "zdm1", "zdm2", "zdm3", "zdm4", "zdm5", "zdm6"
    }:
        raise AuditError("dedicated Zaero deathmatch map set changed")

    return {
        "audit": "zaero-deathmatch-item-injection",
        "schema_version": 1,
        "disposition": {
            "classification": "PARITY",
            "decision": "D-045",
            "mapper_classification_required": False,
            "numeric_cvar_compatibility": True,
            "source_all_or_none_is_precondition_not_transaction": True,
        },
        "inputs": {
            "bsp_audit": _identity(bsp_audit_path, port_root.parent),
            "port": [
                _identity(path, port_root)
                for path in (
                    port_dm, port_dm_header, port_spawn, port_main,
                    port_items, port_weapons, port_project,
                )
            ],
            "zaero": [
                _identity(path, zaero_root)
                for path in (zaero_spawn, zaero_local, zaero_save)
            ],
        },
        "legacy_contract": {
            "angle_step_degrees": 15,
            "attempts_per_item": 4,
            "console_count": True,
            "item_order": legacy_items,
            "placement_height": 16,
            "placement_radius": 128,
            "placement_trace_mask": "MASK_SHOT",
            "pre_drop_movetype": "MOVETYPE_BOUNCE",
            "start_ordinal_begins_at": 1,
            "start_walk_wraps": True,
        },
        "maps": map_records,
        "port_contract": {
            "bit_1_name": "ZAERO_DMFLAG_DISABLE_FLARE_POLYBLEND_DAMAGE",
            "bit_2_name": "ZAERO_DMFLAG_DISABLE_ITEM_INJECTION",
            "cvar": "zdmflags",
            "cvar_default": 0,
            "cvar_flags": "CVAR_SERVERINFO",
            "injection_hook": "G_FindTeams < Zaero_SpawnDeathmatchItems < CTFSpawn",
            "item_order": port_items_order,
            "native_item_lifecycle": "ED_CallSpawn -> SpawnItem -> droptofloor/Touch_Item",
            "rerelease_rejection_guard": "ent->inuse",
        },
        "summary": {
            "dedicated_deathmatch_map_count": len(dedicated),
            "injection_item_count": len(ITEMS),
            "maps_missing_at_least_one_set_member": sum(
                bool(entry["missing_items"]) for entry in map_records
            ),
            "supplied_deathmatch_start_count": total_starts,
            "supplied_map_count": len(map_records),
            "supplied_maps_eligible_for_injection": sum(
                not entry["injection_suppressed_by_existing_member"]
                for entry in map_records
            ),
        },
        "scope_note": (
            "Static/source and BSP-inventory evidence proves the compatibility surface "
            "and implementation shape. Private runtime evidence is maintained separately "
            "and now closes open stock placement, disabled/authored controls, and one "
            "deterministic real-brush partial-placement path. Eight private live controls "
            "also close every possible one-member suppression case. Item pickup/respawn, "
            "save/load, and multiplayer fixtures remain."
        ),
    }


def markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    contract = report["legacy_contract"]
    lines = [
        "# Zaero deathmatch item-injection audit",
        "",
        "This audit identity-records the supplied source, verifies the port contract,",
        "and joins it to the normalized retail BSP inventory.",
        "",
        "## Result",
        "",
        "- `zdmflags` remains a server-info cvar with default 0.",
        "- Bit 1 disables Flare Gun compensation damage; bit 2 disables item injection.",
        "  The port names both bits by their set-bit behavior and keeps values 1 and 2.",
        f'- The source order contains **{summary["injection_item_count"]}** items and each gets up to '
        f'**{contract["attempts_per_item"]}** starts, a **{contract["angle_step_degrees"]}°** sweep, and a '
        f'**{contract["placement_radius"]}-unit** `MASK_SHOT` trace.',
        "- One existing member suppresses the whole automatic pass. Geometry failures",
        "  after that gate do not roll back items already placed.",
        "- The port hook is content activation on every map; it does not enable Zaero",
        "  mapper semantics on stock/community maps.",
        "",
        "## Supplied-map inventory",
        "",
        f'- **{summary["supplied_map_count"]}** maps contain **{summary["supplied_deathmatch_start_count"]}** deathmatch starts.',
        f'- All supplied maps already contain at least one member, so **{summary["supplied_maps_eligible_for_injection"]}** are eligible for automatic injection.',
        f'- **{summary["maps_missing_at_least_one_set_member"]}** maps omit at least one member but still suppress injection under the historical precondition.',
        "",
        "| Map | Kind | DM starts | Present classnames | Item entities | Missing members |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for entry in report["maps"]:
        missing = ", ".join(f'`{item}`' for item in entry["missing_items"]) or "—"
        lines.append(
            f'| `{entry["map_name"]}` | {entry["map_kind"]} | '
            f'{entry["deathmatch_start_count"]} | '
            f'{entry["present_item_classname_count"]} | '
            f'{entry["present_item_entity_count"]} | {missing} |'
        )
    lines.extend(["", report["scope_note"], ""])
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zaero-root", required=True, type=Path)
    parser.add_argument("--port-root", required=True, type=Path)
    parser.add_argument("--bsp-audit", required=True, type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = build_report(args.zaero_root, args.port_root, args.bsp_audit)
        write_text(args.json_output, stable_json_text(report))
        write_text(args.markdown_output, markdown_report(report))
    except (AuditError, OSError, UnicodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
