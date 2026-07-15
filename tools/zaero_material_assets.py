#!/usr/bin/env python3
"""Generate Quake II Rerelease material and glow-map assets for Zaero content."""

from __future__ import annotations

import argparse
import binascii
from collections import Counter, deque
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import struct
import sys
from typing import Callable, Iterable, Mapping, Sequence
import zlib


DEFAULT_MATERIAL_ROOTS = ("textures",)
DEFAULT_GLOW_ROOTS = ("textures", "models")
SUPPORTED_GLOW_EXTENSIONS = {".pcx", ".wal"}
DEFAULT_THRESHOLD = 192
DEFAULT_GAMMA = 1.35
DEFAULT_GROW_RANGE = 28
DEFAULT_SATURATION_REDUCTION = 20.0
COLORMAP_PATH = "pics/colormap.pcx"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
WAL_HEADER_SIZE = 56
PCX_HEADER_SIZE = 128
PCX_PALETTE_MARKER = 12
TOOL_TEXTURE_STEMS = frozenset({"clip", "clip_mon", "trigger", "hint", "origin", "skip"})
CON_PREFIX_RE = re.compile(r"^con\d")


class AssetGenerationError(ValueError):
    """Raised when a source image or destination path is invalid."""


@dataclass(frozen=True)
class GeneratedAsset:
    path: str
    data: bytes
    kind: str
    source_path: str
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def size(self) -> int:
        return len(self.data)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()


@dataclass(frozen=True)
class ImageData:
    width: int
    height: int
    pixels: tuple[tuple[int, int, int], ...]


@dataclass
class MaterialStats:
    scanned: int = 0
    matched: int = 0
    created: int = 0
    overwritten: int = 0
    kept: int = 0
    skipped_unmatched: int = 0
    per_material: Counter[str] = field(default_factory=Counter)


@dataclass
class GlowStats:
    scanned: int = 0
    generated: int = 0
    overwritten: int = 0
    kept: int = 0
    skipped_dark: int = 0
    deleted_stale: int = 0


def contains_any(text: str, keywords: Sequence[str]) -> bool:
    return any(keyword in text for keyword in keywords)


EXACT_STEM_MATERIALS: dict[str, str] = {
    "awater": "splash",
    "brwater": "splash",
    "lava": "splash",
    "redfield": "energy",
    "yelfield": "energy",
}

RULES: tuple[tuple[str, str, Callable[[str], bool]], ...] = (
    ("splash", "fluids", lambda stem: contains_any(stem, ("water", "lava", "slime", "sewer", "drsew"))),
    (
        "glass",
        "lighting",
        lambda stem: contains_any(stem, ("glass", "wndow", "window", "reflt"))
        or stem.startswith(("light", "lite", "plite", "wstlt")),
    ),
    ("energy", "energy", lambda stem: contains_any(stem, ("field", "force", "shield", "laser", "lzr", "telev"))),
    ("meat", "gore", lambda stem: contains_any(stem, ("gore", "blood", "gib", "meat"))),
    ("flesh", "flesh", lambda stem: contains_any(stem, ("flesh", "skin", "organ", "head"))),
    ("wood", "wood", lambda stem: contains_any(stem, ("crate", "wood", "box"))),
    (
        "mech",
        "mechanical",
        lambda stem: contains_any(
            stem,
            (
                "grate",
                "ggrat",
                "button",
                "butn",
                "switch",
                "lever",
                "console",
                "control",
                "comp",
                "keypad",
                "mach",
                "wire",
                "cable",
                "pipe",
                "turret",
                "door",
                "dr",
            ),
        ),
    ),
    (
        "clank",
        "metal",
        lambda stem: contains_any(
            stem,
            (
                "metal",
                "metl",
                "palmet",
                "c_met",
                "cmet",
                "fmet",
                "mmtl",
                "rmetal",
                "bmetal",
                "wmtal",
                "mtal",
                "plate",
                "plat",
                "pillar",
                "pilr",
                "support",
                "trim",
                "stlt",
                "baselt",
                "belt",
                "roof",
                "slot",
                "wall",
            ),
        ),
    ),
    ("tile", "tile", lambda stem: "tile" in stem),
    ("grass", "foliage", lambda stem: stem.startswith(("grass", "bush", "field")) or "vine" in stem),
    ("step", "stairs", lambda stem: stem.startswith("stair") or "step" in stem),
    (
        "boot",
        "hard-surface",
        lambda stem: contains_any(
            stem,
            (
                "brick",
                "asphalt",
                "dirt",
                "earth",
                "sand",
                "rock",
                "floor",
                "florr",
                "flr",
                "flat",
                "ceil",
                "dump",
                "drag",
                "geo",
                "basic",
                "basemap",
                "wastemap",
            ),
        )
        or CON_PREFIX_RE.match(stem) is not None,
    ),
)


def _normalize_runtime_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    PurePosixPath(normalized)
    return normalized


def _relative_to_root(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _matches_root(path: str, roots: Sequence[str]) -> bool:
    folded = path.casefold()
    return any(folded == root.casefold() or folded.startswith(root.casefold().rstrip("/") + "/") for root in roots)


def material_key(stem: str) -> str:
    lowered = stem.casefold()
    if lowered.startswith("+") and len(lowered) >= 3:
        return lowered[2:]
    return lowered


def guess_material(runtime_path: str) -> tuple[str | None, str | None]:
    stem = material_key(PurePosixPath(runtime_path).stem)
    if stem in TOOL_TEXTURE_STEMS or stem == "black" or "sky" in stem:
        return None, None

    exact = EXACT_STEM_MATERIALS.get(stem)
    if exact is not None:
        return exact, "exact"

    for material, source, predicate in RULES:
        if predicate(stem):
            return material, source
    return None, None


def iter_wal_files(source_root: Path, roots: Sequence[str]) -> Iterable[Path]:
    source = Path(source_root)
    for root_name in roots:
        root_path = source.joinpath(*PurePosixPath(root_name).parts)
        if not root_path.is_dir():
            continue
        yield from sorted(
            (path for path in root_path.rglob("*.wal") if path.is_file()),
            key=lambda path: path.relative_to(source).as_posix().casefold(),
        )


def generate_material_files(
    source_root: Path,
    output_root: Path,
    *,
    roots: Sequence[str] = DEFAULT_MATERIAL_ROOTS,
    overwrite: bool = False,
    dry_run: bool = False,
    quiet: bool = False,
) -> MaterialStats:
    source = Path(source_root).resolve()
    output = Path(output_root).resolve()
    stats = MaterialStats()

    for wal_path in iter_wal_files(source, roots):
        stats.scanned += 1
        runtime_path = _relative_to_root(wal_path, source)
        material, reason = guess_material(runtime_path)
        if material is None:
            stats.skipped_unmatched += 1
            if not quiet:
                print(f"skip {runtime_path} (unmatched)")
            continue

        stats.matched += 1
        stats.per_material[material] += 1
        material_relative = str(PurePosixPath(runtime_path).with_suffix(".mat"))
        target = output.joinpath(*PurePosixPath(material_relative).parts)
        existed = target.exists()
        if existed and not overwrite:
            stats.kept += 1
            if not quiet:
                print(f"keep {material_relative} -> {material} [{reason}]")
            continue

        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(material, encoding="ascii")
        if existed:
            stats.overwritten += 1
            verb = "overwrite"
        else:
            stats.created += 1
            verb = "create"
        if not quiet:
            print(f"{verb} {material_relative} -> {material} [{reason}]")

    return stats


def read_pcx_palette(data: bytes, label: str) -> tuple[tuple[int, int, int], ...]:
    if len(data) < PCX_HEADER_SIZE + 769:
        raise AssetGenerationError(f"PCX is too small: {label}")
    if data[0] != 10:
        raise AssetGenerationError(f"PCX has invalid manufacturer byte: {label}")
    if data[-769] != PCX_PALETTE_MARKER:
        raise AssetGenerationError(f"PCX has no 256-color palette: {label}")
    palette = data[-768:]
    return tuple(tuple(palette[index : index + 3]) for index in range(0, 768, 3))


def read_pcx_rgb(data: bytes, label: str) -> ImageData:
    if len(data) < PCX_HEADER_SIZE + 769:
        raise AssetGenerationError(f"PCX is too small: {label}")
    if data[0] != 10 or data[2] != 1 or data[3] != 8:
        raise AssetGenerationError(f"Unsupported PCX format: {label}")

    xmin, ymin, xmax, ymax = struct.unpack_from("<HHHH", data, 4)
    width = xmax - xmin + 1
    height = ymax - ymin + 1
    planes = data[65]
    bytes_per_line = struct.unpack_from("<H", data, 66)[0]
    if planes != 1 or width <= 0 or height <= 0 or bytes_per_line < width:
        raise AssetGenerationError(f"Unsupported PCX dimensions or planes: {label}")

    palette = read_pcx_palette(data, label)
    encoded = data[PCX_HEADER_SIZE:-769]
    expected = height * bytes_per_line
    decoded = bytearray()
    index = 0
    while len(decoded) < expected and index < len(encoded):
        value = encoded[index]
        index += 1
        if value >= 0xC0:
            if index >= len(encoded):
                raise AssetGenerationError(f"PCX RLE run is truncated: {label}")
            count = value & 0x3F
            decoded.extend([encoded[index]] * count)
            index += 1
        else:
            decoded.append(value)
    if len(decoded) < expected:
        raise AssetGenerationError(f"PCX pixel data is truncated: {label}")

    pixels: list[tuple[int, int, int]] = []
    for row in range(height):
        offset = row * bytes_per_line
        for palette_index in decoded[offset : offset + width]:
            pixels.append(palette[palette_index])
    return ImageData(width, height, tuple(pixels))


def read_wal_rgb(data: bytes, palette: Sequence[tuple[int, int, int]], label: str) -> ImageData:
    if len(data) < WAL_HEADER_SIZE:
        raise AssetGenerationError(f"WAL is too small: {label}")
    width, height = struct.unpack_from("<II", data, 32)
    offset0 = struct.unpack_from("<I", data, 40)[0]
    if width <= 0 or height <= 0 or width > 4096 or height > 4096:
        raise AssetGenerationError(f"WAL has unsupported dimensions: {label}")
    pixel_count = width * height
    pixel_bytes = data[offset0 : offset0 + pixel_count]
    if len(pixel_bytes) != pixel_count:
        raise AssetGenerationError(f"WAL pixel data is truncated: {label}")
    return ImageData(width, height, tuple(palette[index] for index in pixel_bytes))


def load_rgb_image(
    runtime_path: str,
    data: bytes,
    palette: Sequence[tuple[int, int, int]],
) -> ImageData:
    suffix = PurePosixPath(runtime_path).suffix.casefold()
    if suffix == ".wal":
        return read_wal_rgb(data, palette, runtime_path)
    if suffix == ".pcx":
        return read_pcx_rgb(data, runtime_path)
    raise AssetGenerationError(f"Unsupported glow source extension: {runtime_path}")


def compute_saturation(red: int, green: int, blue: int) -> float:
    value = max(red, green, blue)
    if value == 0:
        return 0.0
    return (value - min(red, green, blue)) / value


def build_glow_rgba(
    image: ImageData,
    *,
    threshold: int = DEFAULT_THRESHOLD,
    gamma: float = DEFAULT_GAMMA,
    grow_range: int = DEFAULT_GROW_RANGE,
    saturation_reduction: float = DEFAULT_SATURATION_REDUCTION,
) -> tuple[bytes, int] | None:
    width = image.width
    height = image.height
    pixel_count = width * height
    luminances = [0.0] * pixel_count
    candidate_thresholds = [0.0] * pixel_count
    seed_pixels = [False] * pixel_count
    candidate_pixels = [False] * pixel_count
    included_pixels = [False] * pixel_count

    for index, (red, green, blue) in enumerate(image.pixels):
        luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
        saturation = compute_saturation(red, green, blue)
        local_seed_threshold = max(0.0, threshold - (saturation * saturation_reduction))
        local_candidate_threshold = max(0.0, local_seed_threshold - grow_range)
        luminances[index] = luminance
        candidate_thresholds[index] = local_candidate_threshold
        seed_pixels[index] = luminance >= local_seed_threshold
        candidate_pixels[index] = luminance >= local_candidate_threshold

    pending: deque[int] = deque(index for index, seed in enumerate(seed_pixels) if seed)
    while pending:
        index = pending.popleft()
        if included_pixels[index] or not candidate_pixels[index]:
            continue
        included_pixels[index] = True
        x = index % width
        y = index // width
        for neighbor_y in range(max(0, y - 1), min(height, y + 2)):
            row_offset = neighbor_y * width
            for neighbor_x in range(max(0, x - 1), min(width, x + 2)):
                neighbor_index = row_offset + neighbor_x
                if neighbor_index != index and candidate_pixels[neighbor_index] and not included_pixels[neighbor_index]:
                    pending.append(neighbor_index)

    rgba = bytearray()
    glowing_pixels = 0
    for index, luminance in enumerate(luminances):
        if not included_pixels[index]:
            rgba.extend((255, 255, 255, 0))
            continue
        local_threshold = candidate_thresholds[index]
        scale_divisor = max(1.0, 255.0 - local_threshold)
        normalized = max(0.0, min(1.0, (luminance - local_threshold) / scale_divisor))
        alpha = round((normalized**gamma) * 255)
        rgba.extend((255, 255, 255, alpha))
        glowing_pixels += 1

    if glowing_pixels == 0:
        return None
    return bytes(rgba), glowing_pixels


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = binascii.crc32(chunk_type)
    crc = binascii.crc32(data, crc) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


def encode_png_rgba(width: int, height: int, rgba: bytes) -> bytes:
    if len(rgba) != width * height * 4:
        raise AssetGenerationError("RGBA data length does not match image dimensions")
    rows = []
    stride = width * 4
    for y in range(height):
        rows.append(b"\0" + rgba[y * stride : (y + 1) * stride])
    raw = b"".join(rows)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        PNG_SIGNATURE
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(raw, 9))
        + _png_chunk(b"IEND", b"")
    )


def is_glow_source_path(runtime_path: str, roots: Sequence[str] = DEFAULT_GLOW_ROOTS) -> bool:
    normalized = _normalize_runtime_path(runtime_path)
    suffix = PurePosixPath(normalized).suffix.casefold()
    stem = PurePosixPath(normalized).stem.casefold()
    if suffix not in SUPPORTED_GLOW_EXTENSIONS:
        return False
    if stem.endswith("_glow"):
        return False
    return _matches_root(normalized, roots)


def glow_path_for_source(runtime_path: str) -> str:
    source = PurePosixPath(_normalize_runtime_path(runtime_path))
    return source.with_name(f"{source.stem}_glow.png").as_posix()


def generate_glow_assets(
    asset_bytes: Mapping[str, bytes],
    *,
    roots: Sequence[str] = DEFAULT_GLOW_ROOTS,
    threshold: int = DEFAULT_THRESHOLD,
    gamma: float = DEFAULT_GAMMA,
    grow_range: int = DEFAULT_GROW_RANGE,
    saturation_reduction: float = DEFAULT_SATURATION_REDUCTION,
) -> tuple[list[GeneratedAsset], GlowStats]:
    stats = GlowStats()
    candidates = sorted(
        (path for path in asset_bytes if is_glow_source_path(path, roots)),
        key=lambda path: (path.casefold(), path),
    )
    if not candidates:
        return [], stats

    palette_source = next((path for path in asset_bytes if path.casefold() == COLORMAP_PATH), None)
    if palette_source is None:
        raise AssetGenerationError(f"Cannot generate glow maps without {COLORMAP_PATH}")
    palette = read_pcx_palette(asset_bytes[palette_source], palette_source)

    generated: list[GeneratedAsset] = []
    seen: set[str] = set()
    for source_path in candidates:
        stats.scanned += 1
        image = load_rgb_image(source_path, asset_bytes[source_path], palette)
        glow = build_glow_rgba(
            image,
            threshold=threshold,
            gamma=gamma,
            grow_range=grow_range,
            saturation_reduction=saturation_reduction,
        )
        if glow is None:
            stats.skipped_dark += 1
            continue

        rgba, glowing_pixels = glow
        glow_path = glow_path_for_source(source_path)
        folded = glow_path.casefold()
        if folded in seen or folded in (path.casefold() for path in asset_bytes):
            raise AssetGenerationError(f"Generated glow path collides with existing content: {glow_path}")
        seen.add(folded)
        png = encode_png_rgba(image.width, image.height, rgba)
        generated.append(
            GeneratedAsset(
                path=glow_path,
                data=png,
                kind="glowmap",
                source_path=source_path,
                metadata={
                    "width": image.width,
                    "height": image.height,
                    "glowing_pixels": glowing_pixels,
                    "threshold": threshold,
                    "gamma": gamma,
                    "grow_range": grow_range,
                    "saturation_reduction": saturation_reduction,
                },
            )
        )
        stats.generated += 1

    return generated, stats


def collect_glow_source_bytes(
    source_root: Path,
    *,
    roots: Sequence[str] = DEFAULT_GLOW_ROOTS,
) -> dict[str, bytes]:
    source = Path(source_root).resolve()
    if not source.is_dir():
        raise AssetGenerationError(f"Source root does not exist: {source}")
    result: dict[str, bytes] = {}
    colormap = source.joinpath(*PurePosixPath(COLORMAP_PATH).parts)
    if colormap.is_file():
        result[COLORMAP_PATH] = colormap.read_bytes()
    for root_name in roots:
        root_path = source.joinpath(*PurePosixPath(root_name).parts)
        if not root_path.is_dir():
            continue
        for path in sorted(root_path.rglob("*")):
            if not path.is_file():
                continue
            runtime_path = _relative_to_root(path, source)
            if is_glow_source_path(runtime_path, roots):
                result[runtime_path] = path.read_bytes()
    return result


def _asset_manifest_entry(asset: GeneratedAsset) -> dict[str, object]:
    return {
        "path": asset.path,
        "size": asset.size,
        "sha256": asset.sha256,
        "source": f"generated:{asset.kind}:{asset.source_path}",
    }


def _generated_manifest_entry(asset: GeneratedAsset) -> dict[str, object]:
    return {
        "path": asset.path,
        "source_path": asset.source_path,
        "kind": asset.kind,
        "size": asset.size,
        "sha256": asset.sha256,
        **asset.metadata,
    }


def merge_generated_assets_into_manifest(
    manifest: Mapping[str, object],
    generated_assets: Sequence[GeneratedAsset],
) -> dict[str, object]:
    merged = json.loads(json.dumps(manifest))
    existing_assets = merged.get("assets")
    if not isinstance(existing_assets, list):
        raise AssetGenerationError("Manifest 'assets' must be a list")
    retained_assets = [
        item
        for item in existing_assets
        if not (
            isinstance(item, dict)
            and isinstance(item.get("source"), str)
            and item["source"].startswith("generated:glowmap:")
        )
    ]
    retained_assets.extend(_asset_manifest_entry(asset) for asset in generated_assets)
    retained_assets.sort(key=lambda item: (str(item["path"]).casefold(), str(item["path"])))
    merged["assets"] = retained_assets

    retained_generated = [
        item
        for item in merged.get("generated_assets", [])
        if not (isinstance(item, dict) and item.get("kind") == "glowmap")
    ]
    retained_generated.extend(_generated_manifest_entry(asset) for asset in generated_assets)
    retained_generated.sort(key=lambda item: (str(item["path"]).casefold(), str(item["path"])))
    if retained_generated:
        merged["generated_assets"] = retained_generated
    elif "generated_assets" in merged:
        del merged["generated_assets"]
    return merged


def write_glow_assets(
    output_root: Path,
    generated_assets: Sequence[GeneratedAsset],
    *,
    overwrite: bool = False,
    dry_run: bool = False,
    quiet: bool = False,
) -> GlowStats:
    output = Path(output_root).resolve()
    stats = GlowStats(scanned=len(generated_assets))
    for asset in generated_assets:
        target = output.joinpath(*PurePosixPath(asset.path).parts)
        existed = target.exists()
        if existed and not overwrite:
            if not target.is_file() or target.read_bytes() != asset.data:
                raise AssetGenerationError(f"Existing glow map differs; pass --overwrite: {asset.path}")
            stats.kept += 1
            if not quiet:
                print(f"keep {asset.path}")
            continue
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(asset.data)
        if existed:
            stats.overwritten += 1
            verb = "overwrite"
        else:
            stats.generated += 1
            verb = "create"
        if not quiet:
            print(f"{verb} {asset.path}")
    return stats


def _load_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AssetGenerationError(f"Could not read manifest: {exc}") from exc
    if not isinstance(value, dict):
        raise AssetGenerationError("Manifest root must be an object")
    return value


def _write_json(path: Path, data: Mapping[str, object]) -> None:
    rendered = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    Path(path).write_text(rendered, encoding="utf-8", newline="\n")


def _parse_roots(raw_roots: Sequence[str] | None, defaults: Sequence[str]) -> tuple[str, ...]:
    roots = tuple(raw_roots) if raw_roots else tuple(defaults)
    return tuple(root.replace("\\", "/").strip("/") for root in roots)


def _add_common_glow_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
    parser.add_argument("--gamma", type=float, default=DEFAULT_GAMMA)
    parser.add_argument("--grow-range", type=int, default=DEFAULT_GROW_RANGE)
    parser.add_argument("--saturation-reduction", type=float, default=DEFAULT_SATURATION_REDUCTION)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    mats = subcommands.add_parser("generate-mats", help="Generate .mat files from imported Zaero WAL names")
    mats.add_argument("--source-root", type=Path, required=True)
    mats.add_argument("--output-root", type=Path, default=Path("pack"))
    mats.add_argument("--root", dest="roots", action="append", help="Runtime root to scan, default: textures")
    mats.add_argument("--overwrite", action="store_true")
    mats.add_argument("--dry-run", action="store_true")
    mats.add_argument("--quiet", action="store_true")

    glow = subcommands.add_parser("generate-glow", help="Generate local-private _glow.png files")
    glow.add_argument("--source-root", type=Path, required=True)
    glow.add_argument("--output-root", type=Path)
    glow.add_argument("--manifest", type=Path)
    glow.add_argument("--root", dest="roots", action="append", help="Runtime root to scan, default: textures and models")
    glow.add_argument("--overwrite", action="store_true")
    glow.add_argument("--dry-run", action="store_true")
    glow.add_argument("--quiet", action="store_true")
    _add_common_glow_args(glow)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.command == "generate-mats":
            stats = generate_material_files(
                args.source_root,
                args.output_root,
                roots=_parse_roots(args.roots, DEFAULT_MATERIAL_ROOTS),
                overwrite=args.overwrite,
                dry_run=args.dry_run,
                quiet=args.quiet,
            )
            print(
                "Material summary: "
                f"scanned={stats.scanned} matched={stats.matched} "
                f"created={stats.created} overwritten={stats.overwritten} "
                f"kept={stats.kept} skipped_unmatched={stats.skipped_unmatched}"
            )
            if stats.per_material:
                totals = ", ".join(
                    f"{material}={count}"
                    for material, count in sorted(stats.per_material.items(), key=lambda item: (-item[1], item[0]))
                )
                print(f"Material totals: {totals}")
            return 0

        roots = _parse_roots(args.roots, DEFAULT_GLOW_ROOTS)
        source_bytes = collect_glow_source_bytes(args.source_root, roots=roots)
        generated, generation_stats = generate_glow_assets(
            source_bytes,
            roots=roots,
            threshold=args.threshold,
            gamma=args.gamma,
            grow_range=args.grow_range,
            saturation_reduction=args.saturation_reduction,
        )
        output_root = args.output_root or args.source_root
        write_stats = write_glow_assets(
            output_root,
            generated,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
            quiet=args.quiet,
        )
        if args.manifest and not args.dry_run:
            manifest = _load_json(args.manifest)
            _write_json(args.manifest, merge_generated_assets_into_manifest(manifest, generated))
        print(
            "Glow summary: "
            f"scanned={generation_stats.scanned} generated={write_stats.generated} "
            f"overwritten={write_stats.overwritten} kept={write_stats.kept} "
            f"skipped_dark={generation_stats.skipped_dark}"
        )
        return 0
    except (OSError, AssetGenerationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
