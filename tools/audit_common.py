#!/usr/bin/env python3
"""Shared deterministic and defensive helpers for the ZaeREo audit tools."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import struct
from typing import BinaryIO, Any


PAK_HEADER = struct.Struct("<4sii")
PAK_ENTRY = struct.Struct("<56sii")
BSP_HEADER = struct.Struct("<4si")
BSP_LUMP = struct.Struct("<ii")
Q2_BSP_VERSION = 38
Q2_BSP_LUMP_COUNT = 19


class AuditError(ValueError):
    """Raised when an audited input is malformed or unsafe."""


def checked_root(path: str | os.PathLike[str], label: str) -> Path:
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        raise AuditError(f"{label} is not a directory: {root}")
    return root


def checked_file(path: str | os.PathLike[str], label: str) -> Path:
    file_path = Path(path).expanduser().resolve()
    if not file_path.is_file():
        raise AuditError(f"{label} is not a file: {file_path}")
    return file_path


def checked_range(offset: int, length: int, total: int, label: str) -> None:
    if offset < 0 or length < 0:
        raise AuditError(f"{label} has a negative offset or length")
    if offset > total or length > total - offset:
        raise AuditError(
            f"{label} range [{offset}, {offset + length}) exceeds {total} bytes"
        )


def normalize_runtime_path(raw: str, label: str = "runtime path") -> str:
    """Validate a Quake virtual path without changing its case."""

    value = raw.replace("\\", "/")
    if not value or value.startswith("/") or value.endswith("/"):
        raise AuditError(f"{label} is empty or absolute: {raw!r}")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise AuditError(f"{label} contains a control character: {raw!r}")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise AuditError(f"{label} contains an unsafe path segment: {raw!r}")
    if ":" in parts[0]:
        raise AuditError(f"{label} contains a drive or URI prefix: {raw!r}")
    return "/".join(parts)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_stream_range(
    stream: BinaryIO, offset: int, length: int, *, chunk_size: int = 1024 * 1024
) -> str:
    digest = hashlib.sha256()
    stream.seek(offset)
    remaining = length
    while remaining:
        chunk = stream.read(min(remaining, chunk_size))
        if not chunk:
            raise AuditError("unexpected end of file while hashing a bounded range")
        digest.update(chunk)
        remaining -= len(chunk)
    return digest.hexdigest()


def stable_json_text(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_text(path: str | os.PathLike[str] | None, text: str) -> None:
    if path is None:
        print(text, end="")
        return
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8", newline="\n")


def markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _relative_files(root: Path) -> list[tuple[str, Path]]:
    root_resolved = root.resolve()
    records: list[tuple[str, Path]] = []
    for candidate in root.rglob("*"):
        if candidate.is_symlink():
            raise AuditError(f"tree contains a symbolic link: {candidate}")
        if not candidate.is_file():
            continue
        resolved = candidate.resolve()
        try:
            relative = resolved.relative_to(root_resolved).as_posix()
        except ValueError as error:
            raise AuditError(f"tree entry escapes its root: {candidate}") from error
        relative = normalize_runtime_path(relative, "tree-relative path")
        records.append((relative, resolved))
    records.sort(key=lambda item: item[0].encode("utf-8"))
    return records


def tree_manifest(root: Path) -> dict[str, Any]:
    """Hash every regular file and a canonical stream of the resulting records."""

    files: list[dict[str, Any]] = []
    aggregate = hashlib.sha256()
    total_size = 0
    seen_case: dict[str, str] = {}
    case_collisions: list[list[str]] = []
    for relative, path in _relative_files(root):
        folded = relative.casefold()
        previous = seen_case.get(folded)
        if previous is not None and previous != relative:
            case_collisions.append(sorted([previous, relative]))
        else:
            seen_case[folded] = relative
        size = path.stat().st_size
        file_hash = sha256_file(path)
        record = {"path": relative, "sha256": file_hash, "size": size}
        files.append(record)
        total_size += size
        aggregate.update(relative.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(str(size).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(file_hash.encode("ascii"))
        aggregate.update(b"\n")
    return {
        "aggregate_algorithm": "sha256(path_utf8 + NUL + decimal_size + NUL + sha256 + LF)",
        "case_collisions": sorted(case_collisions),
        "file_count": len(files),
        "files": files,
        "total_size": total_size,
        "tree_sha256": aggregate.hexdigest(),
    }


@dataclass(frozen=True)
class PakEntryRecord:
    runtime_path: str
    offset: int
    size: int
    sha256: str


@dataclass(frozen=True)
class PakArchive:
    path: Path
    label: str
    size: int
    sha256: str
    directory_offset: int
    directory_length: int
    entries: tuple[PakEntryRecord, ...]

    def read_entry(self, entry: PakEntryRecord, max_size: int | None = None) -> bytes:
        if max_size is not None and entry.size > max_size:
            raise AuditError(
                f"{self.label}:{entry.runtime_path} is {entry.size} bytes; limit is {max_size}"
            )
        with self.path.open("rb") as stream:
            stream.seek(entry.offset)
            data = stream.read(entry.size)
        if len(data) != entry.size:
            raise AuditError(f"short read for {self.label}:{entry.runtime_path}")
        return data


def parse_pak(
    path: Path,
    label: str | None = None,
    max_entries: int = 1_000_000,
    *,
    allow_nonzero_name_padding: bool = False,
) -> PakArchive:
    path = checked_file(path, "PAK")
    archive_label = label or path.name
    size = path.stat().st_size
    if size < PAK_HEADER.size:
        raise AuditError(f"{archive_label} is shorter than a PAK header")
    with path.open("rb") as stream:
        header = stream.read(PAK_HEADER.size)
        magic, directory_offset, directory_length = PAK_HEADER.unpack(header)
        if magic != b"PACK":
            raise AuditError(f"{archive_label} has invalid PAK magic {magic!r}")
        checked_range(directory_offset, directory_length, size, f"{archive_label} directory")
        if directory_length % PAK_ENTRY.size:
            raise AuditError(f"{archive_label} directory length is not a multiple of 64")
        entry_count = directory_length // PAK_ENTRY.size
        if entry_count > max_entries:
            raise AuditError(
                f"{archive_label} contains {entry_count} entries; limit is {max_entries}"
            )
        stream.seek(directory_offset)
        directory = stream.read(directory_length)
        if len(directory) != directory_length:
            raise AuditError(f"{archive_label} directory was truncated")

        entries: list[PakEntryRecord] = []
        exact_paths: set[str] = set()
        for index in range(entry_count):
            raw_name, offset, entry_size = PAK_ENTRY.unpack_from(
                directory, index * PAK_ENTRY.size
            )
            name_bytes, separator, padding = raw_name.partition(b"\0")
            if not name_bytes:
                raise AuditError(f"{archive_label} entry {index} has an empty name")
            if separator and any(padding) and not allow_nonzero_name_padding:
                raise AuditError(
                    f"{archive_label} entry {index} has non-NUL bytes after its name terminator"
                )
            try:
                raw_path = name_bytes.decode("ascii")
            except UnicodeDecodeError as error:
                raise AuditError(
                    f"{archive_label} entry {index} name is not ASCII"
                ) from error
            runtime_path = normalize_runtime_path(
                raw_path, f"{archive_label} entry {index} path"
            )
            if runtime_path in exact_paths:
                raise AuditError(
                    f"{archive_label} contains duplicate path {runtime_path!r}"
                )
            exact_paths.add(runtime_path)
            checked_range(offset, entry_size, size, f"{archive_label}:{runtime_path}")
            entry_hash = sha256_stream_range(stream, offset, entry_size)
            entries.append(PakEntryRecord(runtime_path, offset, entry_size, entry_hash))

    entries.sort(key=lambda entry: entry.runtime_path.encode("utf-8"))
    return PakArchive(
        path=path,
        label=archive_label,
        size=size,
        sha256=sha256_file(path),
        directory_offset=directory_offset,
        directory_length=directory_length,
        entries=tuple(entries),
    )


def natural_name_key(path: Path) -> tuple[object, ...]:
    parts = re.split(r"(\d+)", path.name.casefold())
    return tuple(int(part) if part.isdigit() else part for part in parts)


def discover_paks(root: Path) -> list[Path]:
    paks = [
        path.resolve()
        for path in root.iterdir()
        if path.is_file() and path.suffix.casefold() == ".pak"
    ]
    return sorted(paks, key=natural_name_key)


def case_collision_groups(paths: Iterable[str]) -> list[list[str]]:
    groups: dict[str, set[str]] = {}
    for path in paths:
        groups.setdefault(path.casefold(), set()).add(path)
    return sorted(
        [sorted(group) for group in groups.values() if len(group) > 1],
        key=lambda group: [item.encode("utf-8") for item in group],
    )


@dataclass(frozen=True)
class BspEntityLump:
    version: int
    entities: tuple[tuple[tuple[str, str], ...], ...]


def _entity_tokens(text: str) -> Iterator[str]:
    index = 0
    length = len(text)
    while index < length:
        while index < length and text[index].isspace():
            index += 1
        if index >= length:
            return
        if text.startswith("//", index):
            newline = text.find("\n", index + 2)
            index = length if newline < 0 else newline + 1
            continue
        if text[index] in "{}":
            yield text[index]
            index += 1
            continue
        if text[index] == '"':
            index += 1
            start = index
            while index < length and text[index] != '"':
                index += 1
            if index >= length:
                raise AuditError("unterminated quoted token in BSP entity lump")
            yield text[start:index]
            index += 1
            continue
        start = index
        while (
            index < length
            and not text[index].isspace()
            and text[index] not in "{}"
        ):
            index += 1
        yield text[start:index]


def parse_entity_text(data: bytes, max_entities: int = 1_000_000) -> tuple[tuple[tuple[str, str], ...], ...]:
    data = data.rstrip(b"\0")
    if b"\0" in data:
        raise AuditError("BSP entity lump contains an embedded NUL byte")
    text = data.decode("latin-1")
    tokens = iter(_entity_tokens(text))
    entities: list[tuple[tuple[str, str], ...]] = []
    while True:
        try:
            token = next(tokens)
        except StopIteration:
            break
        if token != "{":
            raise AuditError(f"expected '{{' in BSP entity lump, found {token!r}")
        pairs: list[tuple[str, str]] = []
        while True:
            try:
                key = next(tokens)
            except StopIteration as error:
                raise AuditError("unterminated entity in BSP entity lump") from error
            if key == "}":
                break
            if key == "{":
                raise AuditError("nested entity opening brace in BSP entity lump")
            try:
                value = next(tokens)
            except StopIteration as error:
                raise AuditError(f"missing value for entity key {key!r}") from error
            if value in ("{", "}"):
                raise AuditError(f"invalid braced value for entity key {key!r}")
            pairs.append((key, value))
        entities.append(tuple(pairs))
        if len(entities) > max_entities:
            raise AuditError(f"BSP entity count exceeds limit {max_entities}")
    return tuple(entities)


def parse_bsp_entity_lump(
    data: bytes,
    *,
    expected_version: int = Q2_BSP_VERSION,
    max_entity_bytes: int = 64 * 1024 * 1024,
    max_entities: int = 1_000_000,
) -> BspEntityLump:
    header_size = BSP_HEADER.size + Q2_BSP_LUMP_COUNT * BSP_LUMP.size
    if len(data) < header_size:
        raise AuditError("BSP is shorter than the Quake II header")
    magic, version = BSP_HEADER.unpack_from(data, 0)
    if magic != b"IBSP":
        raise AuditError(f"invalid BSP magic {magic!r}")
    if version != expected_version:
        raise AuditError(f"unsupported BSP version {version}; expected {expected_version}")
    lumps: list[tuple[int, int]] = []
    for index in range(Q2_BSP_LUMP_COUNT):
        offset, length = BSP_LUMP.unpack_from(data, BSP_HEADER.size + index * BSP_LUMP.size)
        checked_range(offset, length, len(data), f"BSP lump {index}")
        lumps.append((offset, length))
    entity_offset, entity_length = lumps[0]
    if entity_length > max_entity_bytes:
        raise AuditError(
            f"BSP entity lump is {entity_length} bytes; limit is {max_entity_bytes}"
        )
    entities = parse_entity_text(
        data[entity_offset : entity_offset + entity_length], max_entities=max_entities
    )
    return BspEntityLump(version=version, entities=entities)


def pairs_to_multimap(pairs: Sequence[tuple[str, str]]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for key, value in pairs:
        result.setdefault(key, []).append(value)
    return result


def sorted_count_dict(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[0].encode("utf-8")))


def extension_counts(paths: Iterable[str]) -> dict[str, int]:
    values = []
    for path in paths:
        suffix = Path(path).suffix.casefold()
        values.append(suffix if suffix else "[no extension]")
    return sorted_count_dict(values)
