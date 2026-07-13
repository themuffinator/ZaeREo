#!/usr/bin/env python3
"""Generate a reproducible Zaero-versus-legacy source delta and baseline hashes."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Sequence

from audit_common import (
    AuditError,
    checked_root,
    extension_counts,
    markdown_cell,
    sha256_file,
    stable_json_text,
    tree_manifest,
    write_text,
)


SOURCE_SUFFIXES = frozenset({".c", ".cc", ".cpp", ".cxx"})
FUNCTION_NAME_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*$")


def _file_map(root: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    root_resolved = root.resolve()
    for candidate in root.rglob("*"):
        if candidate.is_symlink():
            raise AuditError(f"source tree contains a symbolic link: {candidate}")
        if not candidate.is_file():
            continue
        resolved = candidate.resolve()
        try:
            relative = resolved.relative_to(root_resolved).as_posix()
        except ValueError as error:
            raise AuditError(f"source file escapes its root: {candidate}") from error
        result[relative] = resolved
    return result


def _line_count(data: bytes) -> int:
    return len(data.splitlines())


def _git_numstat(old_path: Path, new_path: Path) -> tuple[int | None, int | None]:
    if shutil.which("git") is None:
        raise AuditError("Git is required for source numstat generation")
    command = [
        "git",
        "diff",
        "--no-index",
        "--no-ext-diff",
        "--no-renames",
        "--ignore-space-at-eol",
        "--numstat",
        "--",
        str(old_path),
        str(new_path),
    ]
    process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if process.returncode not in (0, 1):
        raise AuditError(
            f"Git numstat failed for {old_path.name}: {process.stderr.strip()}"
        )
    rows = [line for line in process.stdout.splitlines() if line.strip()]
    if not rows:
        return 0, 0
    if len(rows) != 1:
        raise AuditError(f"unexpected Git numstat output for {old_path.name}")
    fields = rows[0].split("\t", 2)
    if len(fields) < 2:
        raise AuditError(f"malformed Git numstat output for {old_path.name}")
    if fields[0] == "-" or fields[1] == "-":
        return None, None
    return int(fields[0]), int(fields[1])


def _git_directory_numstat(old_root: Path, new_root: Path) -> dict[str, int]:
    if shutil.which("git") is None:
        raise AuditError("Git is required for source numstat generation")
    command = [
        "git",
        "diff",
        "--no-index",
        "--no-ext-diff",
        "--find-renames=50%",
        "--ignore-space-at-eol",
        "--numstat",
        "--",
        str(old_root),
        str(new_root),
    ]
    process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if process.returncode not in (0, 1):
        raise AuditError(f"Git directory numstat failed: {process.stderr.strip()}")
    additions = 0
    deletions = 0
    binary_paths = 0
    rows = [line for line in process.stdout.splitlines() if line.strip()]
    for row in rows:
        fields = row.split("\t", 2)
        if len(fields) < 2:
            raise AuditError("malformed Git directory numstat output")
        if fields[0] == "-" or fields[1] == "-":
            binary_paths += 1
        else:
            additions += int(fields[0])
            deletions += int(fields[1])
    return {
        "additions": additions,
        "binary_path_count": binary_paths,
        "deletions": deletions,
        "record_count": len(rows),
    }


def _mask_non_code(text: str) -> str:
    """Replace comments, literals, and preprocessor lines while preserving offsets."""

    chars = list(text)
    index = 0
    length = len(chars)
    state = "code"
    line_start = True
    while index < length:
        char = chars[index]
        next_char = chars[index + 1] if index + 1 < length else ""
        if state == "code":
            if line_start:
                probe = index
                while probe < length and chars[probe] in " \t":
                    probe += 1
                if probe < length and chars[probe] == "#":
                    index = probe
                    state = "preprocessor"
                    continue
            if char == "/" and next_char == "/":
                chars[index] = chars[index + 1] = " "
                index += 2
                state = "line_comment"
                continue
            if char == "/" and next_char == "*":
                chars[index] = chars[index + 1] = " "
                index += 2
                state = "block_comment"
                continue
            if char == '"':
                chars[index] = " "
                index += 1
                state = "string"
                continue
            if char == "'":
                chars[index] = " "
                index += 1
                state = "char"
                continue
            line_start = char == "\n"
            index += 1
            continue
        if state == "line_comment":
            if char == "\n":
                state = "code"
                line_start = True
            else:
                chars[index] = " "
            index += 1
            continue
        if state == "block_comment":
            if char == "*" and next_char == "/":
                chars[index] = chars[index + 1] = " "
                index += 2
                state = "code"
            else:
                if char != "\n":
                    chars[index] = " "
                index += 1
            continue
        if state in ("string", "char"):
            quote = '"' if state == "string" else "'"
            if char == "\\" and index + 1 < length:
                chars[index] = " "
                if chars[index + 1] != "\n":
                    chars[index + 1] = " "
                index += 2
            elif char == quote:
                chars[index] = " "
                index += 1
                state = "code"
            else:
                if char != "\n":
                    chars[index] = " "
                index += 1
            continue
        if state == "preprocessor":
            if char == "\n":
                previous = index - 1
                while previous >= 0 and text[previous] in " \t\r":
                    previous -= 1
                if previous >= 0 and text[previous] == "\\":
                    chars[index] = "\n"
                else:
                    state = "code"
                    line_start = True
            else:
                chars[index] = " "
            index += 1
    return "".join(chars)


def _candidate_function_name(segment: str) -> str | None:
    stripped = segment.rstrip()
    if not stripped.endswith(")"):
        return None
    depth = 0
    opening = None
    for index in range(len(stripped) - 1, -1, -1):
        char = stripped[index]
        if char == ")":
            depth += 1
        elif char == "(":
            depth -= 1
            if depth == 0:
                opening = index
                break
    if opening is None:
        return None
    prefix = stripped[:opening]
    match = FUNCTION_NAME_RE.search(prefix)
    if not match:
        return None
    name = match.group(1)
    if name in {"if", "for", "while", "switch", "sizeof"}:
        return None
    if re.search(r"\btypedef\b", prefix):
        return None
    return name


def _normalized_source_hash(text: str) -> str:
    normalized = "\n".join(line.rstrip(" \t\r") for line in text.splitlines())
    return hashlib.sha256(normalized.encode("utf-8", errors="surrogatepass")).hexdigest()


@dataclass(frozen=True)
class FunctionRecord:
    name: str
    start_line: int
    end_line: int
    sha256: str


def extract_c_functions(path: Path) -> dict[str, FunctionRecord]:
    text = path.read_text(encoding="latin-1")
    masked = _mask_non_code(text)
    depth = 0
    segment_start = 0
    active_name: str | None = None
    active_start = 0
    records: dict[str, FunctionRecord] = {}
    for index, char in enumerate(masked):
        if char == "{" and depth == 0:
            name = _candidate_function_name(masked[segment_start:index])
            if name is not None:
                active_name = name
                signature = masked[segment_start:index]
                leading = len(signature) - len(signature.lstrip())
                active_start = segment_start + leading
            depth = 1
        elif char == "{" and depth > 0:
            depth += 1
        elif char == "}" and depth > 0:
            depth -= 1
            if depth == 0:
                if active_name is not None:
                    source = text[active_start : index + 1]
                    key = active_name
                    suffix = 2
                    while key in records:
                        key = f"{active_name}#{suffix}"
                        suffix += 1
                    records[key] = FunctionRecord(
                        name=active_name,
                        start_line=text.count("\n", 0, active_start) + 1,
                        end_line=text.count("\n", 0, index) + 1,
                        sha256=_normalized_source_hash(source),
                    )
                active_name = None
                segment_start = index + 1
        elif char == ";" and depth == 0:
            segment_start = index + 1
    return records


def _function_delta(old_path: Path, new_path: Path) -> dict[str, Any]:
    old_functions = extract_c_functions(old_path)
    new_functions = extract_c_functions(new_path)
    added: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    changed: list[dict[str, Any]] = []
    unchanged_count = 0
    for key in sorted(set(old_functions) | set(new_functions)):
        old = old_functions.get(key)
        new = new_functions.get(key)
        if old is None and new is not None:
            added.append(
                {"name": new.name, "zaero_lines": [new.start_line, new.end_line]}
            )
        elif new is None and old is not None:
            removed.append(
                {"legacy_lines": [old.start_line, old.end_line], "name": old.name}
            )
        elif old is not None and new is not None and old.sha256 != new.sha256:
            changed.append(
                {
                    "legacy_lines": [old.start_line, old.end_line],
                    "name": new.name,
                    "zaero_lines": [new.start_line, new.end_line],
                }
            )
        else:
            unchanged_count += 1
    return {
        "added": added,
        "added_count": len(added),
        "changed": changed,
        "changed_count": len(changed),
        "removed": removed,
        "removed_count": len(removed),
        "unchanged_count": unchanged_count,
    }


def build_source_delta(
    zaero_root: Path,
    legacy_root: Path,
    rerelease_root: Path,
    *,
    zaero_label: str = "zaero-source",
    legacy_label: str = "legacy-quake2-game",
    rerelease_label: str = "quake2-rerelease-api-2023",
) -> dict[str, Any]:
    zaero_files = _file_map(zaero_root)
    legacy_files = _file_map(legacy_root)
    rerelease_manifest = tree_manifest(rerelease_root)
    directory_numstat = _git_directory_numstat(legacy_root, zaero_root)
    paths = sorted(set(zaero_files) | set(legacy_files), key=lambda value: value.encode("utf-8"))
    file_records: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    total_additions = 0
    total_deletions = 0
    binary_path_count = 0
    function_totals: Counter[str] = Counter()
    for relative in paths:
        old_path = legacy_files.get(relative)
        new_path = zaero_files.get(relative)
        old_hash = sha256_file(old_path) if old_path else None
        new_hash = sha256_file(new_path) if new_path else None
        function_delta = None
        if old_path is None and new_path is not None:
            data = new_path.read_bytes()
            additions: int | None = _line_count(data) if b"\0" not in data else None
            deletions: int | None = 0 if additions is not None else None
            status = "zaero_only"
        elif new_path is None and old_path is not None:
            data = old_path.read_bytes()
            deletions = _line_count(data) if b"\0" not in data else None
            additions = 0 if deletions is not None else None
            status = "legacy_only"
        elif old_path is not None and new_path is not None:
            additions, deletions = _git_numstat(old_path, new_path)
            if old_hash == new_hash:
                status = "identical"
            elif additions == 0 and deletions == 0:
                status = "ignored_eol_whitespace_only"
            else:
                status = "modified"
            if Path(relative).suffix.casefold() in SOURCE_SUFFIXES:
                function_delta = _function_delta(old_path, new_path)
                function_totals.update(
                    {
                        "added": function_delta["added_count"],
                        "changed": function_delta["changed_count"],
                        "removed": function_delta["removed_count"],
                        "unchanged": function_delta["unchanged_count"],
                    }
                )
        else:
            raise AssertionError("unreachable empty union record")
        if additions is None or deletions is None:
            binary_path_count += 1
        else:
            total_additions += additions
            total_deletions += deletions
        status_counts[status] += 1
        record: dict[str, Any] = {
            "additions": additions,
            "deletions": deletions,
            "legacy_sha256": old_hash,
            "path": relative,
            "status": status,
            "zaero_sha256": new_hash,
        }
        if function_delta is not None:
            record["functions"] = function_delta
        file_records.append(record)

    zaero_manifest = tree_manifest(zaero_root)
    legacy_manifest = tree_manifest(legacy_root)
    if binary_path_count == 0 and directory_numstat["binary_path_count"] == 0:
        if (
            total_additions != directory_numstat["additions"]
            or total_deletions != directory_numstat["deletions"]
        ):
            raise AuditError(
                "logical per-path and rename-aware directory numstat totals disagree"
            )
    return {
        "comparison": {
            "directory_numstat": directory_numstat,
            "file_records": file_records,
            "directory_method": "git diff --no-index --find-renames=50% --ignore-space-at-eol --numstat",
            "file_record_method": "logical path union; common paths use git diff --no-index --no-renames --ignore-space-at-eol --numstat",
        },
        "format": "ZaeREo source delta audit",
        "inputs": {
            "legacy_label": legacy_label,
            "rerelease_label": rerelease_label,
            "zaero_label": zaero_label,
        },
        "schema_version": 1,
        "summary": {
            "additions": total_additions,
            "binary_path_count": binary_path_count,
            "compared_path_count": directory_numstat["record_count"],
            "deletions": total_deletions,
            "function_delta": dict(sorted(function_totals.items())),
            "legacy_extension_counts": extension_counts(legacy_files),
            "legacy_file_count": len(legacy_files),
            "legacy_tree_sha256": legacy_manifest["tree_sha256"],
            "logical_path_count": len(paths),
            "rerelease_extension_counts": extension_counts(
                record["path"] for record in rerelease_manifest["files"]
            ),
            "rerelease_file_count": rerelease_manifest["file_count"],
            "rerelease_tree_sha256": rerelease_manifest["tree_sha256"],
            "status_counts": dict(sorted(status_counts.items())),
            "zaero_extension_counts": extension_counts(zaero_files),
            "zaero_file_count": len(zaero_files),
            "zaero_tree_sha256": zaero_manifest["tree_sha256"],
        },
    }


def build_baselines(
    zaero_root: Path,
    legacy_root: Path,
    rerelease_root: Path,
    assets_root: Path,
) -> dict[str, Any]:
    definitions = [
        ("legacy_quake2_game", "Legacy Quake II game source", legacy_root),
        ("quake2_rerelease", "Quake II Rerelease API 2023 source", rerelease_root),
        ("zaero_install", "Zaero 1.1 installation", assets_root),
        ("zaero_source", "Zaero game source", zaero_root),
    ]
    baselines: dict[str, Any] = {}
    for key, description, root in definitions:
        baselines[key] = {
            "description": description,
            "origin": "supplied local tree; upstream commit or archive origin is not recorded",
            **tree_manifest(root),
        }
    return {
        "baselines": baselines,
        "format": "ZaeREo baseline provenance manifest",
        "hash_algorithm": "SHA-256",
        "schema_version": 1,
    }


def source_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    functions = summary["function_delta"]
    lines = [
        "# Zaero source delta audit",
        "",
        "This file is generated by `tools/audit_source_delta.py`; do not edit it by hand.",
        "",
        "The line totals deliberately ignore whitespace at end of line and use Git's "
        "no-index numstat algorithm. Function classification is lexical evidence and must "
        "still be reviewed for source-age drift.",
        "",
        "## Summary",
        "",
        "| Measure | Count |",
        "| --- | ---: |",
        f"| Legacy files | {summary['legacy_file_count']} |",
        f"| Zaero files | {summary['zaero_file_count']} |",
        f"| Compared paths | {summary['compared_path_count']} |",
        f"| Logical union paths | {summary['logical_path_count']} |",
        f"| Inserted lines | {summary['additions']} |",
        f"| Deleted lines | {summary['deletions']} |",
        f"| Added functions | {functions.get('added', 0)} |",
        f"| Changed functions | {functions.get('changed', 0)} |",
        f"| Removed functions | {functions.get('removed', 0)} |",
        "",
        "## Per-file logical delta",
        "",
        "| Path | Status | + | − | Added functions | Changed functions | Removed functions |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for record in report["comparison"]["file_records"]:
        function_delta = record.get("functions", {})
        additions = "binary" if record["additions"] is None else record["additions"]
        deletions = "binary" if record["deletions"] is None else record["deletions"]
        lines.append(
            f"| `{markdown_cell(record['path'])}` | {record['status']} | {additions} | "
            f"{deletions} | {function_delta.get('added_count', 0)} | "
            f"{function_delta.get('changed_count', 0)} | "
            f"{function_delta.get('removed_count', 0)} |"
        )
    lines.extend(["", "## Function-level changes", ""])
    for record in report["comparison"]["file_records"]:
        functions_for_file = record.get("functions")
        if not functions_for_file or not any(
            functions_for_file[f"{kind}_count"] for kind in ("added", "changed", "removed")
        ):
            continue
        lines.extend([f"### `{record['path']}`", ""])
        for heading, key in (("Added", "added"), ("Changed", "changed"), ("Removed", "removed")):
            entries = functions_for_file[key]
            if entries:
                names = ", ".join(f"`{entry['name']}`" for entry in entries)
                lines.append(f"- {heading}: {names}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zaero-root", required=True, help="Zaero source root")
    parser.add_argument("--legacy-root", required=True, help="legacy Quake II game source root")
    parser.add_argument("--rerelease-root", required=True, help="Rerelease source root")
    parser.add_argument("--assets-root", required=True, help="Zaero installation root")
    parser.add_argument("--zaero-label", default="zaero-source")
    parser.add_argument("--legacy-label", default="legacy-quake2-game")
    parser.add_argument("--rerelease-label", default="quake2-rerelease-api-2023")
    parser.add_argument("--json-output", help="JSON output path; stdout when omitted")
    parser.add_argument("--markdown-output", help="optional Markdown report path")
    parser.add_argument("--baselines-output", help="optional baseline provenance JSON path")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        zaero_root = checked_root(args.zaero_root, "Zaero source root")
        legacy_root = checked_root(args.legacy_root, "legacy source root")
        rerelease_root = checked_root(args.rerelease_root, "Rerelease source root")
        assets_root = checked_root(args.assets_root, "assets root")
        report = build_source_delta(
            zaero_root,
            legacy_root,
            rerelease_root,
            zaero_label=args.zaero_label,
            legacy_label=args.legacy_label,
            rerelease_label=args.rerelease_label,
        )
        write_text(args.json_output, stable_json_text(report))
        if args.markdown_output:
            write_text(args.markdown_output, source_markdown(report))
        if args.baselines_output:
            write_text(
                args.baselines_output,
                stable_json_text(
                    build_baselines(zaero_root, legacy_root, rerelease_root, assets_root)
                ),
            )
    except (AuditError, OSError) as error:
        print(f"audit_source_delta.py: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
