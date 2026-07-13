#!/usr/bin/env python3
"""Audit Zaero PAK layering and loose installation assets deterministically."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any, Sequence

from audit_common import (
    AuditError,
    PakArchive,
    case_collision_groups,
    checked_file,
    checked_root,
    discover_paks,
    extension_counts,
    markdown_cell,
    parse_pak,
    stable_json_text,
    tree_manifest,
    write_text,
)


RUNTIME_TOP_LEVEL_DIRS = frozenset(
    {
        "env",
        "maps",
        "models",
        "music",
        "pics",
        "players",
        "sound",
        "sprites",
        "textures",
        "video",
    }
)


def _resolve_paks(root: Path, arguments: Sequence[str] | None) -> list[Path]:
    if not arguments:
        paths = discover_paks(root)
    else:
        paths = []
        for value in arguments:
            candidate = Path(value)
            if not candidate.is_absolute():
                candidate = root / candidate
            paths.append(checked_file(candidate, "PAK layer"))
    if not paths:
        raise AuditError("no PAK layers were found or supplied")
    resolved = [path.resolve() for path in paths]
    if len(set(resolved)) != len(resolved):
        raise AuditError("the PAK layer list contains a duplicate file")
    labels = [path.name for path in resolved]
    if len(set(labels)) != len(labels):
        raise AuditError("PAK layer basenames must be unique for portable reports")
    return resolved


def build_asset_report(
    assets_root: Path,
    pak_paths: Sequence[Path],
    *,
    label: str = "zaero-install",
    max_pak_entries: int = 1_000_000,
) -> dict[str, Any]:
    root_manifest = tree_manifest(assets_root)
    archives: list[PakArchive] = [
        # The known retail Zaero pak0 directory contains harmless uninitialised
        # bytes after several NUL-terminated names. Quake II ignores that fixed-
        # field padding. Keep audit_common strict by default and opt in only for
        # this legacy-source boundary; the visible name is still normalized and
        # all offsets, overlaps, duplicates, and traversal are validated.
        parse_pak(
            path,
            label=path.name,
            max_entries=max_pak_entries,
            allow_nonzero_name_padding=True,
        )
        for path in pak_paths
    ]

    effective: dict[str, tuple[str, Any]] = {}
    origins: dict[str, list[dict[str, Any]]] = {}
    all_pak_paths: list[str] = []
    layer_reports: list[dict[str, Any]] = []
    for archive in archives:
        entry_reports: list[dict[str, Any]] = []
        for entry in archive.entries:
            record = {
                "offset": entry.offset,
                "path": entry.runtime_path,
                "sha256": entry.sha256,
                "size": entry.size,
            }
            entry_reports.append(record)
            origins.setdefault(entry.runtime_path, []).append(
                {
                    "container": archive.label,
                    "sha256": entry.sha256,
                    "size": entry.size,
                }
            )
            effective[entry.runtime_path] = (archive.label, entry)
            all_pak_paths.append(entry.runtime_path)
        layer_reports.append(
            {
                "directory_length": archive.directory_length,
                "directory_offset": archive.directory_offset,
                "entries": entry_reports,
                "entry_count": len(entry_reports),
                "extension_counts": extension_counts(
                    entry.runtime_path for entry in archive.entries
                ),
                "name": archive.label,
                "sha256": archive.sha256,
                "size": archive.size,
            }
        )

    selected_paks = {path.resolve() for path in pak_paths}
    loose_runtime: list[dict[str, Any]] = []
    loose_install: list[dict[str, Any]] = []
    manifest_by_path = {record["path"]: record for record in root_manifest["files"]}
    for path, record in manifest_by_path.items():
        physical = (assets_root / Path(path)).resolve()
        if physical in selected_paks or physical.suffix.casefold() == ".pak":
            continue
        top_level = path.split("/", 1)[0].casefold()
        target = loose_runtime if top_level in RUNTIME_TOP_LEVEL_DIRS else loose_install
        target.append(record)

    overrides = [
        {"path": path, "layers": layers}
        for path, layers in sorted(origins.items(), key=lambda item: item[0].encode("utf-8"))
        if len(layers) > 1
    ]
    effective_entries = [
        {
            "container": container,
            "path": path,
            "sha256": entry.sha256,
            "size": entry.size,
        }
        for path, (container, entry) in sorted(
            effective.items(), key=lambda item: item[0].encode("utf-8")
        )
    ]

    layer_case_collisions = case_collision_groups(all_pak_paths)
    effective_case_collisions = case_collision_groups(
        [*effective.keys(), *(record["path"] for record in loose_runtime)]
    )
    loose_exact_overrides = sorted(
        [record["path"] for record in loose_runtime if record["path"] in effective]
    )
    warnings: list[str] = []
    if layer_case_collisions:
        warnings.append("PAK layers contain paths that differ only by case")
    if effective_case_collisions:
        warnings.append("effective runtime paths contain case collisions")
    if loose_exact_overrides:
        warnings.append("loose runtime files override exact PAK paths")
    if root_manifest["case_collisions"]:
        warnings.append("the installation tree contains case-colliding physical paths")

    total_pak_entries = sum(len(archive.entries) for archive in archives)
    return {
        "case_checks": {
            "all_pak_layer_collisions": layer_case_collisions,
            "effective_runtime_collisions": effective_case_collisions,
            "physical_tree_collisions": root_manifest["case_collisions"],
        },
        "effective_pak_entries": effective_entries,
        "format": "ZaeREo asset audit",
        "input": {"label": label},
        "loose_exact_pak_overrides": loose_exact_overrides,
        "loose_install_files": loose_install,
        "loose_runtime_files": loose_runtime,
        "overrides": overrides,
        "pak_layers": layer_reports,
        "schema_version": 1,
        "summary": {
            "effective_pak_path_count": len(effective_entries),
            "effective_runtime_path_count": len(effective_entries) + len(loose_runtime),
            "loose_install_file_count": len(loose_install),
            "loose_runtime_file_count": len(loose_runtime),
            "pak_entry_count": total_pak_entries,
            "pak_entry_extension_counts": extension_counts(all_pak_paths),
            "pak_layer_count": len(archives),
            "pak_override_path_count": len(overrides),
            "physical_file_count": root_manifest["file_count"],
            "physical_total_size": root_manifest["total_size"],
            "physical_tree_sha256": root_manifest["tree_sha256"],
        },
        "warnings": warnings,
    }


def asset_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Zaero asset audit",
        "",
        "This file is generated by `tools/audit_assets.py`; do not edit it by hand.",
        "",
        "## Summary",
        "",
        "| Measure | Count |",
        "| --- | ---: |",
        f"| PAK layers | {summary['pak_layer_count']} |",
        f"| PAK directory entries | {summary['pak_entry_count']} |",
        f"| Effective PAK paths | {summary['effective_pak_path_count']} |",
        f"| PAK override paths | {summary['pak_override_path_count']} |",
        f"| Loose runtime files | {summary['loose_runtime_file_count']} |",
        f"| Loose installation files | {summary['loose_install_file_count']} |",
        f"| Effective runtime paths | {summary['effective_runtime_path_count']} |",
        "",
        "## PAK layers",
        "",
        "| Layer | Bytes | Entries | SHA-256 |",
        "| --- | ---: | ---: | --- |",
    ]
    for layer in report["pak_layers"]:
        lines.append(
            f"| {markdown_cell(layer['name'])} | {layer['size']} | "
            f"{layer['entry_count']} | `{layer['sha256']}` |"
        )
    lines.extend(["", "## Overrides", ""])
    if report["overrides"]:
        lines.extend(["| Runtime path | Layer order |", "| --- | --- |"]) 
        for override in report["overrides"]:
            containers = " → ".join(layer["container"] for layer in override["layers"])
            lines.append(
                f"| `{markdown_cell(override['path'])}` | {markdown_cell(containers)} |"
            )
    else:
        lines.append("No exact PAK path overrides were found.")
    lines.extend(["", "## Deliberately loose runtime files", ""])
    lines.extend(["| Runtime path | Bytes | SHA-256 |", "| --- | ---: | --- |"]) 
    for record in report["loose_runtime_files"]:
        lines.append(
            f"| `{markdown_cell(record['path'])}` | {record['size']} | `{record['sha256']}` |"
        )
    lines.extend(["", "## Validation", ""])
    if report["warnings"]:
        lines.extend(f"- {warning}" for warning in report["warnings"])
    else:
        lines.append("No traversal, bounds, duplicate, or case-collision warning was found.")
    return "\n".join(lines) + "\n"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets-root", required=True, help="Zaero installation root")
    parser.add_argument(
        "--pak",
        action="append",
        help="PAK layer in precedence order; relative paths resolve under --assets-root",
    )
    parser.add_argument("--label", default="zaero-install", help="portable input label")
    parser.add_argument("--json-output", help="JSON output path; stdout when omitted")
    parser.add_argument("--markdown-output", help="optional Markdown summary path")
    parser.add_argument("--max-pak-entries", type=int, default=1_000_000)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        root = checked_root(args.assets_root, "assets root")
        paks = _resolve_paks(root, args.pak)
        report = build_asset_report(
            root, paks, label=args.label, max_pak_entries=args.max_pak_entries
        )
        write_text(args.json_output, stable_json_text(report))
        if args.markdown_output:
            write_text(args.markdown_output, asset_markdown(report))
    except (AuditError, OSError) as error:
        print(f"audit_assets.py: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
