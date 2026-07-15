#!/usr/bin/env python3
"""Audit Zaero's stock-monster precache extractions and port adaptation."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_common import (  # noqa: E402
    AuditError,
    checked_file,
    checked_root,
    sha256_file,
    stable_json_text,
    write_text,
)
from audit_source_delta import _candidate_function_name, _mask_non_code  # noqa: E402


PRECACHE_NAME_RE = re.compile(
    r"^SP_(?:monster|misc)_[A-Za-z0-9_]+_precache$"
)
ZAERO_MAX_SOUNDS_RE = re.compile(r"^\s*#define\s+MAX_SOUNDS\s+(\d+)", re.MULTILINE)
RERELEASE_MAX_SOUNDS_RE = re.compile(
    r"constexpr\s+size_t\s+MAX_SOUNDS\s*=\s*(\d+)\s*;"
)
RERELEASE_OLD_MAX_SOUNDS_RE = re.compile(
    r"MAX_SOUNDS_OLD\s*=\s*(\d+)"
)


def _identity(path: Path, root: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256_file(path),
        "size": path.stat().st_size,
    }


def _read_latin1(path: Path) -> str:
    return path.read_text(encoding="latin-1")


@dataclass(frozen=True)
class FunctionRange:
    name: str
    start_line: int
    end_line: int


def _function_records(path: Path) -> list[FunctionRange]:
    """Extract ordinary functions at file or namespace scope."""

    text = _read_latin1(path)
    masked = _mask_non_code(text)
    depth = 0
    segment_start = 0
    active: list[tuple[str, int, int]] = []
    records: list[FunctionRange] = []
    for index, char in enumerate(masked):
        if char == "{":
            signature = masked[segment_start:index]
            name = _candidate_function_name(signature)
            depth += 1
            if name is not None:
                leading = len(signature) - len(signature.lstrip())
                start = segment_start + leading
                active.append((name, start, depth))
            segment_start = index + 1
        elif char == "}":
            if active and active[-1][2] == depth:
                name, start, _ = active.pop()
                records.append(
                    FunctionRange(
                        name=name,
                        start_line=text.count("\n", 0, start) + 1,
                        end_line=text.count("\n", 0, index) + 1,
                    )
                )
            depth = max(0, depth - 1)
            segment_start = index + 1
        elif char == ";":
            segment_start = index + 1
    return sorted(
        records,
        key=lambda record: (record.start_line, record.end_line, record.name),
    )


def _call_sites(paths: Iterable[Path], symbol: str, root: Path) -> list[dict[str, Any]]:
    pattern = re.compile(rf"\b{re.escape(symbol)}\s*\(")
    sites: list[dict[str, Any]] = []
    for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
        text = _read_latin1(path)
        masked = _mask_non_code(text)
        functions = _function_records(path)
        for match in pattern.finditer(masked):
            line = masked.count("\n", 0, match.start()) + 1
            caller = next(
                (
                    record
                    for record in functions
                    if record.start_line <= line <= record.end_line
                ),
                None,
            )
            if caller is None:
                # A file-scope declaration is not a consumer.
                continue
            if caller.name == symbol and line == caller.start_line:
                # The function definition is not a recursive call.
                continue
            sites.append(
                {
                    "caller": caller.name,
                    "line": line,
                    "path": path.relative_to(root).as_posix(),
                }
            )
    return sorted(
        sites,
        key=lambda item: (item["path"].encode("utf-8"), item["line"], item["caller"]),
    )


def _require_call_set(
    actual: list[dict[str, Any]], expected: set[tuple[str, str]], label: str
) -> None:
    observed = {(item["path"], item["caller"]) for item in actual}
    if observed != expected:
        raise AuditError(
            f"{label} call graph changed: expected {sorted(expected)!r}, "
            f"found {sorted(observed)!r}"
        )


def _extract_limit(pattern: re.Pattern[str], text: str, label: str) -> int:
    match = pattern.search(text)
    if match is None:
        raise AuditError(f"{label} no longer declares the expected sound limit")
    return int(match.group(1))


def _source_files(root: Path, suffix: str) -> list[Path]:
    return sorted(
        (path for path in root.rglob(f"*{suffix}") if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix().encode("utf-8"),
    )


def build_report(
    zaero_root: Path,
    legacy_root: Path,
    rerelease_root: Path,
    port_root: Path,
) -> dict[str, Any]:
    zaero_root = checked_root(zaero_root, "Zaero source root")
    legacy_root = checked_root(legacy_root, "legacy Quake II game root")
    rerelease_root = checked_root(rerelease_root, "Rerelease source root")
    port_root = checked_root(port_root, "ZaeREo source root")

    stock_files: list[tuple[Path, Path]] = []
    helpers: list[dict[str, Any]] = []
    all_zaero_c = _source_files(zaero_root, ".c")
    for zaero_path in sorted(zaero_root.glob("m_*.c"), key=lambda path: path.name):
        legacy_path = legacy_root / zaero_path.name
        if not legacy_path.is_file():
            continue
        stock_files.append((zaero_path, legacy_path))
        legacy_names = {record.name for record in _function_records(legacy_path)}
        for record in _function_records(zaero_path):
            if record.name in legacy_names or not PRECACHE_NAME_RE.fullmatch(record.name):
                continue
            calls = _call_sites(all_zaero_c, record.name, zaero_root)
            external = [item for item in calls if item["path"] != zaero_path.name]
            helpers.append(
                {
                    "call_sites": calls,
                    "definition_lines": [record.start_line, record.end_line],
                    "external_call_sites": external,
                    "name": record.name,
                    "owner": zaero_path.name,
                }
            )
    helpers.sort(key=lambda item: (item["owner"], item["name"]))
    if not helpers:
        raise AuditError("no Zaero-only stock precache helpers were found")

    external_helpers = [item for item in helpers if item["external_call_sites"]]
    external_sites = [
        site for helper in external_helpers for site in helper["external_call_sites"]
    ]

    rerelease_infantry = checked_file(
        rerelease_root / "m_infantry.cpp", "Rerelease m_infantry.cpp"
    )
    rerelease_turret = checked_file(
        rerelease_root / "g_turret.cpp", "Rerelease g_turret.cpp"
    )
    port_infantry = checked_file(port_root / "m_infantry.cpp", "port m_infantry.cpp")
    port_turret = checked_file(port_root / "g_turret.cpp", "port g_turret.cpp")
    port_handler = checked_file(
        port_root / "zaero" / "g_zaero_handler.cpp", "port Handler source"
    )
    port_hound = checked_file(
        port_root / "zaero" / "g_zaero_hound.cpp", "port Hound source"
    )

    baseline_calls = _call_sites(
        [rerelease_infantry, rerelease_turret], "InfantryPrecache", rerelease_root
    )
    _require_call_set(
        baseline_calls,
        {
            ("g_turret.cpp", "SP_turret_driver"),
            ("m_infantry.cpp", "SP_monster_infantry"),
        },
        "Rerelease InfantryPrecache",
    )
    port_calls = _call_sites(
        [port_infantry, port_turret, port_handler], "InfantryPrecache", port_root
    )
    _require_call_set(
        port_calls,
        {
            ("g_turret.cpp", "SP_turret_driver"),
            ("m_infantry.cpp", "InfantryConvertFromZaeroHandler"),
            ("m_infantry.cpp", "SP_monster_infantry"),
            ("zaero/g_zaero_handler.cpp", "handler_precache"),
        },
        "ZaeREo InfantryPrecache",
    )
    hound_calls = _call_sites(
        [port_handler, port_hound], "ZaeroHoundPrecache", port_root
    )
    _require_call_set(
        hound_calls,
        {("zaero/g_zaero_handler.cpp", "handler_precache")},
        "ZaeREo ZaeroHoundPrecache",
    )

    zaero_handler = checked_file(zaero_root / "z_handler.c", "Zaero z_handler.c")
    zaero_handler_text = _read_latin1(zaero_handler)
    for fragment in (
        "SP_monster_infantry_precache();",
        "SP_monster_hound_precache();",
    ):
        if fragment not in zaero_handler_text:
            raise AuditError(f"Zaero Handler no longer contains {fragment}")

    zaero_shared = checked_file(zaero_root / "q_shared.h", "Zaero q_shared.h")
    rerelease_game = checked_file(rerelease_root / "game.h", "Rerelease game.h")
    zaero_limit = _extract_limit(
        ZAERO_MAX_SOUNDS_RE, _read_latin1(zaero_shared), "Zaero q_shared.h"
    )
    rerelease_game_text = _read_latin1(rerelease_game)
    rerelease_limit = _extract_limit(
        RERELEASE_MAX_SOUNDS_RE, rerelease_game_text, "Rerelease game.h"
    )
    rerelease_old_limit = _extract_limit(
        RERELEASE_OLD_MAX_SOUNDS_RE, rerelease_game_text, "Rerelease game.h"
    )

    zaero_project = checked_file(zaero_root / "zaero.dsp", "Zaero project file")
    zaero_main = checked_file(zaero_root / "g_main.c", "Zaero g_main.c")
    zaero_trigger = checked_file(zaero_root / "z_trigger.c", "Zaero z_trigger.c")
    project_text = _read_latin1(zaero_project)
    main_text = _read_latin1(zaero_main)
    trigger_text = _read_latin1(zaero_trigger)
    cache_facts = {
        "allocates_per_level_list_and_names": all(
            fragment in trigger_text
            for fragment in (
                "gi.TagMalloc (sizeof(list_t), TAG_LEVEL)",
                "gi.TagMalloc (strlen(name) + 1, TAG_LEVEL)",
            )
        ),
        "intercepts_global_soundindex": "gi.soundindex = internalSoundIndex;" in main_text,
        "lowercases_caller_buffer_in_place": "name[i] = tolower(name[i]);" in trigger_text,
        "rejects_at_legacy_limit_with_zero": all(
            fragment in trigger_text
            for fragment in ("numSounds >= MAX_SOUNDS-1", "return 0;")
        ),
        "supplied_project_defines_cache_sound": bool(
            re.search(r'/D\s+"CACHE_SOUND"', project_text, re.IGNORECASE)
        ),
    }
    if not all(
        value
        for key, value in cache_facts.items()
        if key != "supplied_project_defines_cache_sound"
    ):
        raise AuditError("legacy CACHE_SOUND implementation no longer matches the audit")

    port_texts = {
        path.relative_to(port_root).as_posix(): path.read_text(encoding="utf-8")
        for path in (port_infantry, port_handler, port_hound)
    }
    port_all_source_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for suffix in (".cpp", ".h")
        for path in _source_files(port_root, suffix)
    )
    legacy_cache_symbols = (
        "CACHE_SOUND",
        "internalSoundIndex",
        "actual_soundindex",
        "soundNumRejected",
    )
    port_strategy = {
        "cached_soundindex_files": sorted(
            path for path, text in port_texts.items() if "cached_soundindex" in text
        ),
        "legacy_cache_interceptor_symbols_present": sorted(
            symbol for symbol in legacy_cache_symbols if symbol in port_all_source_text
        ),
        "uses_cached_assignments": all(
            "cached_soundindex" in text and ".assign(" in text
            for text in port_texts.values()
        ),
    }
    if port_strategy["legacy_cache_interceptor_symbols_present"]:
        raise AuditError("port source contains legacy CACHE_SOUND interceptor symbols")
    if not port_strategy["uses_cached_assignments"]:
        raise AuditError("port precache paths no longer use cached_soundindex assignments")

    source_counts = Counter(item["owner"] for item in helpers)
    zaero_input_paths = {path for path, _ in stock_files} | {
        zaero_handler,
        zaero_main,
        zaero_project,
        zaero_shared,
        zaero_trigger,
    }
    legacy_input_paths = {path for _, path in stock_files}
    return {
        "audit": "zaero-stock-monster-precaches",
        "schema_version": 1,
        "inputs": {
            "legacy_sources": [
                _identity(path, legacy_root)
                for path in sorted(legacy_input_paths, key=lambda item: item.name)
            ],
            "port_sources": [
                _identity(path, port_root)
                for path in (port_turret, port_infantry, port_handler, port_hound)
            ],
            "rerelease_sources": [
                _identity(path, rerelease_root)
                for path in (rerelease_game, rerelease_turret, rerelease_infantry)
            ],
            "zaero_sources": [
                _identity(path, zaero_root)
                for path in sorted(
                    zaero_input_paths,
                    key=lambda item: item.relative_to(zaero_root).as_posix(),
                )
            ],
        },
        "legacy_sound_index_context": {
            "cache_sound_workaround": cache_facts,
            "rerelease_legacy_compatibility_limit": rerelease_old_limit,
            "rerelease_max_sounds": rerelease_limit,
            "zaero_max_sounds": zaero_limit,
        },
        "port_adaptation": {
            "classification": "ADAPT",
            "decision": "D-043",
            "handler_dependencies": {
                "custom_hound_precache": "ZaeroHoundPrecache",
                "native_stock_precache": "InfantryPrecache",
            },
            "native_rerelease_calls": baseline_calls,
            "port_calls": port_calls,
            "port_hound_calls": hound_calls,
            "sound_index_strategy": port_strategy,
        },
        "stock_precache_extractions": helpers,
        "summary": {
            "external_call_site_count": len(external_sites),
            "externally_reused_helper_count": len(external_helpers),
            "helper_count": len(helpers),
            "helpers_by_source": dict(sorted(source_counts.items())),
            "source_file_count": len(source_counts),
        },
        "scope_note": (
            "This audit classifies only the added stock precache helper surfaces and "
            "their call graph. Other resource, AI, EMP, flash, cadence, and behavior "
            "changes in the same stock files require their own compatibility rows."
        ),
    }


def markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    limits = report["legacy_sound_index_context"]
    cache = limits["cache_sound_workaround"]
    adaptation = report["port_adaptation"]
    lines = [
        "# Zaero stock-monster precache audit",
        "",
        "This normalized audit classifies AI-015 and the related legacy sound-index",
        "workaround. It is source/static evidence, not live audible or map-completion proof.",
        "",
        "## Result",
        "",
        f'- Zaero adds **{summary["helper_count"]}** stock precache helpers across '
        f'**{summary["source_file_count"]}** source files.',
        f'- Only **{summary["externally_reused_helper_count"]}** helper has a cross-file '
        f'consumer, at **{summary["external_call_site_count"]}** call site: '
        "`SP_monster_infantry_precache` from Handler.",
        "- The Rerelease baseline already exposes `InfantryPrecache` to both native",
        "  Infantry and `SP_turret_driver`; ZaeREo reuses it for Handler precache and",
        "  conversion, while Hound keeps its Zaero-owned precache.",
        "- The other stock helper extractions are not port requirements by themselves.",
        "  Other behavior changes in those files remain separately classified.",
        "",
        "## Added stock helper call graph",
        "",
        "| Owner | Helper | Local consumers | Cross-file consumers |",
        "| --- | --- | --- | --- |",
    ]
    for helper in report["stock_precache_extractions"]:
        local = [
            item["caller"]
            for item in helper["call_sites"]
            if item["path"] == helper["owner"]
        ]
        external = [
            f'{item["path"]}:{item["caller"]}'
            for item in helper["external_call_sites"]
        ]
        lines.append(
            f'| {helper["owner"]} | `{helper["name"]}` | '
            f'{", ".join(f"`{name}`" for name in local) or "—"} | '
            f'{", ".join(f"`{name}`" for name in external) or "—"} |'
        )
    lines.extend(
        [
            "",
            "## Sound-index context",
            "",
            "| Fact | Result |",
            "| --- | --- |",
            f'| Legacy Zaero `MAX_SOUNDS` | {limits["zaero_max_sounds"]} |',
            f'| Rerelease `MAX_SOUNDS` | {limits["rerelease_max_sounds"]} |',
            f'| Rerelease legacy-compatibility value | {limits["rerelease_legacy_compatibility_limit"]} |',
            f'| Supplied project defines `CACHE_SOUND` | {str(cache["supplied_project_defines_cache_sound"]).lower()} |',
            f'| Workaround intercepts global sound indexing | {str(cache["intercepts_global_soundindex"]).lower()} |',
            f'| Workaround mutates caller name buffers | {str(cache["lowercases_caller_buffer_in_place"]).lower()} |',
            f'| Workaround rejects at the legacy limit | {str(cache["rejects_at_legacy_limit_with_zero"]).lower()} |',
            f'| Workaround allocates a level list and copied names | {str(cache["allocates_per_level_list_and_names"]).lower()} |',
            "",
            "## D-043 disposition",
            "",
            "Use the native Rerelease `InfantryPrecache` surface for Handler and retain",
            "native stock spawn paths everywhere else. Use `cached_soundindex` assignments",
            "for Handler, Hound, and Infantry resources. Do not port the disabled legacy",
            "global interceptor or its 256-entry rejection behavior. Full all-map resource",
            "reference and audible verification remains open.",
            "",
            report["scope_note"],
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zaero-root", required=True, type=Path)
    parser.add_argument("--legacy-root", required=True, type=Path)
    parser.add_argument("--rerelease-root", required=True, type=Path)
    parser.add_argument("--port-root", required=True, type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = build_report(
            args.zaero_root,
            args.legacy_root,
            args.rerelease_root,
            args.port_root,
        )
        write_text(args.json_output, stable_json_text(report))
        write_text(args.markdown_output, markdown_report(report))
    except (AuditError, OSError, UnicodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
