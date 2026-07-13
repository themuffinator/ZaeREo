#!/usr/bin/env python3
"""Create a byte-reproducible, path-safe release ZIP.

Unlike ``Compress-Archive`` and ``ZipFile.CreateFromDirectory``, this helper
normalizes entry order, timestamps, permissions, and path separators.  The
archive is replaced atomically only after every source path has been checked.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import tempfile
import zipfile

from make_pak import PakError, iter_source_files, validate_pak_path


FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
COPY_CHUNK_SIZE = 1024 * 1024


class ReleaseZipError(ValueError):
    """Raised when a requested release archive would be unsafe."""


def _validated_prefix(prefix: str) -> str:
    normalized = prefix.replace("\\", "/").strip("/")
    if not normalized:
        return ""
    validate_pak_path(f"{normalized}/placeholder")
    return normalized


def _member_name(relative: str, prefix: str) -> str:
    name = f"{prefix}/{relative}" if prefix else relative
    # The PAK validator is stricter than ZIP itself and intentionally rejects
    # absolute paths, traversal, drive prefixes, controls, and non-portable
    # separators.
    validate_pak_path(name)
    return name


def build_release_zip(source_dir: Path, output_path: Path, *, prefix: str = "") -> str:
    source = Path(source_dir).resolve()
    output = Path(output_path).resolve()
    if not source.is_dir():
        raise ReleaseZipError(f"Release stage is not a directory: {source}")
    try:
        output.relative_to(source)
    except ValueError:
        pass
    else:
        raise ReleaseZipError("Output archive must not be inside the staged tree")

    prefix = _validated_prefix(prefix)
    try:
        files = iter_source_files(source)
    except PakError as exc:
        raise ReleaseZipError(str(exc)) from exc
    if not files:
        raise ReleaseZipError("Release stage contains no files")

    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
    )
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(
            temporary,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
            allowZip64=True,
        ) as archive:
            for path, relative in files:
                member = _member_name(relative, prefix)
                info = zipfile.ZipInfo(member, FIXED_TIMESTAMP)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = (0o100644 & 0xFFFF) << 16
                info.flag_bits |= 0x800  # UTF-8 member names
                with path.open("rb") as source_stream, archive.open(info, "w") as dest:
                    for chunk in iter(lambda: source_stream.read(COPY_CHUNK_SIZE), b""):
                        dest.write(chunk)
        os.replace(temporary, output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    digest = hashlib.sha256()
    with output.open("rb") as stream:
        for chunk in iter(lambda: stream.read(COPY_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_dir", type=Path, help="Staged directory to archive")
    parser.add_argument("output_path", type=Path, help="Destination .zip")
    parser.add_argument(
        "--prefix",
        default="",
        help="Optional single archive-root prefix (for example 'zaereo')",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        digest = build_release_zip(args.source_dir, args.output_path, prefix=args.prefix)
    except (OSError, PakError, ReleaseZipError) as exc:
        raise SystemExit(f"error: {exc}") from exc
    print(f"{args.output_path.resolve()}  sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
