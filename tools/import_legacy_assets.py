#!/usr/bin/env python3
"""Import a verified Zaero installation into a clean runtime content tree.

The original distribution is layered as pak0 -> pak1 -> pak2, followed by nine
loose files which were deliberately shipped outside the PAKs.  This importer
models that precedence explicitly, never executes legacy binaries, and emits a
deterministic provenance manifest without recording the user's absolute path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterator, Mapping, Sequence

from make_pak import (
    COPY_CHUNK_SIZE,
    PakEntry,
    PakError,
    iter_entry_chunks,
    iter_source_files,
    read_pak_index,
    sha256_file,
    validate_pak_path,
)


SCHEMA_VERSION = 1
PAK_LAYERS = ("pak0.pak", "pak1.pak", "pak2.pak")
KNOWN_PAK_SHA256 = {
    "pak0.pak": "1de0161318cb946dbaad1ad6ac9abe375d3aa1da57f3571fdee3e5549cb0fafd",
    "pak1.pak": "3806e4cc59564e5a081518adf04fc608d79159b1e31d073b6699f0a3a34b4973",
    "pak2.pak": "e0b043599386f5b39701919f334de37d21011dd254630e17504dece497fec82e",
}
REQUIRED_LOOSE_PATHS = (
    "sprites/plasma1.sp2",
    "sprites/plasma1_0.pcx",
    "sprites/plasma1_1.pcx",
    "sprites/plasma1_2.pcx",
    "sprites/plasma1_3.pcx",
    "sprites/plasmashield.sp2",
    "sprites/plasmashield_0.pcx",
    "video/intro.cin",
    "video/outro.cin",
)


class ImportError(ValueError):
    """Raised when the legacy source or requested destination is unsafe."""


def excluded_reason(path: str) -> str | None:
    """Return why a legacy member is intentionally not runtime content."""

    folded = path.casefold()
    parts = PurePosixPath(folded).parts
    name = parts[-1]
    if folded in {"default.cfg", "autoexec", "autoexec.cfg"}:
        return "legacy configuration would replace or unbind Rerelease settings"
    if name.endswith((".dll", ".so", ".dylib")):
        return "legacy native game binary is incompatible with Quake II Rerelease"
    if name.endswith(".dm2") or (parts and parts[0] == "demos"):
        return "legacy protocol demo is not Rerelease runtime content"
    if name.endswith(".ssv") or (parts and parts[0] == "save"):
        return "legacy saved game is machine/generated state"
    if parts and parts[0] in {"screenshots", "scrnshot"}:
        return "player-generated screenshot is not runtime content"
    return None


@dataclass(frozen=True)
class AssetSource:
    path: str
    source_label: str
    container: Path
    size: int
    pak_entry: PakEntry | None = None

    def chunks(self) -> Iterator[bytes]:
        if self.pak_entry is None:
            with self.container.open("rb") as stream:
                for chunk in iter(lambda: stream.read(COPY_CHUNK_SIZE), b""):
                    yield chunk
            return
        with self.container.open("rb") as stream:
            yield from iter_entry_chunks(stream, self.pak_entry)

    def sha256(self) -> str:
        digest = hashlib.sha256()
        for chunk in self.chunks():
            digest.update(chunk)
        return digest.hexdigest()


@dataclass(frozen=True)
class ImportPlan:
    assets: tuple[AssetSource, ...]
    manifest: dict[str, object]


def _insert_asset(
    merged: dict[str, AssetSource],
    asset: AssetSource,
    overrides: list[dict[str, str]],
) -> None:
    folded = asset.path.casefold()
    previous = merged.get(folded)
    if previous is not None and previous.path != asset.path:
        raise ImportError(
            "Layered assets differ only by case, which is ambiguous on Quake II "
            f"filesystems: {previous.path!r} ({previous.source_label}) and "
            f"{asset.path!r} ({asset.source_label})"
        )
    if previous is not None:
        overrides.append(
            {
                "path": asset.path,
                "replaced_source": previous.source_label,
                "winning_source": asset.source_label,
            }
        )
    merged[folded] = asset


def collect_import_plan(
    source_root: Path,
    *,
    expected_hashes: Mapping[str, str] = KNOWN_PAK_SHA256,
    verify_hashes: bool = True,
) -> ImportPlan:
    source = Path(source_root).resolve()
    if not source.is_dir():
        raise ImportError(f"Legacy Zaero directory does not exist: {source}")

    merged: dict[str, AssetSource] = {}
    pak_manifest: list[dict[str, object]] = []
    excluded: list[dict[str, object]] = []
    overrides: list[dict[str, str]] = []

    for layer_name in PAK_LAYERS:
        pak_path = source / layer_name
        if not pak_path.is_file() or pak_path.is_symlink():
            raise ImportError(f"Required legacy archive is missing: {pak_path}")
        actual_hash = sha256_file(pak_path)
        expected_hash = expected_hashes.get(layer_name)
        if verify_hashes and actual_hash != expected_hash:
            raise ImportError(
                f"Unexpected SHA-256 for {layer_name}: {actual_hash}; "
                f"expected {expected_hash or 'a known retail hash'}"
            )
        try:
            entries = read_pak_index(pak_path)
        except (OSError, PakError) as exc:
            raise ImportError(f"Could not safely parse {layer_name}: {exc}") from exc
        pak_manifest.append(
            {
                "name": layer_name,
                "sha256": actual_hash,
                "expected_sha256": expected_hash,
                "size": pak_path.stat().st_size,
                "entry_count": len(entries),
            }
        )
        for entry in entries:
            reason = excluded_reason(entry.path)
            if reason:
                excluded.append(
                    {
                        "path": entry.path,
                        "source": layer_name,
                        "size": entry.size,
                        "reason": reason,
                    }
                )
                continue
            _insert_asset(
                merged,
                AssetSource(entry.path, layer_name, pak_path, entry.size, entry),
                overrides,
            )

    for relative in REQUIRED_LOOSE_PATHS:
        validate_pak_path(relative)
        loose_path = source.joinpath(*PurePosixPath(relative).parts)
        if not loose_path.is_file() or loose_path.is_symlink():
            raise ImportError(f"Required loose legacy asset is missing or unsafe: {relative}")
        _insert_asset(
            merged,
            AssetSource(relative, f"loose:{relative}", loose_path, loose_path.stat().st_size),
            overrides,
        )

    # Nothing else outside the PAK layers is imported implicitly. Recording the
    # allowlist misses makes that safety property auditable (notably the retail
    # DLL/SO, autoexec, installer state, readmes, and icon).
    allowed_loose = {path.casefold() for path in REQUIRED_LOOSE_PATHS}
    pak_names = {name.casefold() for name in PAK_LAYERS}
    for loose_path in sorted(
        (path for path in source.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(source).as_posix().casefold(),
    ):
        relative = loose_path.relative_to(source).as_posix()
        folded = relative.casefold()
        if folded in allowed_loose or folded in pak_names:
            continue
        excluded.append(
            {
                "path": relative,
                "source": "loose-root",
                "size": loose_path.stat().st_size,
                "reason": excluded_reason(relative) or "not on the explicit loose runtime allowlist",
            }
        )

    assets = tuple(sorted(merged.values(), key=lambda asset: (asset.path.casefold(), asset.path)))
    asset_entries: list[dict[str, object]] = []
    for asset in assets:
        asset_entries.append(
            {
                "path": asset.path,
                "size": asset.size,
                "sha256": asset.sha256(),
                "source": asset.source_label,
            }
        )

    manifest: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "product": "Zaero legacy runtime asset import",
        "precedence": [*PAK_LAYERS, "required loose files"],
        "source_archives": pak_manifest,
        "required_loose_paths": list(REQUIRED_LOOSE_PATHS),
        "assets": asset_entries,
        "overrides": sorted(
            overrides,
            key=lambda item: (
                item["path"].casefold(),
                item["replaced_source"],
                item["winning_source"],
            ),
        ),
        "excluded": sorted(
            excluded,
            key=lambda item: (str(item["path"]).casefold(), str(item["source"])),
        ),
    }
    return ImportPlan(assets, manifest)


def manifest_json(manifest: Mapping[str, object]) -> str:
    return json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def _destination(root: Path, relative: str) -> Path:
    destination = root.joinpath(*PurePosixPath(relative).parts)
    resolved = destination.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ImportError(f"Destination escapes import root: {relative!r}") from exc
    return destination


def _hash_existing(path: Path) -> str:
    return sha256_file(path)


def execute_import(
    plan: ImportPlan,
    output_root: Path,
    *,
    manifest_path: Path | None = None,
    dry_run: bool = False,
    overwrite: bool = False,
) -> dict[str, int]:
    """Materialize a plan after preflighting every target conflict."""

    output = Path(output_root).resolve()
    if output.exists() and not output.is_dir():
        raise ImportError(f"Destination root is not a directory: {output}")
    if not dry_run:
        output.mkdir(parents=True, exist_ok=True)
    existing_by_case: dict[str, str] = {}
    existing_files: list[tuple[Path, str]] = []
    if output.exists():
        try:
            existing_files = iter_source_files(output)
        except PakError as exc:
            raise ImportError(f"Destination tree is not PAK-safe: {exc}") from exc
    for _, relative in existing_files:
        existing_by_case[relative.casefold()] = relative

    manifest_assets = {
        str(entry["path"]): entry for entry in plan.manifest.get("assets", [])  # type: ignore[union-attr]
    }
    targets: list[tuple[AssetSource, Path, str, bool]] = []
    for asset in plan.assets:
        destination = _destination(output, asset.path)
        existing_spelling = existing_by_case.get(asset.path.casefold())
        if existing_spelling is not None and existing_spelling != asset.path:
            raise ImportError(
                f"Destination case collision: {existing_spelling!r} and {asset.path!r}"
            )
        expected_hash = str(manifest_assets[asset.path]["sha256"])
        unchanged = False
        if destination.exists():
            if destination.is_symlink() or not destination.is_file():
                raise ImportError(f"Destination is not a regular file: {destination}")
            unchanged = _hash_existing(destination) == expected_hash
            if not unchanged and not overwrite:
                raise ImportError(
                    f"Destination differs from verified legacy asset; pass --overwrite: {destination}"
                )
        targets.append((asset, destination, expected_hash, unchanged))

    if dry_run:
        return {
            "planned": len(plan.assets),
            "written": 0,
            "unchanged": sum(1 for *_, unchanged in targets if unchanged),
        }

    written = 0
    unchanged_count = 0
    for asset, destination, expected_hash, unchanged in targets:
        if unchanged:
            unchanged_count += 1
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.importing")
        if temporary.exists():
            temporary.unlink()
        try:
            with temporary.open("wb") as target:
                for chunk in asset.chunks():
                    target.write(chunk)
            if temporary.stat().st_size != asset.size or sha256_file(temporary) != expected_hash:
                raise ImportError(f"Copied bytes failed verification: {asset.path}")
            os.replace(temporary, destination)
        finally:
            if temporary.exists():
                temporary.unlink()
        written += 1

    if manifest_path is not None:
        manifest_destination = Path(manifest_path).resolve()
        manifest_destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = manifest_destination.with_name(f".{manifest_destination.name}.tmp")
        temporary.write_text(manifest_json(plan.manifest), encoding="utf-8", newline="\n")
        os.replace(temporary, manifest_destination)

    return {"planned": len(plan.assets), "written": written, "unchanged": unchanged_count}


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import verified Zaero 1.1 assets using retail PAK precedence."
    )
    parser.add_argument("--source", type=Path, required=True, help="Legacy Zaero install directory")
    parser.add_argument("--output", type=Path, required=True, help="Destination runtime content root")
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Manifest path (default: sibling '<output>-asset-manifest.json')",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate and plan without writing")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace differing files inside the explicitly selected output root",
    )
    parser.add_argument(
        "--allow-unknown-hashes",
        action="store_true",
        help="Development/testing only: do not require the known supplied PAK hashes",
    )
    parser.add_argument(
        "--print-manifest",
        action="store_true",
        help="Write the deterministic manifest JSON to stdout",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    output = args.output.resolve()
    manifest_path = args.manifest
    if manifest_path is None:
        manifest_path = output.with_name(f"{output.name}-asset-manifest.json")
    try:
        plan = collect_import_plan(
            args.source,
            verify_hashes=not args.allow_unknown_hashes,
        )
        result = execute_import(
            plan,
            output,
            manifest_path=manifest_path,
            dry_run=args.dry_run,
            overwrite=args.overwrite,
        )
    except (OSError, PakError, ImportError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.print_manifest:
        print(manifest_json(plan.manifest), end="")
    action = "Validated" if args.dry_run else "Imported"
    print(
        f"{action} {result['planned']} assets "
        f"({result['written']} written, {result['unchanged']} unchanged)."
    )
    if args.dry_run:
        print("Dry run: no content or manifest files were written.")
    else:
        print(f"Manifest: {Path(manifest_path).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
