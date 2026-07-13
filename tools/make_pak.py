#!/usr/bin/env python3
"""Read and create Quake II PACK archives deterministically.

The helpers in this module are intentionally strict.  A path which is harmless
on one host can be an extraction escape or a case collision on another, so PAK
input is validated using the case-insensitive semantics used by Quake II.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import os
import shutil
import struct
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Iterator, Sequence


PAK_MAGIC = b"PACK"
PAK_HEADER = struct.Struct("<4sii")
PAK_ENTRY = struct.Struct("<56sii")
MAX_PAK_PATH_BYTES = 55  # One byte in the 56-byte field remains for NUL.
COPY_CHUNK_SIZE = 1024 * 1024
_WINDOWS_UNSAFE = frozenset('<>:"|?*')


class PakError(ValueError):
    """Raised when a PAK archive or member path is invalid."""


@dataclass(frozen=True)
class PakEntry:
    path: str
    offset: int
    size: int


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(COPY_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_pak_path(raw_path: str) -> str:
    """Return a canonical member path, or reject unsafe/ambiguous input."""

    if not raw_path:
        raise PakError("PAK member path is empty")
    if "\\" in raw_path:
        raise PakError(f"PAK member path must use '/': {raw_path!r}")
    if raw_path.startswith("/"):
        raise PakError(f"PAK member path is absolute: {raw_path!r}")
    if any(ord(char) < 32 or ord(char) == 127 for char in raw_path):
        raise PakError(f"PAK member path contains a control character: {raw_path!r}")
    if any(char in _WINDOWS_UNSAFE for char in raw_path):
        raise PakError(f"PAK member path is not portable to Windows: {raw_path!r}")

    try:
        encoded = raw_path.encode("ascii")
    except UnicodeEncodeError as exc:
        raise PakError(f"PAK member path is not ASCII: {raw_path!r}") from exc
    if len(encoded) > MAX_PAK_PATH_BYTES:
        raise PakError(
            f"PAK member path is too long ({len(encoded)} > "
            f"{MAX_PAK_PATH_BYTES} bytes): {raw_path!r}"
        )

    parts = PurePosixPath(raw_path).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise PakError(f"PAK member path contains an unsafe component: {raw_path!r}")
    if PurePosixPath(raw_path).as_posix() != raw_path:
        raise PakError(f"PAK member path is not canonical: {raw_path!r}")
    return raw_path


def _decode_name(field: bytes) -> str:
    nul = field.find(b"\0")
    if nul < 0:
        raise PakError("PAK directory member name is not NUL-terminated")
    # Retail-era PAK writers did not consistently clear the unused tail of the
    # fixed-width field.  Bytes after the first NUL are padding, not a path.
    try:
        name = field[:nul].decode("ascii")
    except UnicodeDecodeError as exc:
        raise PakError("PAK directory member name is not ASCII") from exc
    return validate_pak_path(name)


def read_pak_index(path: Path) -> list[PakEntry]:
    """Parse a PAK directory without extracting any members."""

    path = Path(path)
    file_size = path.stat().st_size
    if file_size < PAK_HEADER.size:
        raise PakError(f"PAK is smaller than its header: {path}")

    with path.open("rb") as stream:
        header = stream.read(PAK_HEADER.size)
        magic, directory_offset, directory_size = PAK_HEADER.unpack(header)
        if magic != PAK_MAGIC:
            raise PakError(f"Invalid PAK magic in {path}: {magic!r}")
        if directory_offset < PAK_HEADER.size or directory_size < 0:
            raise PakError(f"Invalid PAK directory bounds in {path}")
        if directory_size % PAK_ENTRY.size:
            raise PakError(f"PAK directory size is not a multiple of {PAK_ENTRY.size}: {path}")
        directory_end = directory_offset + directory_size
        if directory_end > file_size:
            raise PakError(f"PAK directory extends past end of file: {path}")

        stream.seek(directory_offset)
        raw_directory = stream.read(directory_size)

    entries: list[PakEntry] = []
    seen: dict[str, str] = {}
    occupied: list[tuple[int, int, str]] = []
    for index in range(0, directory_size, PAK_ENTRY.size):
        name_field, member_offset, member_size = PAK_ENTRY.unpack_from(raw_directory, index)
        member_path = _decode_name(name_field)
        folded = member_path.casefold()
        if folded in seen:
            raise PakError(
                f"Duplicate or case-colliding PAK members: {seen[folded]!r} and {member_path!r}"
            )
        seen[folded] = member_path

        if member_offset < PAK_HEADER.size or member_size < 0:
            raise PakError(f"Invalid bounds for PAK member {member_path!r}")
        member_end = member_offset + member_size
        if member_end > file_size:
            raise PakError(f"PAK member extends past end of file: {member_path!r}")
        if member_size and not (member_end <= directory_offset or member_offset >= directory_end):
            raise PakError(f"PAK member overlaps the directory: {member_path!r}")
        if member_size:
            occupied.append((member_offset, member_end, member_path))
        entries.append(PakEntry(member_path, member_offset, member_size))

    occupied.sort()
    for left, right in zip(occupied, occupied[1:]):
        if right[0] < left[1]:
            raise PakError(f"PAK members overlap: {left[2]!r} and {right[2]!r}")
    return entries


def iter_entry_chunks(
    stream: BinaryIO, entry: PakEntry, chunk_size: int = COPY_CHUNK_SIZE
) -> Iterator[bytes]:
    stream.seek(entry.offset)
    remaining = entry.size
    while remaining:
        chunk = stream.read(min(remaining, chunk_size))
        if not chunk:
            raise PakError(f"Unexpected EOF while reading {entry.path!r}")
        remaining -= len(chunk)
        yield chunk


def read_entry(path: Path, entry: PakEntry) -> bytes:
    with Path(path).open("rb") as stream:
        return b"".join(iter_entry_chunks(stream, entry))


def _matches_exclude(path: str, patterns: Sequence[str]) -> bool:
    folded = path.casefold()
    return any(fnmatch.fnmatchcase(folded, pattern.casefold()) for pattern in patterns)


def iter_source_files(
    root: Path, exclude_patterns: Sequence[str] = ()
) -> list[tuple[Path, str]]:
    root = Path(root).resolve()
    if not root.is_dir():
        raise PakError(f"Source directory does not exist: {root}")

    files: list[tuple[Path, str]] = []
    seen: dict[str, str] = {}
    for current, directories, names in os.walk(root, followlinks=False):
        current_path = Path(current)
        for directory in list(directories):
            directory_path = current_path / directory
            if directory_path.is_symlink():
                raise PakError(f"Symlinked directories are not allowed in PAK input: {directory_path}")
        for name in names:
            file_path = current_path / name
            if file_path.is_symlink():
                raise PakError(f"Symlinked files are not allowed in PAK input: {file_path}")
            relative = file_path.relative_to(root).as_posix()
            validate_pak_path(relative)
            if _matches_exclude(relative, exclude_patterns):
                continue
            folded = relative.casefold()
            if folded in seen:
                raise PakError(
                    f"Duplicate or case-colliding source paths: {seen[folded]!r} and {relative!r}"
                )
            seen[folded] = relative
            files.append((file_path, relative))

    files.sort(key=lambda item: (item[1].casefold(), item[1]))
    return files


def build_pak(
    source_dir: Path,
    output_path: Path,
    *,
    exclude_patterns: Sequence[str] = (),
) -> list[PakEntry]:
    """Build a byte-for-byte deterministic PAK and return its index."""

    source = Path(source_dir).resolve()
    output = Path(output_path).resolve()
    try:
        output.relative_to(source)
    except ValueError:
        pass
    else:
        raise PakError("The output PAK must not be inside its source directory")

    source_files = iter_source_files(source, exclude_patterns)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    if temporary.exists():
        temporary.unlink()

    entries: list[PakEntry] = []
    try:
        with temporary.open("wb") as pak:
            pak.write(PAK_HEADER.pack(PAK_MAGIC, 0, 0))
            for source_path, relative in source_files:
                offset = pak.tell()
                size = source_path.stat().st_size
                if offset > 0x7FFFFFFF or size > 0x7FFFFFFF:
                    raise PakError("Classic Quake II PAK offsets and sizes are limited to signed 32-bit")
                with source_path.open("rb") as source_stream:
                    shutil.copyfileobj(source_stream, pak, COPY_CHUNK_SIZE)
                entries.append(PakEntry(relative, offset, size))

            directory_offset = pak.tell()
            for entry in entries:
                encoded = entry.path.encode("ascii")
                name_field = encoded + bytes(PAK_ENTRY.size - 8 - len(encoded))
                pak.write(PAK_ENTRY.pack(name_field, entry.offset, entry.size))
            directory_size = len(entries) * PAK_ENTRY.size
            if directory_offset > 0x7FFFFFFF or directory_size > 0x7FFFFFFF:
                raise PakError("Classic Quake II PAK directory is limited to signed 32-bit")
            pak.seek(0)
            pak.write(PAK_HEADER.pack(PAK_MAGIC, directory_offset, directory_size))
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()

    parsed = read_pak_index(output)
    if parsed != entries:
        raise PakError("Post-build PAK verification did not reproduce the planned directory")
    return parsed


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a deterministic, path-safe Quake II .pak archive."
    )
    parser.add_argument("source_dir", type=Path, help="Directory which becomes the PAK root")
    parser.add_argument("output_path", type=Path, help="Destination .pak path")
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="Case-insensitive member-path glob to omit (repeatable)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        entries = build_pak(
            args.source_dir,
            args.output_path,
            exclude_patterns=args.exclude,
        )
    except (OSError, PakError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(
        f"Packed {len(entries)} files into {args.output_path} "
        f"(sha256 {sha256_file(args.output_path)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
