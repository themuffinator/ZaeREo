from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS))

from import_legacy_assets import PAK_LAYERS, REQUIRED_LOOSE_PATHS, collect_import_plan, execute_import  # noqa: E402
from make_pak import build_pak, sha256_file  # noqa: E402
from zaero_material_assets import (  # noqa: E402
    PNG_SIGNATURE,
    generate_glow_assets,
    generate_material_files,
)


def make_palette() -> list[tuple[int, int, int]]:
    palette = [(0, 0, 0)] * 256
    palette[1] = (255, 255, 255)
    palette[2] = (64, 64, 64)
    palette[3] = (255, 0, 0)
    return palette


def encode_pcx(width: int, height: int, pixels: list[int], palette: list[tuple[int, int, int]]) -> bytes:
    if len(pixels) != width * height:
        raise AssertionError("pixel count mismatch")
    header = bytearray(128)
    header[0] = 10
    header[1] = 5
    header[2] = 1
    header[3] = 8
    struct.pack_into("<HHHH", header, 4, 0, 0, width - 1, height - 1)
    struct.pack_into("<HH", header, 12, width, height)
    header[65] = 1
    struct.pack_into("<H", header, 66, width)
    struct.pack_into("<H", header, 68, 1)

    encoded = bytearray()
    for value in pixels:
        if value >= 0xC0:
            encoded.extend((0xC1, value))
        else:
            encoded.append(value)

    palette_bytes = bytearray()
    for red, green, blue in palette:
        palette_bytes.extend((red, green, blue))
    return bytes(header + encoded + bytes([12]) + palette_bytes)


def encode_wal(width: int, height: int, pixels: list[int]) -> bytes:
    if len(pixels) != width * height:
        raise AssertionError("pixel count mismatch")
    header = bytearray(56)
    header[:8] = b"testwal\0"
    struct.pack_into("<II", header, 32, width, height)
    struct.pack_into("<IIII", header, 40, 56, 56 + len(pixels), 56 + len(pixels), 56 + len(pixels))
    return bytes(header) + bytes(pixels)


class ZaeroMaterialAssetTests(unittest.TestCase):
    def test_material_files_are_generated_from_texture_names(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            output = root / "pack"
            for relative in (
                "textures/z2/metal1_1.wal",
                "textures/z2/water8.wal",
                "textures/z2/clip.wal",
            ):
                path = source.joinpath(*relative.split("/"))
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"placeholder")

            stats = generate_material_files(source, output, quiet=True)

            self.assertEqual(stats.scanned, 3)
            self.assertEqual(stats.matched, 2)
            self.assertEqual((output / "textures" / "z2" / "metal1_1.mat").read_text(encoding="ascii"), "clank")
            self.assertEqual((output / "textures" / "z2" / "water8.mat").read_text(encoding="ascii"), "splash")
            self.assertFalse((output / "textures" / "z2" / "clip.mat").exists())

    def test_glow_assets_are_generated_as_pngs_from_wal_and_pcx(self) -> None:
        palette = make_palette()
        assets = {
            "pics/colormap.pcx": encode_pcx(1, 1, [0], palette),
            "textures/z1/light_01.wal": encode_wal(2, 1, [1, 2]),
            "models/weapons/v_test/skin.pcx": encode_pcx(2, 1, [1, 2], palette),
            "textures/z1/dark.wal": encode_wal(1, 1, [2]),
        }

        generated, stats = generate_glow_assets(assets)

        by_path = {asset.path: asset for asset in generated}
        self.assertEqual(stats.scanned, 3)
        self.assertEqual(stats.skipped_dark, 1)
        self.assertEqual(set(by_path), {
            "models/weapons/v_test/skin_glow.png",
            "textures/z1/light_01_glow.png",
        })
        self.assertTrue(by_path["textures/z1/light_01_glow.png"].data.startswith(PNG_SIGNATURE))
        self.assertEqual(by_path["models/weapons/v_test/skin_glow.png"].metadata["glowing_pixels"], 1)

    def test_import_plan_includes_generated_glow_assets_in_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "install"
            source.mkdir()
            palette = make_palette()

            layer0 = root / "layer0"
            (layer0 / "pics").mkdir(parents=True)
            (layer0 / "textures" / "z1").mkdir(parents=True)
            (layer0 / "pics" / "colormap.pcx").write_bytes(encode_pcx(1, 1, [0], palette))
            (layer0 / "textures" / "z1" / "light_01.wal").write_bytes(encode_wal(2, 1, [1, 2]))
            build_pak(layer0, source / PAK_LAYERS[0])
            for index in (1, 2):
                empty = root / f"layer{index}"
                empty.mkdir()
                build_pak(empty, source / PAK_LAYERS[index])
            for relative in REQUIRED_LOOSE_PATHS:
                path = source.joinpath(*relative.split("/"))
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(f"loose:{relative}".encode("ascii"))

            expected = {name: sha256_file(source / name) for name in PAK_LAYERS}
            plan = collect_import_plan(source, expected_hashes=expected)
            output = root / "runtime"
            manifest_path = root / "manifest.json"
            execute_import(plan, output, manifest_path=manifest_path)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertTrue((output / "textures" / "z1" / "light_01_glow.png").is_file())
            glow_entry = next(
                item for item in manifest["assets"] if item["path"] == "textures/z1/light_01_glow.png"
            )
            self.assertEqual(glow_entry["source"], "generated:glowmap:textures/z1/light_01.wal")
            self.assertEqual(manifest["generated_assets"][0]["kind"], "glowmap")


if __name__ == "__main__":
    unittest.main()
