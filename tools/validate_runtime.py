#!/usr/bin/env python3
"""Validate an imported Zaero runtime tree or its packaged PAK.

Validation is read-only.  It checks portable/case-safe paths, rejects legacy
state and binaries, and optionally proves every imported byte against the
manifest produced by ``import_legacy_assets.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from import_legacy_assets import KNOWN_PAK_SHA256, SCHEMA_VERSION, excluded_reason
from make_pak import (
    PakEntry,
    PakError,
    iter_entry_chunks,
    iter_source_files,
    read_pak_index,
    sha256_file,
    validate_pak_path,
)


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ValidationError(ValueError):
    """Raised when runtime content does not match its safety contract."""


@dataclass(frozen=True)
class RuntimeAsset:
    path: str
    size: int
    calculate_sha256: Callable[[], str]


def _directory_assets(root: Path) -> dict[str, RuntimeAsset]:
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValidationError(f"Runtime directory does not exist: {root}")
    try:
        files = iter_source_files(root)
    except PakError as exc:
        raise ValidationError(str(exc)) from exc
    result: dict[str, RuntimeAsset] = {}
    for path, relative in files:
        result[relative.casefold()] = RuntimeAsset(
            relative,
            path.stat().st_size,
            lambda path=path: sha256_file(path),
        )
    return result


def _pak_entry_hash(pak_path: Path, entry: PakEntry) -> str:
    digest = hashlib.sha256()
    with pak_path.open("rb") as stream:
        for chunk in iter_entry_chunks(stream, entry):
            digest.update(chunk)
    return digest.hexdigest()


def _pak_assets(path: Path) -> dict[str, RuntimeAsset]:
    pak_path = Path(path).resolve()
    try:
        entries = read_pak_index(pak_path)
    except (OSError, PakError) as exc:
        raise ValidationError(f"Could not safely parse runtime PAK: {exc}") from exc
    return {
        entry.path.casefold(): RuntimeAsset(
            entry.path,
            entry.size,
            lambda pak_path=pak_path, entry=entry: _pak_entry_hash(pak_path, entry),
        )
        for entry in entries
    }


def load_manifest(
    path: Path,
    *,
    verify_known_source_hashes: bool = True,
) -> dict[str, object]:
    try:
        manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"Could not read manifest: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValidationError(f"Unsupported asset manifest schema (expected {SCHEMA_VERSION})")

    assets = manifest.get("assets")
    if not isinstance(assets, list):
        raise ValidationError("Manifest 'assets' must be a list")
    seen: dict[str, str] = {}
    previous_key: tuple[str, str] | None = None
    for item in assets:
        if not isinstance(item, dict):
            raise ValidationError("Every manifest asset must be an object")
        path_value = item.get("path")
        size = item.get("size")
        digest = item.get("sha256")
        if not isinstance(path_value, str):
            raise ValidationError("Manifest asset path must be a string")
        try:
            validate_pak_path(path_value)
        except PakError as exc:
            raise ValidationError(str(exc)) from exc
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ValidationError(f"Manifest asset has invalid size: {path_value!r}")
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise ValidationError(f"Manifest asset has invalid SHA-256: {path_value!r}")
        folded = path_value.casefold()
        if folded in seen:
            raise ValidationError(
                f"Manifest has duplicate/case-colliding paths: {seen[folded]!r}, {path_value!r}"
            )
        seen[folded] = path_value
        sort_key = (folded, path_value)
        if previous_key is not None and sort_key < previous_key:
            raise ValidationError("Manifest assets are not in deterministic path order")
        previous_key = sort_key

    required_loose = manifest.get("required_loose_paths")
    if not isinstance(required_loose, list) or not all(
        isinstance(item, str) for item in required_loose
    ):
        raise ValidationError("Manifest 'required_loose_paths' must be a string list")
    for relative in required_loose:
        if relative.casefold() not in seen:
            raise ValidationError(f"Required loose asset is not represented in manifest: {relative}")

    source_archives = manifest.get("source_archives")
    if not isinstance(source_archives, list):
        raise ValidationError("Manifest 'source_archives' must be a list")
    if verify_known_source_hashes:
        archive_hashes: dict[str, str] = {}
        for item in source_archives:
            if not isinstance(item, dict):
                raise ValidationError("Every source archive must be an object")
            name, digest = item.get("name"), item.get("sha256")
            if isinstance(name, str) and isinstance(digest, str):
                archive_hashes[name.casefold()] = digest
        for name, expected in KNOWN_PAK_SHA256.items():
            if archive_hashes.get(name.casefold()) != expected:
                raise ValidationError(f"Manifest does not prove the known supplied hash for {name}")
    return manifest


def validate_runtime(
    assets: Mapping[str, RuntimeAsset],
    *,
    manifest: Mapping[str, object] | None = None,
    strict: bool = False,
) -> dict[str, int]:
    for asset in assets.values():
        try:
            validate_pak_path(asset.path)
        except PakError as exc:
            raise ValidationError(str(exc)) from exc
        reason = excluded_reason(asset.path)
        if reason:
            raise ValidationError(f"Forbidden runtime member {asset.path!r}: {reason}")

    verified = 0
    if manifest is not None:
        manifest_items = manifest.get("assets")
        if not isinstance(manifest_items, list):
            raise ValidationError("Manifest 'assets' must be a list")
        expected_keys: set[str] = set()
        for item in manifest_items:
            if not isinstance(item, dict):
                raise ValidationError("Every manifest asset must be an object")
            expected_path = str(item["path"])
            folded = expected_path.casefold()
            expected_keys.add(folded)
            actual = assets.get(folded)
            if actual is None:
                raise ValidationError(f"Manifest asset is missing: {expected_path}")
            if actual.path != expected_path:
                raise ValidationError(
                    f"Runtime spelling differs from manifest: {actual.path!r} vs {expected_path!r}"
                )
            if actual.size != item["size"]:
                raise ValidationError(f"Runtime size differs from manifest: {expected_path}")
            if actual.calculate_sha256() != item["sha256"]:
                raise ValidationError(f"Runtime SHA-256 differs from manifest: {expected_path}")
            verified += 1
        if strict:
            extras = sorted(asset.path for key, asset in assets.items() if key not in expected_keys)
            if extras:
                raise ValidationError(f"Runtime has files absent from strict manifest: {extras[0]!r}")

    return {"assets": len(assets), "manifest_verified": verified}


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Zaero runtime content without modifying it.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--root", type=Path, help="Loose runtime content root")
    source.add_argument("--pak", type=Path, help="Packaged runtime PAK")
    parser.add_argument("--manifest", type=Path, help="Importer manifest to verify byte-for-byte")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="With a manifest, reject all files not listed by the importer",
    )
    parser.add_argument(
        "--allow-unknown-source-hashes",
        action="store_true",
        help="Development/testing only: accept a manifest from other source PAKs",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        assets = _directory_assets(args.root) if args.root else _pak_assets(args.pak)
        manifest = (
            load_manifest(
                args.manifest,
                verify_known_source_hashes=not args.allow_unknown_source_hashes,
            )
            if args.manifest
            else None
        )
        result = validate_runtime(assets, manifest=manifest, strict=args.strict)
    except (OSError, ValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(
        f"Validated {result['assets']} runtime assets; "
        f"{result['manifest_verified']} matched the import manifest."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
