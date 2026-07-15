#!/usr/bin/env python3
"""Inventory every effective Zaero BSP entity lump and Rerelease registry gap."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Sequence

from audit_common import (
    AuditError,
    BSP_HEADER,
    BSP_LUMP,
    PakArchive,
    PakEntryRecord,
    case_collision_groups,
    checked_file,
    checked_root,
    discover_paks,
    markdown_cell,
    normalize_runtime_path,
    pairs_to_multimap,
    parse_bsp_entity_lump,
    parse_pak,
    sha256_file,
    stable_json_text,
    write_text,
)


SPAWN_ENTRY_RE = re.compile(
    r'\{\s*"([^"\r\n]+)"\s*,\s*SP_[A-Za-z_][A-Za-z0-9_]*\s*\}'
)
ITEM_CLASSNAME_RE = re.compile(
    r'/\*\s*classname\s*\*/\s*"([^"\r\n]+)"', re.IGNORECASE
)
TARGET_REFERENCE_KEYS = (
    "target",
    "pathtarget",
    "deathtarget",
    "killtarget",
    "combattarget",
)
ACTIVATION_TARGET_KEYS = frozenset(("target", "pathtarget", "deathtarget"))


def _resolve_paks(root: Path, arguments: Sequence[str] | None) -> list[Path]:
    if not arguments:
        result = discover_paks(root)
    else:
        result = []
        for value in arguments:
            candidate = Path(value)
            if not candidate.is_absolute():
                candidate = root / candidate
            result.append(checked_file(candidate, "PAK layer"))
    if not result:
        raise AuditError("no PAK layers were found or supplied")
    resolved = [path.resolve() for path in result]
    if len(resolved) != len(set(resolved)):
        raise AuditError("the PAK layer list contains a duplicate file")
    if len({path.name for path in resolved}) != len(resolved):
        raise AuditError("PAK layer basenames must be unique for portable reports")
    return resolved


def extract_rerelease_registry(root: Path) -> dict[str, Any]:
    spawn_file = checked_file(root / "g_spawn.cpp", "Rerelease spawn registry")
    item_file = checked_file(root / "g_items.cpp", "Rerelease item registry")
    spawn_text = spawn_file.read_text(encoding="utf-8", errors="replace")
    item_text = item_file.read_text(encoding="utf-8", errors="replace")
    spawn_names = sorted(set(SPAWN_ENTRY_RE.findall(spawn_text)))
    item_names = sorted(set(ITEM_CLASSNAME_RE.findall(item_text)))
    all_names = sorted(set(spawn_names) | set(item_names))
    return {
        "all_classnames": all_names,
        "all_classname_count": len(all_names),
        "item_classnames": item_names,
        "item_registry_sha256": sha256_file(item_file),
        "spawn_classnames": spawn_names,
        "spawn_registry_sha256": sha256_file(spawn_file),
    }


def _read_loose_bsps(root: Path) -> list[dict[str, Any]]:
    maps_root = root / "maps"
    if not maps_root.exists():
        return []
    if not maps_root.is_dir():
        raise AuditError(f"loose maps path is not a directory: {maps_root}")
    root_resolved = root.resolve()
    records: list[dict[str, Any]] = []
    for candidate in maps_root.rglob("*"):
        if candidate.is_symlink():
            raise AuditError(f"loose maps tree contains a symbolic link: {candidate}")
        if not candidate.is_file() or candidate.suffix.casefold() != ".bsp":
            continue
        resolved = candidate.resolve()
        try:
            runtime_path = resolved.relative_to(root_resolved).as_posix()
        except ValueError as error:
            raise AuditError(f"loose BSP escapes the assets root: {candidate}") from error
        records.append(
            {
                "container": "loose",
                "data": resolved.read_bytes(),
                "path": normalize_runtime_path(runtime_path, "loose BSP path"),
                "sha256": sha256_file(resolved),
                "size": resolved.stat().st_size,
            }
        )
    return sorted(records, key=lambda record: record["path"].encode("utf-8"))


def _effective_bsps(root: Path, pak_paths: Sequence[Path]) -> tuple[list[dict[str, Any]], list[PakArchive]]:
    # See audit_assets.py: retail Zaero PAK name fields can contain ignored
    # bytes after their first NUL. BSP extraction opts into that one legacy
    # representation quirk while retaining every path/range safety check.
    archives = [
        parse_pak(path, label=path.name, allow_nonzero_name_padding=True)
        for path in pak_paths
    ]
    effective: dict[str, dict[str, Any]] = {}
    for archive in archives:
        for entry in archive.entries:
            if not (
                entry.runtime_path.casefold().startswith("maps/")
                and entry.runtime_path.casefold().endswith(".bsp")
            ):
                continue
            effective[entry.runtime_path] = {
                "archive": archive,
                "container": archive.label,
                "entry": entry,
                "path": entry.runtime_path,
                "sha256": entry.sha256,
                "size": entry.size,
            }
    for loose in _read_loose_bsps(root):
        effective[loose["path"]] = loose
    collisions = case_collision_groups(effective.keys())
    if collisions:
        raise AuditError(f"effective BSP paths differ only by case: {collisions}")
    result: list[dict[str, Any]] = []
    for path, source in sorted(effective.items(), key=lambda item: item[0].encode("utf-8")):
        if "data" in source:
            data = source["data"]
        else:
            archive: PakArchive = source["archive"]
            entry: PakEntryRecord = source["entry"]
            data = archive.read_entry(entry)
        result.append(
            {
                "container": source["container"],
                "data": data,
                "path": path,
                "sha256": source["sha256"],
                "size": source["size"],
            }
        )
    return result, archives


def _ordered_counts(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items(), key=lambda item: item[0].encode("utf-8")))


def _ordered_value_counts(
    counters: dict[str, Counter[str]],
) -> dict[str, dict[str, int]]:
    return {
        key: _ordered_counts(counters[key])
        for key in sorted(counters, key=lambda value: value.encode("utf-8"))
    }


def _entity_classname(values: dict[str, list[str]]) -> str:
    classnames = values.get("classname")
    return classnames[-1] if classnames else "[missing classname]"


def _target_references(
    entities: Sequence[tuple[str, dict[str, list[str]]]], targetname: str | None
) -> list[dict[str, Any]]:
    if not targetname:
        return []
    references: list[dict[str, Any]] = []
    for entity_index, (classname, values) in enumerate(entities):
        for key in TARGET_REFERENCE_KEYS:
            for raw_value in values.get(key, []):
                names = (
                    raw_value.split(";")
                    if key == "target" and classname == "func_timer"
                    else [raw_value]
                )
                if targetname not in names:
                    continue
                references.append(
                    {
                        "activates": key in ACTIVATION_TARGET_KEYS,
                        "classname": classname,
                        "entity_index": entity_index,
                        "key": key,
                        "value": raw_value,
                    }
                )
    return references


def _changelevel_destination(
    raw_value: str | None, available_maps: set[str]
) -> dict[str, Any]:
    if not raw_value:
        return {
            "destination_bsp": None,
            "destination_kind": "missing-value",
            "destination_present": False,
        }
    if "+" in raw_value or raw_value.casefold().endswith((".cin", ".pcx")):
        return {
            "destination_bsp": None,
            "destination_kind": "presentation-chain",
            "destination_present": None,
        }
    map_name = raw_value.lstrip("*").split("$", 1)[0]
    return {
        "destination_bsp": f"maps/{map_name}.bsp",
        "destination_kind": "bsp",
        "destination_present": map_name.casefold() in available_maps,
    }


def _audit_one_map(source: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    parsed = parse_bsp_entity_lump(source["data"])
    # `SpawnEntities` receives the entity string, not the resolved BSP bytes.
    # Record a stable hash of exactly the bytes it can observe (with only the
    # conventional trailing C-string terminators removed).  This is useful for
    # conservative runtime identity and save-mismatch diagnostics, but is not
    # a substitute for the full BSP hash retained in `sha256` below.
    entity_offset, entity_length = BSP_LUMP.unpack_from(source["data"], BSP_HEADER.size)
    entity_lump = source["data"][entity_offset : entity_offset + entity_length].rstrip(b"\0")
    classname_counts: Counter[str] = Counter()
    key_counts: Counter[str] = Counter()
    value_counts: dict[str, Counter[str]] = defaultdict(Counter)
    classname_key_counts: dict[str, Counter[str]] = defaultdict(Counter)
    classname_value_counts: dict[str, dict[str, Counter[str]]] = defaultdict(
        lambda: defaultdict(Counter)
    )
    duplicate_keys: list[dict[str, Any]] = []
    semicolon_timers: list[dict[str, Any]] = []
    changelevels: list[dict[str, Any]] = []
    entity_values: list[tuple[str, dict[str, list[str]]]] = []
    for entity_index, pairs in enumerate(parsed.entities):
        values = pairs_to_multimap(pairs)
        classname = _entity_classname(values)
        entity_values.append((classname, values))
        classname_counts[classname] += 1
        duplicates = sorted(key for key, items in values.items() if len(items) > 1)
        if duplicates:
            duplicate_keys.append({"entity_index": entity_index, "keys": duplicates})
        for key, value in pairs:
            key_counts[key] += 1
            value_counts[key][value] += 1
            classname_key_counts[classname][key] += 1
            classname_value_counts[classname][key][value] += 1
        if classname == "func_timer":
            for target in values.get("target", []):
                if ";" in target:
                    semicolon_timers.append(
                        {"entity_index": entity_index, "target": target}
                    )
        if classname == "target_changelevel":
            targetname = values.get("targetname", [None])[-1]
            changelevels.append(
                {
                    "activation_reference_count": 0,
                    "entity_index": entity_index,
                    "map": values.get("map", [None])[-1],
                    "other_reference_count": 0,
                    "spawnpoint": values.get("spawnpoint", [None])[-1],
                    "target_references": [],
                    "targetname": targetname,
                }
            )

    # A target can be defined after its changelevel, so repeat reference
    # resolution against the complete entity list rather than retaining the
    # partial result collected during the single-pass inventory.
    for changelevel in changelevels:
        references = _target_references(entity_values, changelevel["targetname"])
        changelevel["activation_reference_count"] = sum(
            reference["activates"] for reference in references
        )
        changelevel["other_reference_count"] = sum(
            not reference["activates"] for reference in references
        )
        changelevel["target_references"] = references
    coop_starts = classname_counts["info_player_coop"]
    deathmatch_starts = classname_counts["info_player_deathmatch"]
    path = source["path"]
    record = {
        "bsp_version": parsed.version,
        "changelevels": changelevels,
        "classname_counts": _ordered_counts(classname_counts),
        "container": source["container"],
        "coop_start_count": coop_starts,
        "deathmatch_start_count": deathmatch_starts,
        "duplicate_keys": duplicate_keys,
        "entity_lump_sha256": hashlib.sha256(entity_lump).hexdigest(),
        "entity_lump_size": len(entity_lump),
        "entity_count": len(parsed.entities),
        "key_counts": _ordered_counts(key_counts),
        "map_kind": "campaign" if coop_starts else "deathmatch",
        "map_name": Path(path).stem,
        "path": path,
        "semicolon_timer_targets": semicolon_timers,
        "sha256": source["sha256"],
        "size": source["size"],
        "value_counts": _ordered_value_counts(value_counts),
    }
    aggregate = {
        "changelevels": changelevels,
        "classnames": classname_counts,
        "classname_key_counts": classname_key_counts,
        "classname_value_counts": classname_value_counts,
        "coop_starts": coop_starts,
        "deathmatch_starts": deathmatch_starts,
        "entity_count": len(parsed.entities),
        "key_counts": key_counts,
        "semicolon_timers": semicolon_timers,
        "value_counts": value_counts,
    }
    return record, aggregate


def build_bsp_report(
    assets_root: Path,
    pak_paths: Sequence[Path],
    rerelease_root: Path,
    *,
    assets_label: str = "zaero-install",
    rerelease_label: str = "quake2-rerelease-api-2023",
) -> dict[str, Any]:
    bsp_sources, archives = _effective_bsps(assets_root, pak_paths)
    if not bsp_sources:
        raise AuditError("no effective maps/*.bsp files were found")
    registry = extract_rerelease_registry(rerelease_root)

    map_records: list[dict[str, Any]] = []
    global_classnames: Counter[str] = Counter()
    classname_maps: dict[str, set[str]] = defaultdict(set)
    global_keys: Counter[str] = Counter()
    global_values: dict[str, Counter[str]] = defaultdict(Counter)
    global_classname_keys: dict[str, Counter[str]] = defaultdict(Counter)
    global_classname_values: dict[str, dict[str, Counter[str]]] = defaultdict(
        lambda: defaultdict(Counter)
    )
    all_changelevels: list[dict[str, Any]] = []
    all_timers: list[dict[str, Any]] = []
    total_entities = 0
    total_coop = 0
    total_deathmatch = 0
    available_maps = {
        Path(source["path"]).stem.casefold() for source in bsp_sources
    }
    for source in bsp_sources:
        record, aggregate = _audit_one_map(source)
        for changelevel in record["changelevels"]:
            changelevel.update(
                _changelevel_destination(changelevel["map"], available_maps)
            )
        map_records.append(record)
        total_entities += aggregate["entity_count"]
        total_coop += aggregate["coop_starts"]
        total_deathmatch += aggregate["deathmatch_starts"]
        global_classnames.update(aggregate["classnames"])
        global_keys.update(aggregate["key_counts"])
        for classname, keys in aggregate["classname_key_counts"].items():
            global_classname_keys[classname].update(keys)
        for classname, keys in aggregate["classname_value_counts"].items():
            for key, values in keys.items():
                global_classname_values[classname][key].update(values)
        for key, values in aggregate["value_counts"].items():
            global_values[key].update(values)
        for classname in aggregate["classnames"]:
            classname_maps[classname].add(record["map_name"])
        all_changelevels.extend(
            {"map_name": record["map_name"], **item}
            for item in aggregate["changelevels"]
        )
        all_timers.extend(
            {"map_name": record["map_name"], **item}
            for item in aggregate["semicolon_timers"]
        )

    map_classnames = set(global_classnames)
    rerelease_names = set(registry["all_classnames"])
    recognized = sorted(map_classnames & rerelease_names)
    missing = sorted(map_classnames - rerelease_names)
    campaign_count = sum(record["map_kind"] == "campaign" for record in map_records)
    deathmatch_count = len(map_records) - campaign_count
    spawnflags2_counts = _ordered_counts(global_values.get("spawnflags2", Counter()))
    orphan_changelevels = sum(
        changelevel["activation_reference_count"] == 0
        for changelevel in all_changelevels
    )
    missing_changelevel_bsps = sum(
        changelevel["destination_kind"] == "bsp"
        and not changelevel["destination_present"]
        for changelevel in all_changelevels
    )

    return {
        "format": "ZaeREo BSP entity audit",
        "global": {
            "changelevels": all_changelevels,
            "classname_counts": _ordered_counts(global_classnames),
            "classname_maps": {
                name: sorted(maps)
                for name, maps in sorted(
                    classname_maps.items(), key=lambda item: item[0].encode("utf-8")
                )
            },
            "classname_key_counts": {
                classname: _ordered_counts(keys)
                for classname, keys in sorted(
                    global_classname_keys.items(), key=lambda item: item[0].encode("utf-8")
                )
            },
            "classname_value_counts": {
                classname: _ordered_value_counts(keys)
                for classname, keys in sorted(
                    global_classname_values.items(), key=lambda item: item[0].encode("utf-8")
                )
            },
            "key_counts": _ordered_counts(global_keys),
            "semicolon_timer_targets": all_timers,
            "spawnflags2_value_counts": spawnflags2_counts,
            "value_counts": _ordered_value_counts(global_values),
        },
        "inputs": {
            "assets_label": assets_label,
            "pak_layers": [archive.label for archive in archives],
            "rerelease_label": rerelease_label,
        },
        "maps": map_records,
        "rerelease_registry": {
            **registry,
            "map_classnames_missing": missing,
            "map_classnames_missing_count": len(missing),
            "map_classnames_recognized": recognized,
            "map_classnames_recognized_count": len(recognized),
        },
        "schema_version": 1,
        "summary": {
            "campaign_map_count": campaign_count,
            "coop_start_count": total_coop,
            "deathmatch_map_count": deathmatch_count,
            "deathmatch_start_count": total_deathmatch,
            "entity_count": total_entities,
            "map_count": len(map_records),
            "missing_changelevel_bsp_count": missing_changelevel_bsps,
            "orphan_changelevel_count": orphan_changelevels,
            "target_changelevel_count": len(all_changelevels),
            "target_help_count": global_classnames["target_help"],
            "unique_classname_count": len(global_classnames),
        },
    }


def bsp_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    registry = report["rerelease_registry"]
    lines = [
        "# Zaero BSP entity audit",
        "",
        "This file is generated by `tools/audit_bsp_entities.py`; do not edit it by hand.",
        "",
        "## Summary",
        "",
        "| Measure | Count |",
        "| --- | ---: |",
        f"| Maps | {summary['map_count']} |",
        f"| Campaign maps | {summary['campaign_map_count']} |",
        f"| Deathmatch maps | {summary['deathmatch_map_count']} |",
        f"| Entity records | {summary['entity_count']} |",
        f"| Distinct classnames | {summary['unique_classname_count']} |",
        f"| Co-op starts | {summary['coop_start_count']} |",
        f"| Deathmatch starts | {summary['deathmatch_start_count']} |",
        f"| Changelevel entities | {summary['target_changelevel_count']} |",
        f"| Changelevels without activation references | {summary['orphan_changelevel_count']} |",
        f"| Missing changelevel BSP destinations | {summary['missing_changelevel_bsp_count']} |",
        f"| Rerelease-recognized map classnames | {registry['map_classnames_recognized_count']} |",
        f"| Missing map-facing classnames | {registry['map_classnames_missing_count']} |",
        "",
        "## Maps",
        "",
        "| Map | Kind | Entities | Classnames | Co-op starts | DM starts | Source |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for record in report["maps"]:
        lines.append(
            f"| `{markdown_cell(record['map_name'])}` | {record['map_kind']} | "
            f"{record['entity_count']} | {len(record['classname_counts'])} | "
            f"{record['coop_start_count']} | {record['deathmatch_start_count']} | "
            f"{markdown_cell(record['container'])} |"
        )
    lines.extend(["", "## Classnames absent from the Rerelease registry", ""])
    lines.extend(f"- `{name}`" for name in registry["map_classnames_missing"])
    lines.extend(["", "## Semicolon timer targets", ""])
    timers = report["global"]["semicolon_timer_targets"]
    if timers:
        lines.extend(["| Map | Entity | Target value |", "| --- | ---: | --- |"]) 
        for timer in timers:
            lines.append(
                f"| `{timer['map_name']}` | {timer['entity_index']} | "
                f"`{markdown_cell(timer['target'])}` |"
            )
    else:
        lines.append("None.")
    lines.extend(["", "## Changelevel target closure", ""])
    lines.extend(
        [
            "| Map | Entity | Destination | BSP present | Targetname | Activation references | Other references |",
            "| --- | ---: | --- | --- | --- | ---: | ---: |",
        ]
    )
    for changelevel in report["global"]["changelevels"]:
        present = changelevel["destination_present"]
        present_text = "n/a" if present is None else ("yes" if present else "no")
        lines.append(
            f"| `{markdown_cell(changelevel['map_name'])}` | "
            f"{changelevel['entity_index']} | "
            f"`{markdown_cell(changelevel['map'])}` | {present_text} | "
            f"`{markdown_cell(changelevel['targetname'])}` | "
            f"{changelevel['activation_reference_count']} | "
            f"{changelevel['other_reference_count']} |"
        )
    lines.extend(["", "## `spawnflags2` values", ""])
    lines.extend(["| Value | Count |", "| --- | ---: |"]) 
    for value, count in report["global"]["spawnflags2_value_counts"].items():
        lines.append(f"| `{markdown_cell(value)}` | {count} |")
    return "\n".join(lines) + "\n"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets-root", required=True, help="Zaero installation root")
    parser.add_argument("--rerelease-root", required=True, help="Rerelease source root")
    parser.add_argument(
        "--pak",
        action="append",
        help="PAK layer in precedence order; relative paths resolve under --assets-root",
    )
    parser.add_argument("--assets-label", default="zaero-install")
    parser.add_argument("--rerelease-label", default="quake2-rerelease-api-2023")
    parser.add_argument("--json-output", help="JSON output path; stdout when omitted")
    parser.add_argument("--markdown-output", help="optional Markdown summary path")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        assets_root = checked_root(args.assets_root, "assets root")
        rerelease_root = checked_root(args.rerelease_root, "Rerelease root")
        paks = _resolve_paks(assets_root, args.pak)
        report = build_bsp_report(
            assets_root,
            paks,
            rerelease_root,
            assets_label=args.assets_label,
            rerelease_label=args.rerelease_label,
        )
        write_text(args.json_output, stable_json_text(report))
        if args.markdown_output:
            write_text(args.markdown_output, bsp_markdown(report))
    except (AuditError, OSError) as error:
        print(f"audit_bsp_entities.py: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
