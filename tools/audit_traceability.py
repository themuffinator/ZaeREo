#!/usr/bin/env python3
"""Generate fail-closed record-level source and BSP compatibility coverage."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Sequence

from audit_common import AuditError, markdown_cell, stable_json_text, write_text


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "docs" / "audits" / "source-delta.json"
DEFAULT_BSP = ROOT / "docs" / "audits" / "bsp-entities.json"
LEDGERS = (
    ROOT / "docs" / "compatibility" / "feature-matrix.md",
    ROOT / "docs" / "compatibility" / "entity-matrix.md",
    ROOT / "docs" / "compatibility" / "quirks.md",
    ROOT / "docs" / "compatibility" / "decisions.md",
)
IDENTIFIER_RE = re.compile(r"\b(?:SYS|MAP|PLY|AI)-\d{3}\b|\b[EDQ]-\d{3}\b")
ENTITY_ROW_RE = re.compile(r"^\|\s*(E-\d{3})\s*\|\s*([^|]+?)\s*\|", re.MULTILINE)


class TraceabilityError(AuditError):
    """Raised when a mechanical audit cannot be traced to a reviewed ledger."""


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise TraceabilityError(f"invalid {label} {path}: {error}") from error
    if not isinstance(value, dict):
        raise TraceabilityError(f"{label} must be a JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ledger_identifiers(repository_root: Path) -> tuple[set[str], dict[str, str]]:
    identifiers: set[str] = set()
    entity_rows: dict[str, str] = {}
    for relative in ("feature-matrix.md", "entity-matrix.md", "quirks.md", "decisions.md"):
        path = repository_root / "docs" / "compatibility" / relative
        if not path.is_file():
            raise TraceabilityError(f"missing compatibility ledger: {path}")
        text = path.read_text(encoding="utf-8")
        identifiers.update(IDENTIFIER_RE.findall(text))
        if relative == "entity-matrix.md":
            for identifier, classnames in ENTITY_ROW_RE.findall(text):
                for classname in classnames.split("/"):
                    normalized = classname.strip().strip("`")
                    if normalized:
                        entity_rows[normalized] = identifier
    return identifiers, entity_rows


def _source_route(path: str) -> dict[str, Any]:
    """Map each individual legacy record to the narrowest existing reviewed seam."""

    if path.startswith("z_debug") or path == "z_mtest.c":
        return {
            "disposition": "NON_RUNTIME",
            "ids": ["D-015", "Q-039"],
            "phase": "0-1",
            "implementation_seam": "src/zaero",
            "proof": "tests/release/test_release_surfaces.py",
            "reason": "Debug/test source is retained as evidence but denied from the Release surface.",
        }
    if path.startswith("z_"):
        return {
            "disposition": "PARITY",
            "ids": ["MAP-001", "SYS-015"],
            "phase": "3-7",
            "implementation_seam": "src/zaero",
            "proof": "tests/compatibility/test_spawn_save_contract.py",
            "reason": "Zaero-only production source is routed to the owned C++ compatibility layer.",
        }
    if path in {"game.001", "game.dsp", "game.plg", "zaero.dsp"}:
        return {
            "disposition": "TOOLING_ONLY",
            "ids": ["SYS-001", "D-002"],
            "phase": "1",
            "implementation_seam": "src/game.vcxproj",
            "proof": "tests/build/test_project_manifest.py",
            "reason": "Vintage project metadata is evidence for the modern C++ build layout, not runtime behavior.",
        }
    if path == "readme.txt":
        return {
            "disposition": "TOOLING_ONLY",
            "ids": ["SYS-003", "D-003"],
            "phase": "0-2",
            "implementation_seam": "README.md",
            "proof": "tests/repository/test_repository_scaffold.py",
            "reason": "Legacy documentation informs provenance and installation policy only.",
        }
    if path.startswith("g_phys"):
        return {
            "disposition": "ADAPT",
            "ids": ["MAP-010", "D-035"],
            "phase": "3",
            "implementation_seam": "src/g_phys.cpp",
            "proof": "tests/compatibility/test_zaero_physics_contract.py",
            "reason": "Legacy physics intent is adapted through the Rerelease lifecycle and time model.",
        }
    if path.startswith(("g_func", "g_misc", "g_spawn", "g_target", "g_trigger", "g_turret", "g_utils")):
        return {
            "disposition": "ADAPT",
            "ids": ["MAP-002", "D-018"],
            "phase": "2-3",
            "implementation_seam": "src/g_spawn.cpp",
            "proof": "tests/compatibility/test_stock_world_extensions.py",
            "reason": "Stock classname and mapper deltas are gated by Zaero map identity.",
        }
    if path.startswith(("g_items", "g_weapon", "p_", "g_cmds", "g_combat")):
        return {
            "disposition": "ADAPT",
            "ids": ["PLY-001", "D-031"],
            "phase": "4",
            "implementation_seam": "src/g_items.cpp",
            "proof": "tests/compatibility/test_zaero_items_weapons.py",
            "reason": "Player, item, weapon, HUD, and command behavior is adapted to native Rerelease state.",
        }
    if path.startswith(("g_ai", "g_monster", "m_")):
        return {
            "disposition": "ADAPT",
            "ids": ["AI-001", "D-043"],
            "phase": "5-7",
            "implementation_seam": "src/zaero/g_zaero_ai.cpp",
            "proof": "tests/compatibility/test_zaero_stock_precaches.py",
            "reason": "AI and stock-monster deltas are reviewed against Rerelease-native monster lifecycle and precaches.",
        }
    if path.startswith(("g_main", "g_save", "g_local", "game.h", "q_shared")):
        return {
            "disposition": "ADAPT",
            "ids": ["SYS-015", "MAP-009"],
            "phase": "1-3",
            "implementation_seam": "src/g_save.cpp",
            "proof": "tests/compatibility/test_spawn_save_contract.py",
            "reason": "Shared declarations and save/export differences are translated to the Rerelease API/JSON save ABI.",
        }
    return {
        "disposition": "SOURCE_AGE",
        "ids": ["D-002", "SYS-015"],
        "phase": "0-1",
        "implementation_seam": "src",
        "proof": "tests/audit/test_audit_reports.py",
        "reason": "No independent Zaero runtime contract is assumed until review distinguishes source-age drift.",
    }


def _source_records(source: dict[str, Any]) -> list[dict[str, Any]]:
    records = source.get("comparison", {}).get("file_records")
    if not isinstance(records, list):
        raise TraceabilityError("source audit lacks comparison.file_records")
    result: list[dict[str, Any]] = []
    for file_record in records:
        path = file_record.get("path")
        status = file_record.get("status")
        if not isinstance(path, str) or not isinstance(status, str):
            raise TraceabilityError("source audit file record lacks path/status")
        if status != "identical":
            result.append(
                {
                    "record_id": f"source:path:{path}",
                    "kind": "path",
                    "path": path,
                    "source_status": status,
                    **_source_route(path),
                }
            )
        for scope in ("functions", "globals"):
            delta = file_record.get(scope, {})
            if not isinstance(delta, dict):
                continue
            for change in ("added", "changed", "removed"):
                entries = delta.get(change, [])
                if not isinstance(entries, list):
                    raise TraceabilityError(f"source {scope} delta is not an array: {path}")
                for ordinal, entry in enumerate(entries, start=1):
                    name = entry.get("name") if isinstance(entry, dict) else None
                    if not isinstance(name, str) or not name:
                        raise TraceabilityError(f"source {scope} record has no name: {path}")
                    result.append(
                        {
                            "record_id": f"source:{scope[:-1]}:{change}:{path}:{name}:{ordinal}",
                            "kind": scope[:-1],
                            "change": change,
                            "path": path,
                            "name": name,
                            "lines": {
                                key: entry[key]
                                for key in ("legacy_lines", "zaero_lines")
                                if key in entry
                            },
                            **_source_route(path),
                        }
                    )
    return sorted(result, key=lambda item: item["record_id"].encode("utf-8"))


def _bsp_records(bsp: dict[str, Any], entity_rows: dict[str, str]) -> list[dict[str, Any]]:
    global_data = bsp.get("global")
    registry = bsp.get("rerelease_registry")
    if not isinstance(global_data, dict) or not isinstance(registry, dict):
        raise TraceabilityError("BSP audit lacks global/registry records")
    maps = global_data.get("classname_maps")
    keys = global_data.get("classname_key_counts")
    values = global_data.get("classname_value_counts")
    recognized = set(registry.get("all_classnames", []))
    if not isinstance(maps, dict) or not isinstance(keys, dict) or not isinstance(values, dict):
        raise TraceabilityError("BSP audit lacks per-classname key/value coverage input")
    result: list[dict[str, Any]] = []
    for classname in sorted(maps, key=lambda item: item.encode("utf-8")):
        if not isinstance(classname, str):
            raise TraceabilityError("BSP classname is not text")
        identifier = entity_rows.get(classname, "MAP-001")
        common = {
            "classname": classname,
            "ids": [identifier, "D-018"],
            "disposition": "PARITY",
            "phase": "2-8",
            "maps": maps[classname],
            "classifier": "Zaero map identity/classname dispatch (D-018)",
            "implementation_seam": "src/g_spawn.cpp",
            "save_lifecycle_surface": "native unless the linked entity contract declares saved Zaero state",
            "spawn_status": (
                "registered-in-current-rerelease" if classname in recognized else "requires-zaereo-compatibility"
            ),
            "proof": "tests/compatibility/test_spawn_save_contract.py",
        }
        result.append({"record_id": f"bsp:classname:{classname}", "kind": "classname", **common})
        class_keys = keys.get(classname)
        class_values = values.get(classname)
        if not isinstance(class_keys, dict) or not isinstance(class_values, dict):
            raise TraceabilityError(f"BSP audit has incomplete key/value record for {classname}")
        for key in sorted(class_keys, key=lambda item: item.encode("utf-8")):
            observed_values = class_values.get(key)
            if not isinstance(observed_values, dict):
                raise TraceabilityError(f"BSP audit has no values for {classname}.{key}")
            result.append(
                {
                    "record_id": f"bsp:key:{classname}:{key}",
                    "kind": "key",
                    "key": key,
                    "occurrences": class_keys[key],
                    "observed_values": observed_values,
                    "key_semantics": "explicit mapper surface; see linked classname contract",
                    **common,
                }
            )
            if key in {"spawnflags", "spawnflags2"}:
                for value, count in sorted(observed_values.items(), key=lambda item: item[0].encode("utf-8")):
                    result.append(
                        {
                            "record_id": f"bsp:spawnflag:{classname}:{key}:{value}",
                            "kind": "spawnflag-value",
                            "key": key,
                            "value": value,
                            "occurrences": count,
                            "flag_semantics": "authored spawnflag value; preserve or explicitly adapt through the linked contract",
                            **common,
                        }
                    )
    return sorted(result, key=lambda item: item["record_id"].encode("utf-8"))


def _validate_records(records: list[dict[str, Any]], identifiers: set[str]) -> list[dict[str, str]]:
    uncovered: list[dict[str, str]] = []
    seen: set[str] = set()
    for record in records:
        record_id = record.get("record_id")
        if not isinstance(record_id, str) or not record_id or record_id in seen:
            raise TraceabilityError(f"invalid or duplicate traceability record id: {record_id!r}")
        seen.add(record_id)
        ids = record.get("ids")
        if not isinstance(ids, list) or not ids or any(identifier not in identifiers for identifier in ids):
            uncovered.append({"record_id": record_id, "reason": "missing-or-unknown-ledger-id"})
            continue
        if record.get("disposition") not in {"PARITY", "ADAPT", "FIX", "SOURCE_AGE", "NON_RUNTIME", "TOOLING_ONLY"}:
            uncovered.append({"record_id": record_id, "reason": "invalid-disposition"})
            continue
        for field in ("phase", "implementation_seam", "proof"):
            value = record.get(field)
            if not isinstance(value, str) or not value:
                uncovered.append({"record_id": record_id, "reason": f"missing-{field}"})
                break
    return uncovered


def build_traceability_reports(
    source_path: Path = DEFAULT_SOURCE,
    bsp_path: Path = DEFAULT_BSP,
    *,
    repository_root: Path = ROOT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_path = source_path.resolve()
    bsp_path = bsp_path.resolve()
    repository_root = repository_root.resolve()
    source = _read_json(source_path, "source audit")
    bsp = _read_json(bsp_path, "BSP audit")
    identifiers, entity_rows = _ledger_identifiers(repository_root)
    source_records = _source_records(source)
    bsp_records = _bsp_records(bsp, entity_rows)
    source_uncovered = _validate_records(source_records, identifiers)
    bsp_uncovered = _validate_records(bsp_records, identifiers)
    source_report = {
        "format": "ZaeREo source delta traceability coverage",
        "schema_version": 1,
        "inputs": {"source_delta_sha256": _sha256(source_path)},
        "summary": {
            "record_count": len(source_records),
            "path_record_count": sum(record["kind"] == "path" for record in source_records),
            "function_record_count": sum(record["kind"] == "function" for record in source_records),
            "global_record_count": sum(record["kind"] == "global" for record in source_records),
            "uncovered_count": len(source_uncovered),
            "complete": not source_uncovered,
        },
        "records": source_records,
        "uncovered": source_uncovered,
    }
    bsp_report = {
        "format": "ZaeREo BSP contract traceability coverage",
        "schema_version": 1,
        "inputs": {"bsp_entities_sha256": _sha256(bsp_path)},
        "summary": {
            "record_count": len(bsp_records),
            "classname_record_count": sum(record["kind"] == "classname" for record in bsp_records),
            "key_record_count": sum(record["kind"] == "key" for record in bsp_records),
            "spawnflag_value_record_count": sum(record["kind"] == "spawnflag-value" for record in bsp_records),
            "uncovered_count": len(bsp_uncovered),
            "complete": not bsp_uncovered,
        },
        "records": bsp_records,
        "uncovered": bsp_uncovered,
    }
    return source_report, bsp_report


def _coverage_markdown(report: dict[str, Any], title: str, input_label: str) -> str:
    summary = report["summary"]
    lines = [
        f"# {title}",
        "",
        "This file is generated by `tools/audit_traceability.py`; do not edit it by hand.",
        "A covered record has review routing, not a completed gameplay claim.",
        "",
        "## Summary",
        "",
        "| Measure | Count |",
        "| --- | ---: |",
        f"| Input SHA-256 | `{report['inputs'][input_label]}` |",
        f"| Records | {summary['record_count']} |",
        f"| Uncovered | {summary['uncovered_count']} |",
        f"| Complete | `{str(summary['complete']).lower()}` |",
        "",
        "## Record routing",
        "",
        "| Record | Kind | Disposition | Ledger IDs | Phase | Seam | Proof |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in report["records"]:
        ids = ", ".join(f"`{identifier}`" for identifier in record["ids"])
        lines.append(
            f"| `{markdown_cell(record['record_id'])}` | {record['kind']} | {record['disposition']} | "
            f"{ids} | {markdown_cell(record['phase'])} | `{markdown_cell(record['implementation_seam'])}` | "
            f"`{markdown_cell(record['proof'])}` |"
        )
    return "\n".join(lines).rstrip() + "\n"


def source_coverage_markdown(report: dict[str, Any]) -> str:
    return _coverage_markdown(report, "Zaero source delta traceability coverage", "source_delta_sha256")


def bsp_coverage_markdown(report: dict[str, Any]) -> str:
    return _coverage_markdown(report, "Zaero BSP contract traceability coverage", "bsp_entities_sha256")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-audit", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--bsp-audit", type=Path, default=DEFAULT_BSP)
    parser.add_argument("--source-json-output", type=Path, required=True)
    parser.add_argument("--source-markdown-output", type=Path, required=True)
    parser.add_argument("--bsp-json-output", type=Path, required=True)
    parser.add_argument("--bsp-markdown-output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        source_report, bsp_report = build_traceability_reports(args.source_audit, args.bsp_audit)
        write_text(args.source_json_output, stable_json_text(source_report))
        write_text(args.source_markdown_output, source_coverage_markdown(source_report))
        write_text(args.bsp_json_output, stable_json_text(bsp_report))
        write_text(args.bsp_markdown_output, bsp_coverage_markdown(bsp_report))
    except (OSError, TraceabilityError) as error:
        print(f"audit_traceability.py: {error}", file=sys.stderr)
        return 2
    if not source_report["summary"]["complete"] or not bsp_report["summary"]["complete"]:
        print("audit_traceability.py: traceability coverage is incomplete", file=sys.stderr)
        return 3
    print(
        "traceability coverage complete: "
        f"source_records={source_report['summary']['record_count']} "
        f"bsp_records={bsp_report['summary']['record_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
