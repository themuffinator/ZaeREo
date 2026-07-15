#!/usr/bin/env python3
"""Audit D-015 source-only surfaces and validate Release artifacts."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any, Iterable
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_common import (  # noqa: E402
    AuditError,
    PAK_ENTRY,
    PAK_HEADER,
    checked_file,
    checked_range,
    checked_root,
    normalize_runtime_path,
    sha256_file,
    stable_json_text,
    write_text,
)


POLICY_SCHEMA = "zaereo.release-surface-policy/v1"
SOURCE_SUFFIXES = frozenset(
    {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".inc", ".inl"}
)
MAX_BINARY_BYTES = 512 * 1024 * 1024
MAX_ARCHIVE_MEMBER_BYTES = 512 * 1024 * 1024
MAX_ARCHIVE_TOTAL_BYTES = 4 * 1024 * 1024 * 1024
MSBUILD_NAMESPACE = {"m": "http://schemas.microsoft.com/developer/msbuild/2003"}


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AuditError(f"policy contains duplicate key {key!r}")
        result[key] = value
    return result


def load_policy(path: Path) -> tuple[Path, dict[str, Any]]:
    policy_path = checked_file(path, "Release-surface policy")
    try:
        policy = json.loads(
            policy_path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except json.JSONDecodeError as error:
        raise AuditError(f"Release-surface policy is invalid JSON: {error}") from error
    if not isinstance(policy, dict) or policy.get("schema") != POLICY_SCHEMA:
        raise AuditError(f"Release-surface policy must use schema {POLICY_SCHEMA}")
    if policy.get("decision") != "D-015":
        raise AuditError("Release-surface policy must be governed by D-015")
    if not isinstance(policy.get("revision"), int) or policy["revision"] < 1:
        raise AuditError("Release-surface policy revision must be a positive integer")
    for key in ("legacy", "port", "release_binary", "release_archive"):
        if not isinstance(policy.get(key), dict):
            raise AuditError(f"Release-surface policy {key!r} must be an object")
    return policy_path, policy


def _relative_path(raw: Any, label: str) -> str:
    if not isinstance(raw, str) or not raw or "\\" in raw:
        raise AuditError(f"{label} must be a non-empty POSIX relative path")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise AuditError(f"{label} is not a safe relative path: {raw!r}")
    return path.as_posix()


def _string_list(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise AuditError(f"{label} must be a {'possibly empty ' if allow_empty else ''}list")
    if any(not isinstance(item, str) or not item for item in value):
        raise AuditError(f"{label} must contain non-empty strings")
    if len(value) != len(set(value)):
        raise AuditError(f"{label} contains duplicates")
    return list(value)


def _read_latin1(path: Path) -> str:
    return path.read_text(encoding="latin-1")


def _line_numbers(text: str, token: str) -> list[int]:
    lines: list[int] = []
    start = 0
    while True:
        index = text.find(token, start)
        if index < 0:
            return lines
        lines.append(text.count("\n", 0, index) + 1)
        start = index + len(token)


def _source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    root_resolved = root.resolve()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise AuditError(f"port source contains a symbolic link: {path}")
        if not path.is_file() or path.suffix.casefold() not in SOURCE_SUFFIXES:
            continue
        resolved = path.resolve()
        try:
            resolved.relative_to(root_resolved)
        except ValueError as error:
            raise AuditError(f"port source escapes its root: {path}") from error
        files.append(resolved)
    return sorted(files, key=lambda item: item.relative_to(root).as_posix().encode("utf-8"))


def _legacy_project_configuration(text: str, configuration: str) -> list[str]:
    if configuration == "Release":
        pattern = re.compile(
            r'!IF\s+"\$\(CFG\)"\s*==\s*"zaero - Win32 Release"(.*?)!ELSEIF',
            re.DOTALL | re.IGNORECASE,
        )
    elif configuration == "Debug":
        pattern = re.compile(
            r'!ELSEIF\s+"\$\(CFG\)"\s*==\s*"zaero - Win32 Debug"(.*?)!ENDIF',
            re.DOTALL | re.IGNORECASE,
        )
    else:
        raise AuditError(f"unsupported legacy configuration {configuration!r}")
    match = pattern.search(text)
    if match is None:
        raise AuditError(f"legacy project lacks the {configuration} configuration")
    effective = re.findall(r"^# ADD CPP\s+(.+)$", match.group(1), re.MULTILINE)
    if len(effective) != 1:
        raise AuditError(
            f"legacy {configuration} configuration has {len(effective)} effective CPP lines"
        )
    return re.findall(r'/D\s+"([^"]+)"', effective[0])


def _legacy_project_modules(text: str) -> set[str]:
    return {
        match.group(1).replace("\\", "/")
        for match in re.finditer(r"^SOURCE=\.\\(.+)$", text, re.MULTILINE)
    }


def _msbuild_definitions(project_path: Path) -> dict[str, list[str]]:
    try:
        root = ET.parse(project_path).getroot()
    except ET.ParseError as error:
        raise AuditError(f"port project is invalid XML: {error}") from error
    result: dict[str, list[str]] = {}
    condition_re = re.compile(
        r"^'\$\(Configuration\)\|\$\(Platform\)'\s*==\s*'([^']+)'$"
    )
    for group in root.findall("m:ItemDefinitionGroup", MSBUILD_NAMESPACE):
        match = condition_re.match(group.attrib.get("Condition", ""))
        if match is None:
            continue
        definitions = group.find("m:ClCompile/m:PreprocessorDefinitions", MSBUILD_NAMESPACE)
        if definitions is None or definitions.text is None:
            raise AuditError(f"port project {match.group(1)} lacks PreprocessorDefinitions")
        values = [
            value.strip()
            for value in definitions.text.split(";")
            if value.strip() and not value.strip().startswith("%(")
        ]
        if len(values) != len(set(values)):
            raise AuditError(f"port project {match.group(1)} repeats a definition")
        result[match.group(1)] = values
    return result


def _validate_project_definitions(
    actual: dict[str, list[str]], expected: Any
) -> dict[str, dict[str, list[str]]]:
    if not isinstance(expected, dict) or not expected:
        raise AuditError("port project configurations must be a non-empty object")
    report: dict[str, dict[str, list[str]]] = {}
    for configuration, contract in expected.items():
        if not isinstance(contract, dict):
            raise AuditError(f"port project contract {configuration!r} must be an object")
        if configuration not in actual:
            raise AuditError(f"port project lacks configuration {configuration!r}")
        required = _string_list(
            contract.get("required_defines"),
            f"{configuration} required_defines",
            allow_empty=True,
        )
        forbidden = _string_list(
            contract.get("forbidden_defines"),
            f"{configuration} forbidden_defines",
            allow_empty=True,
        )
        overlap = set(required) & set(forbidden)
        if overlap:
            raise AuditError(
                f"{configuration} defines are both required and forbidden: {sorted(overlap)}"
            )
        missing = sorted(set(required) - set(actual[configuration]))
        present = sorted(set(forbidden) & set(actual[configuration]))
        if missing:
            raise AuditError(f"port project {configuration} misses defines {missing}")
        if present:
            raise AuditError(f"port project {configuration} enables forbidden defines {present}")
        report[configuration] = {
            "definitions": actual[configuration],
            "forbidden_definitions_present": present,
            "required_definitions": required,
        }
    return report


def _exact_identifier_count(text: str, token: str) -> int:
    return len(
        re.findall(
            rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])",
            text,
        )
    )


def audit_port(policy: dict[str, Any], port_root: Path) -> dict[str, Any]:
    """Validate only the current source/project half of the D-015 policy."""

    port_root = checked_root(port_root, "ZaeREo source root")
    port_contract = policy["port"]
    port_project_contract = port_contract.get("project")
    if not isinstance(port_project_contract, dict):
        raise AuditError("port project contract must be an object")
    port_project_relative = _relative_path(
        port_project_contract.get("path"), "port project path"
    )
    port_project = checked_file(port_root / port_project_relative, "port project")
    port_configurations = _validate_project_definitions(
        _msbuild_definitions(port_project),
        port_project_contract.get("configurations"),
    )

    source_files = _source_files(port_root)
    forbidden_basenames = _string_list(
        port_contract.get("forbidden_source_basenames"),
        "port forbidden_source_basenames",
    )
    forbidden_basename_set = {value.casefold() for value in forbidden_basenames}
    if len(forbidden_basename_set) != len(forbidden_basenames):
        raise AuditError("port forbidden_source_basenames has case-insensitive duplicates")
    bad_paths = [
        path.relative_to(port_root).as_posix()
        for path in source_files
        if path.name.casefold() in forbidden_basename_set
    ]
    if bad_paths:
        raise AuditError(f"port contains forbidden legacy debug modules: {bad_paths}")

    texts = {
        path.relative_to(port_root).as_posix(): path.read_text(
            encoding="utf-8", errors="strict"
        )
        for path in source_files
    }
    forbidden_tokens = _string_list(
        port_contract.get("forbidden_source_tokens"), "port forbidden_source_tokens"
    )
    token_hits: list[dict[str, Any]] = []
    for token in forbidden_tokens:
        for relative, text in texts.items():
            lines = _line_numbers(text, token)
            if lines:
                token_hits.append({"lines": lines, "path": relative, "token": token})
    if token_hits:
        first = token_hits[0]
        raise AuditError(
            f"port contains forbidden legacy surface {first['token']!r} in "
            f"{first['path']}:{first['lines'][0]}"
        )

    scoped_contracts = port_contract.get("scoped_forbidden_source_tokens")
    if not isinstance(scoped_contracts, list) or not scoped_contracts:
        raise AuditError("port scoped_forbidden_source_tokens must be a non-empty list")
    scoped_report: list[dict[str, Any]] = []
    native_unscoped_counts: dict[str, int] = {}
    for index, contract in enumerate(scoped_contracts):
        if not isinstance(contract, dict):
            raise AuditError(f"scoped source contract {index} must be an object")
        relative = _relative_path(contract.get("path"), f"scoped source {index} path")
        tokens = _string_list(contract.get("tokens"), f"scoped source {relative} tokens")
        if relative not in texts:
            raise AuditError(f"scoped port source is missing: {relative}")
        hits = {
            token: _line_numbers(texts[relative], token)
            for token in tokens
            if _line_numbers(texts[relative], token)
        }
        if hits:
            token = sorted(hits)[0]
            raise AuditError(
                f"scoped port source {relative} contains disabled legacy surface "
                f"{token!r} at line {hits[token][0]}"
            )
        for token in tokens:
            native_unscoped_counts[token] = sum(
                _exact_identifier_count(text, token)
                for path, text in texts.items()
                if path != relative
            )
        scoped_report.append(
            {"forbidden_tokens_present": [], "path": relative, "tokens": tokens}
        )

    return {
        "forbidden_source_basenames_present": bad_paths,
        "forbidden_source_token_hits": token_hits,
        "native_unscoped_exact_identifier_counts": dict(
            sorted(native_unscoped_counts.items())
        ),
        "project": {
            "configurations": port_configurations,
            "path": port_project_relative,
            "sha256": sha256_file(port_project),
        },
        "scoped_forbidden_source_tokens": scoped_report,
        "source_file_count": len(source_files),
    }


def build_report(policy_path: Path, zaero_root: Path, port_root: Path) -> dict[str, Any]:
    policy_file, policy = load_policy(policy_path)
    zaero_root = checked_root(zaero_root, "Zaero source root")
    port_root = checked_root(port_root, "ZaeREo source root")

    legacy = policy["legacy"]
    identities = legacy.get("identity_locked_files")
    if not isinstance(identities, list) or not identities:
        raise AuditError("legacy identity_locked_files must be a non-empty list")
    legacy_files: dict[str, Path] = {}
    identity_report: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for index, record in enumerate(identities):
        if not isinstance(record, dict):
            raise AuditError(f"legacy identity record {index} must be an object")
        relative = _relative_path(record.get("path"), f"legacy identity {index} path")
        expected_hash = record.get("sha256")
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise AuditError(f"legacy identity {relative} has an invalid SHA-256")
        if relative in seen_paths:
            raise AuditError(f"legacy identity path is repeated: {relative}")
        seen_paths.add(relative)
        path = checked_file(zaero_root / PurePosixPath(relative), f"legacy source {relative}")
        actual_hash = sha256_file(path)
        if actual_hash != expected_hash:
            raise AuditError(
                f"legacy source identity changed for {relative}: expected {expected_hash}, "
                f"found {actual_hash}"
            )
        legacy_files[relative] = path
        identity_report.append(
            {"path": relative, "sha256": actual_hash, "size": path.stat().st_size}
        )
    identity_report.sort(key=lambda item: item["path"].encode("utf-8"))

    project_contract = legacy.get("project")
    if not isinstance(project_contract, dict):
        raise AuditError("legacy project contract must be an object")
    project_relative = _relative_path(project_contract.get("path"), "legacy project path")
    if project_relative not in legacy_files:
        raise AuditError("legacy project must be identity-locked")
    project_text = _read_latin1(legacy_files[project_relative])
    config_contracts = project_contract.get("configurations")
    if not isinstance(config_contracts, dict) or set(config_contracts) != {"Debug", "Release"}:
        raise AuditError("legacy project must define exact Debug and Release contracts")
    legacy_configurations: dict[str, dict[str, list[str]]] = {}
    for name in ("Debug", "Release"):
        contract = config_contracts[name]
        if not isinstance(contract, dict):
            raise AuditError(f"legacy {name} contract must be an object")
        expected_defines = _string_list(
            contract.get("defines_exact"), f"legacy {name} defines_exact"
        )
        actual_defines = _legacy_project_configuration(project_text, name)
        if actual_defines != expected_defines:
            raise AuditError(
                f"legacy {name} defines changed: expected {expected_defines}, "
                f"found {actual_defines}"
            )
        legacy_configurations[name] = {"definitions": actual_defines}
    never_defined = _string_list(
        project_contract.get("never_defined"), "legacy project never_defined"
    )
    defined = {
        value
        for configuration in legacy_configurations.values()
        for value in configuration["definitions"]
    }
    unexpected = sorted(set(never_defined) & defined)
    if unexpected:
        raise AuditError(f"legacy project unexpectedly defines {unexpected}")
    included_modules = _string_list(
        project_contract.get("included_debug_modules"),
        "legacy included_debug_modules",
    )
    actual_modules = _legacy_project_modules(project_text)
    missing_modules = sorted(set(included_modules) - actual_modules)
    if missing_modules:
        raise AuditError(f"legacy project no longer includes modules {missing_modules}")

    probes = legacy.get("source_probes")
    if not isinstance(probes, list) or not probes:
        raise AuditError("legacy source_probes must be a non-empty list")
    probe_report: list[dict[str, Any]] = []
    surface_counts: Counter[str] = Counter()
    seen_probes: set[tuple[str, str]] = set()
    for index, probe in enumerate(probes):
        if not isinstance(probe, dict):
            raise AuditError(f"legacy source probe {index} must be an object")
        relative = _relative_path(probe.get("path"), f"legacy probe {index} path")
        token = probe.get("token")
        surface = probe.get("surface")
        expected_count = probe.get("count")
        if relative not in legacy_files:
            raise AuditError(f"legacy probe path is not identity-locked: {relative}")
        if not isinstance(token, str) or not token:
            raise AuditError(f"legacy probe {index} token must be non-empty")
        if not isinstance(surface, str) or not surface:
            raise AuditError(f"legacy probe {index} surface must be non-empty")
        if not isinstance(expected_count, int) or expected_count < 1:
            raise AuditError(f"legacy probe {index} count must be positive")
        key = (relative, token)
        if key in seen_probes:
            raise AuditError(f"legacy source probe is repeated: {relative}:{token}")
        seen_probes.add(key)
        lines = _line_numbers(_read_latin1(legacy_files[relative]), token)
        if len(lines) != expected_count:
            raise AuditError(
                f"legacy probe changed for {relative}:{token!r}: expected "
                f"{expected_count}, found {len(lines)}"
            )
        surface_counts[surface] += 1
        probe_report.append(
            {
                "count": len(lines),
                "lines": lines,
                "path": relative,
                "surface": surface,
                "token": token,
            }
        )
    probe_report.sort(key=lambda item: (item["path"], item["lines"], item["token"]))

    port_report = audit_port(policy, port_root)

    binary_strings = _string_list(
        policy["release_binary"].get("forbidden_ascii_strings"),
        "release_binary forbidden_ascii_strings",
    )
    archive_basenames = _string_list(
        policy["release_archive"].get("forbidden_member_basenames"),
        "release_archive forbidden_member_basenames",
    )
    binary_suffixes = _string_list(
        policy["release_archive"].get("binary_member_suffixes"),
        "release_archive binary_member_suffixes",
    )
    pak_suffixes = _string_list(
        policy["release_archive"].get("pak_member_suffixes"),
        "release_archive pak_member_suffixes",
    )
    all_suffixes = binary_suffixes + pak_suffixes
    if any(not value.startswith(".") or value != value.casefold() for value in all_suffixes):
        raise AuditError("release archive scan suffixes must be lowercase extensions")
    if set(binary_suffixes) & set(pak_suffixes):
        raise AuditError("release archive binary and PAK suffixes overlap")

    return {
        "audit": "zaero-release-surfaces",
        "disposition": {
            "classification": "ADAPT",
            "decision": "D-015",
            "live_release_smoke_remaining": True,
            "result": (
                "Legacy debug/test tools and compiled-out experiments remain source "
                "evidence only and are absent from the current production surface."
            ),
        },
        "legacy": {
            "identity_locked_files": identity_report,
            "project": {
                "configurations": legacy_configurations,
                "included_debug_modules": included_modules,
                "never_defined": never_defined,
            },
            "source_probes": probe_report,
            "surfaces_by_probe_count": dict(sorted(surface_counts.items())),
        },
        "policy": {
            "decision": policy["decision"],
            "path": policy_file.name,
            "policy_id": policy["policy_id"],
            "revision": policy["revision"],
            "sha256": sha256_file(policy_file),
        },
        "port": port_report,
        "release_contract": {
            "archive_binary_member_suffixes": binary_suffixes,
            "archive_forbidden_member_basenames": archive_basenames,
            "archive_pak_member_suffixes": pak_suffixes,
            "binary_forbidden_ascii_strings": binary_strings,
            "binary_validation_is_local": True,
        },
        "schema_version": 1,
        "summary": {
            "animated_rocket_guard_count": next(
                item["count"]
                for item in probe_report
                if item["path"] == "g_weapon.c" and item["token"] == "#ifdef _SHANETEST"
            ),
            "disabled_grapple_block_count": next(
                item["count"]
                for item in probe_report
                if item["path"] == "z_boss.c"
                and item["token"] == "#if 0 //def USE_GRAPPLE_CABLE"
            ),
            "legacy_debug_command_count": surface_counts["debug-command"],
            "legacy_debug_module_count": len(included_modules),
            "legacy_identity_file_count": len(identity_report),
            "legacy_probe_count": len(probe_report),
            "port_forbidden_source_hit_count": 0,
        },
    }


def _forbidden_binary_hits(data: bytes, strings: Iterable[str]) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for value in strings:
        ascii_value = value.encode("ascii")
        utf16_value = value.encode("utf-16-le")
        encodings = []
        if ascii_value in data:
            encodings.append("ascii")
        if utf16_value in data:
            encodings.append("utf-16-le")
        if encodings:
            hits.append({"encodings": ",".join(encodings), "string": value})
    return hits


def validate_binary(policy: dict[str, Any], binary_path: Path) -> dict[str, Any]:
    path = checked_file(binary_path, "Release binary")
    size = path.stat().st_size
    if size > MAX_BINARY_BYTES:
        raise AuditError(f"Release binary exceeds {MAX_BINARY_BYTES} bytes: {path}")
    strings = _string_list(
        policy["release_binary"].get("forbidden_ascii_strings"),
        "release_binary forbidden_ascii_strings",
    )
    data = path.read_bytes()
    hits = _forbidden_binary_hits(data, strings)
    if hits:
        raise AuditError(f"Release binary contains forbidden D-015 strings: {hits}")
    return {
        "forbidden_string_count": len(strings),
        "forbidden_string_hits": hits,
        "path": path.name,
        "sha256": sha256_file(path),
        "size": size,
    }


def _archive_member_path(raw: str) -> PurePosixPath:
    if "\\" in raw or raw.startswith("/") or raw.endswith("/"):
        raise AuditError(f"Release archive has an unsafe member path: {raw!r}")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise AuditError(f"Release archive has an unsafe member path: {raw!r}")
    return path


def _validate_pak_bytes(
    data: bytes, label: str, forbidden_basenames: set[str]
) -> int:
    if len(data) < PAK_HEADER.size:
        raise AuditError(f"Release archive PAK is shorter than its header: {label}")
    magic, directory_offset, directory_length = PAK_HEADER.unpack_from(data, 0)
    if magic != b"PACK":
        raise AuditError(f"Release archive PAK has invalid magic: {label}")
    checked_range(directory_offset, directory_length, len(data), f"{label} directory")
    if directory_length % PAK_ENTRY.size:
        raise AuditError(f"Release archive PAK has malformed directory length: {label}")
    entry_count = directory_length // PAK_ENTRY.size
    if entry_count > 1_000_000:
        raise AuditError(f"Release archive PAK has too many entries: {label}")
    seen: set[str] = set()
    for index in range(entry_count):
        raw_name, offset, size = PAK_ENTRY.unpack_from(
            data, directory_offset + index * PAK_ENTRY.size
        )
        name_bytes, separator, padding = raw_name.partition(b"\0")
        if not name_bytes:
            raise AuditError(f"Release archive PAK has an empty entry name: {label}")
        if separator and any(padding):
            raise AuditError(
                f"Release archive PAK has non-NUL name padding: {label}:{index}"
            )
        try:
            runtime_path = normalize_runtime_path(
                name_bytes.decode("ascii"), f"{label} entry {index}"
            )
        except UnicodeDecodeError as error:
            raise AuditError(
                f"Release archive PAK has a non-ASCII entry name: {label}:{index}"
            ) from error
        folded = runtime_path.casefold()
        if folded in seen:
            raise AuditError(
                f"Release archive PAK has duplicate/case-colliding path {runtime_path!r}"
            )
        seen.add(folded)
        checked_range(offset, size, len(data), f"{label}:{runtime_path}")
        if PurePosixPath(runtime_path).name.casefold() in forbidden_basenames:
            raise AuditError(
                f"Release archive PAK contains forbidden D-015 member "
                f"{label}:{runtime_path}"
            )
    return entry_count


def validate_archive(policy: dict[str, Any], archive_path: Path) -> dict[str, Any]:
    path = checked_file(archive_path, "Release archive")
    contract = policy["release_archive"]
    forbidden_basenames = {
        value.casefold()
        for value in _string_list(
            contract.get("forbidden_member_basenames"),
            "release_archive forbidden_member_basenames",
        )
    }
    binary_suffixes = set(
        _string_list(
            contract.get("binary_member_suffixes"),
            "release_archive binary_member_suffixes",
        )
    )
    pak_suffixes = set(
        _string_list(
            contract.get("pak_member_suffixes"),
            "release_archive pak_member_suffixes",
        )
    )
    binary_strings = _string_list(
        policy["release_binary"].get("forbidden_ascii_strings"),
        "release_binary forbidden_ascii_strings",
    )
    seen_casefolded: set[str] = set()
    scanned_binaries: list[str] = []
    scanned_paks: list[dict[str, Any]] = []
    total_size = 0
    member_count = 0
    try:
        with zipfile.ZipFile(path, "r") as archive:
            for info in archive.infolist():
                if info.is_dir():
                    raise AuditError(f"Release archive contains directory entry {info.filename!r}")
                member = _archive_member_path(info.filename)
                folded = member.as_posix().casefold()
                if folded in seen_casefolded:
                    raise AuditError(
                        f"Release archive has a duplicate/case-colliding member: {info.filename}"
                    )
                seen_casefolded.add(folded)
                member_count += 1
                if info.flag_bits & 0x1:
                    raise AuditError(f"Release archive member is encrypted: {info.filename}")
                if info.file_size > MAX_ARCHIVE_MEMBER_BYTES:
                    raise AuditError(f"Release archive member is too large: {info.filename}")
                total_size += info.file_size
                if total_size > MAX_ARCHIVE_TOTAL_BYTES:
                    raise AuditError("Release archive expanded size exceeds the audit limit")
                if member.name.casefold() in forbidden_basenames:
                    raise AuditError(
                        f"Release archive contains forbidden D-015 member {info.filename!r}"
                    )
                if member.suffix.casefold() in binary_suffixes:
                    data = archive.read(info)
                    hits = _forbidden_binary_hits(data, binary_strings)
                    if hits:
                        raise AuditError(
                            f"Release archive binary {info.filename!r} contains forbidden "
                            f"D-015 strings: {hits}"
                        )
                    scanned_binaries.append(member.as_posix())
                if member.suffix.casefold() in pak_suffixes:
                    data = archive.read(info)
                    scanned_paks.append(
                        {
                            "entry_count": _validate_pak_bytes(
                                data, member.as_posix(), forbidden_basenames
                            ),
                            "path": member.as_posix(),
                        }
                    )
    except zipfile.BadZipFile as error:
        raise AuditError(f"Release archive is not a valid ZIP: {path}") from error
    return {
        "binary_members_scanned": sorted(scanned_binaries),
        "member_count": member_count,
        "path": path.name,
        "pak_members_scanned": sorted(scanned_paks, key=lambda item: item["path"]),
        "sha256": sha256_file(path),
        "total_uncompressed_size": total_size,
    }


def markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    legacy = report["legacy"]
    port = report["port"]
    contract = report["release_contract"]
    lines = [
        "# D-015 Release-surface audit",
        "",
        "This normalized source audit distinguishes legacy developer experiments from",
        "shipped gameplay. It remains static evidence and does not embed a runtime report;",
        "D-015 separately records the retained live Release smoke that closes Q-039/SYS-018.",
        "",
        "## Result",
        "",
        f'- **{summary["legacy_identity_file_count"]}** supplied source/project files are identity-locked.',
        f'- The legacy project includes **{summary["legacy_debug_module_count"]}** debug/test modules and exposes **{summary["legacy_debug_command_count"]}** guarded commands only in its Debug configuration.',
        f'- `_SHANETEST` guards the animated-rocket path at **{summary["animated_rocket_guard_count"]}** sites but is absent from both supplied build configurations.',
        f'- The ZBoss grapple renderer has **{summary["disabled_grapple_block_count"]}** literal `#if 0` blocks; the selected source path uses `TE_MEDIC_CABLE_ATTACK`.',
        "- The current port source and project contain zero forbidden legacy surfaces.",
        "- Release DLL and ZIP validation is intentionally local so generated artifact",
        "  hashes do not enter the checked-in normalized report.",
        "",
        "## Supplied project definitions",
        "",
        "| Configuration | Definitions |",
        "| --- | --- |",
    ]
    for name, item in legacy["project"]["configurations"].items():
        lines.append(f'| {name} | {", ".join(f"`{value}`" for value in item["definitions"])} |')
    lines.extend(
        [
            "",
            "## Current project definitions",
            "",
            "| Configuration | Definitions | Forbidden present |",
            "| --- | --- | --- |",
        ]
    )
    for name, item in port["project"]["configurations"].items():
        definitions = ", ".join(f"`{value}`" for value in item["definitions"])
        present = ", ".join(item["forbidden_definitions_present"]) or "none"
        lines.append(f"| {name} | {definitions} | {present} |")
    lines.extend(
        [
            "",
            "## Production deny contracts",
            "",
            f'- Source tokens: **{len(report["release_contract"]["binary_forbidden_ascii_strings"])}** binary-safe signatures plus the broader source-only symbol list in the policy.',
            f'- Archive member basenames: **{len(contract["archive_forbidden_member_basenames"])}**.',
            f'- Binary member suffixes scanned inside archives: {", ".join(f"`{value}`" for value in contract["archive_binary_member_suffixes"])}.',
            f'- Runtime PAK member suffixes scanned inside archives: {", ".join(f"`{value}`" for value in contract["archive_pak_member_suffixes"])}.',
            "- `TE_GRAPPLE_CABLE` is denied only in the Zaero ZBoss implementation; native",
            "  Rerelease protocol declarations and CTF use remain allowed.",
            "",
            "## Runtime evidence boundary",
            "",
            "Produced Release DLL/package validation remains local generated evidence.",
            "D-015 separately links the retained windowed Release DLL-load/map-spawn/",
            "client-entry/shutdown report. This static gate does not embed that live proof.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--zaero-root", required=True, type=Path)
    parser.add_argument("--port-root", required=True, type=Path)
    parser.add_argument("--binary", action="append", default=[], type=Path)
    parser.add_argument("--archive", action="append", default=[], type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--validation-json-output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        policy_path, policy = load_policy(args.policy)
        report = build_report(policy_path, args.zaero_root, args.port_root)
        binary_results = [validate_binary(policy, path) for path in args.binary]
        archive_results = [validate_archive(policy, path) for path in args.archive]
        write_text(args.json_output, stable_json_text(report))
        write_text(args.markdown_output, markdown_report(report))
        if args.validation_json_output is not None:
            if not binary_results and not archive_results:
                raise AuditError(
                    "--validation-json-output requires at least one --binary or --archive"
                )
            write_text(
                args.validation_json_output,
                stable_json_text(
                    {
                        "archives": archive_results,
                        "audit": "zaero-release-artifact-surfaces",
                        "binaries": binary_results,
                        "policy": {
                            "policy_id": policy["policy_id"],
                            "revision": policy["revision"],
                            "sha256": sha256_file(policy_path),
                        },
                        "schema_version": 1,
                    }
                ),
            )
        for result in binary_results:
            print(
                f"validated Release binary {result['path']}: "
                f"{result['forbidden_string_count']} forbidden strings absent",
                file=sys.stderr,
            )
        for result in archive_results:
            print(
                f"validated Release archive {result['path']}: "
                f"{result['member_count']} members, "
                f"{len(result['binary_members_scanned'])} binaries and "
                f"{len(result['pak_members_scanned'])} PAKs scanned",
                file=sys.stderr,
            )
    except (AuditError, OSError, UnicodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
