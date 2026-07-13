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


def _audit_one_map(source: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    parsed = parse_bsp_entity_lump(source["data"])
    classname_counts: Counter[str] = Counter()
    key_counts: Counter[str] = Counter()
    value_counts: dict[str, Counter[str]] = defaultdict(Counter)
    duplicate_keys: list[dict[str, Any]] = []
    semicolon_timers: list[dict[str, Any]] = []
    changelevels: list[dict[str, Any]] = []
    for entity_index, pairs in enumerate(parsed.entities):
        values = pairs_to_multimap(pairs)
        classname = _entity_classname(values)
        classname_counts[classname] += 1
        duplicates = sorted(key for key, items in values.items() if len(items) > 1)
        if duplicates:
            duplicate_keys.append({"entity_index": entity_index, "keys": duplicates})
        for key, value in pairs:
            key_counts[key] += 1
            value_counts[key][value] += 1
        if classname == "func_timer":
            for target in values.get("target", []):
                if ";" in target:
                    semicolon_timers.append(
                        {"entity_index": entity_index, "target": target}
                    )
        if classname == "target_changelevel":
            changelevels.append(
                {
                    "entity_index": entity_index,
                    "map": values.get("map", [None])[-1],
                    "spawnpoint": values.get("spawnpoint", [None])[-1],
                    "targetname": values.get("targetname", [None])[-1],
                }
            )
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
    all_changelevels: list[dict[str, Any]] = []
    all_timers: list[dict[str, Any]] = []
    total_entities = 0
    total_coop = 0
    total_deathmatch = 0
    for source in bsp_sources:
        record, aggregate = _audit_one_map(source)
        map_records.append(record)
        total_entities += aggregate["entity_count"]
        total_coop += aggregate["coop_starts"]
        total_deathmatch += aggregate["deathmatch_starts"]
        global_classnames.update(aggregate["classnames"])
        global_keys.update(aggregate["key_counts"])
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
