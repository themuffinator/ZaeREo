from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS))

from import_legacy_assets import (  # noqa: E402
    PAK_LAYERS,
    REQUIRED_LOOSE_PATHS,
    ImportError as AssetImportError,
    collect_import_plan,
    execute_import,
)
from make_pak import build_pak, sha256_file  # noqa: E402


def make_synthetic_install(root: Path) -> dict[str, str]:
    layers = [
        {
            "base.dat": b"zero",
            "sound/common.wav": b"common",
            "default.cfg": b"unbindall",
            "demos/legacy.dm2": b"demo",
            "save/save0/server.ssv": b"save",
            "screenshots/shot.pcx": b"shot",
            "scrnshot/quake00.tga": b"shot",
            "gamex86.dll": b"binary",
        },
        {"base.dat": b"one", "autoexec.cfg": b"legacy config"},
        {"base.dat": b"two", "maps/zdm1.bsp": b"map"},
    ]
    for index, members in enumerate(layers):
        source = root / f"layer{index}"
        for relative, data in members.items():
            path = source.joinpath(*relative.split("/"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        build_pak(source, root / PAK_LAYERS[index])
    for relative in REQUIRED_LOOSE_PATHS:
        path = root.joinpath(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"loose:{relative}".encode("ascii"))
    return {name: sha256_file(root / name) for name in PAK_LAYERS}


class ImportLegacyAssetsTests(unittest.TestCase):
    def test_three_layer_last_wins_and_exclusions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "install"
            source.mkdir()
            expected = make_synthetic_install(source)
            plan = collect_import_plan(source, expected_hashes=expected)

            by_path = {asset.path: asset for asset in plan.assets}
            self.assertEqual(b"".join(by_path["base.dat"].chunks()), b"two")
            self.assertEqual(len(plan.assets), 12)
            self.assertEqual(
                [(item["replaced_source"], item["winning_source"]) for item in plan.manifest["overrides"]],
                [("pak0.pak", "pak1.pak"), ("pak1.pak", "pak2.pak")],
            )
            excluded = {item["path"] for item in plan.manifest["excluded"]}
            self.assertTrue(
                {
                    "default.cfg",
                    "autoexec.cfg",
                    "demos/legacy.dm2",
                    "save/save0/server.ssv",
                    "screenshots/shot.pcx",
                    "scrnshot/quake00.tga",
                    "gamex86.dll",
                }.issubset(excluded)
            )

    def test_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "install"
            source.mkdir()
            expected = make_synthetic_install(source)
            plan = collect_import_plan(source, expected_hashes=expected)
            output = root / "runtime"
            manifest = root / "manifest.json"
            result = execute_import(
                plan, output, manifest_path=manifest, dry_run=True, overwrite=False
            )
            self.assertEqual(result, {"planned": 12, "written": 0, "unchanged": 0})
            self.assertFalse(output.exists())
            self.assertFalse(manifest.exists())

    def test_import_is_verified_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "install"
            source.mkdir()
            expected = make_synthetic_install(source)
            plan = collect_import_plan(source, expected_hashes=expected)
            output = root / "runtime"
            manifest = root / "manifest.json"

            first = execute_import(plan, output, manifest_path=manifest)
            second = execute_import(plan, output, manifest_path=manifest)
            self.assertEqual(first["written"], 12)
            self.assertEqual(second["unchanged"], 12)
            self.assertEqual((output / "base.dat").read_bytes(), b"two")
            self.assertFalse((output / "default.cfg").exists())
            self.assertEqual(json.loads(manifest.read_text(encoding="utf-8")), plan.manifest)

    def test_refuses_modified_destination_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "install"
            source.mkdir()
            expected = make_synthetic_install(source)
            plan = collect_import_plan(source, expected_hashes=expected)
            output = root / "runtime"
            execute_import(plan, output)
            (output / "base.dat").write_bytes(b"local edit")
            with self.assertRaisesRegex(AssetImportError, "--overwrite"):
                execute_import(plan, output)
            execute_import(plan, output, overwrite=True)
            self.assertEqual((output / "base.dat").read_bytes(), b"two")

    def test_requires_every_explicit_loose_asset(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "install"
            source.mkdir()
            expected = make_synthetic_install(source)
            source.joinpath(*REQUIRED_LOOSE_PATHS[-1].split("/")).unlink()
            with self.assertRaisesRegex(AssetImportError, "Required loose"):
                collect_import_plan(source, expected_hashes=expected)

    def test_known_hashes_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "install"
            source.mkdir()
            make_synthetic_install(source)
            with self.assertRaisesRegex(AssetImportError, "Unexpected SHA-256"):
                collect_import_plan(source)


if __name__ == "__main__":
    unittest.main()
