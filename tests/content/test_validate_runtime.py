from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS))

from import_legacy_assets import collect_import_plan, execute_import  # noqa: E402
from make_pak import build_pak  # noqa: E402
from tests.content.test_import_legacy_assets import make_synthetic_install  # noqa: E402
from validate_runtime import (  # noqa: E402
    ValidationError,
    _directory_assets,
    _pak_assets,
    load_manifest,
    validate_stage,
    validate_runtime,
)


class ValidateRuntimeTests(unittest.TestCase):
    def _import_fixture(self, root: Path):
        source = root / "install"
        source.mkdir()
        expected = make_synthetic_install(source)
        plan = collect_import_plan(source, expected_hashes=expected)
        output = root / "runtime"
        manifest_path = root / "manifest.json"
        execute_import(plan, output, manifest_path=manifest_path)
        manifest = load_manifest(manifest_path, verify_known_source_hashes=False)
        return output, manifest

    def _stage_fixture(self, root: Path):
        output, manifest = self._import_fixture(root)
        stage = root / "stage"
        stage.mkdir()

        project = root / "project"
        project.mkdir()
        (project / "zaero.cfg").write_text("set game zaereo\n", encoding="ascii")
        build_pak(project, stage / "pak0.pak")

        imported = root / "imported-pak"
        shutil.copytree(output, imported)
        for relative in manifest["required_loose_paths"]:
            source = imported.joinpath(*relative.split("/"))
            source.unlink()
            destination = stage.joinpath(*relative.split("/"))
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(output.joinpath(*relative.split("/")), destination)
        build_pak(imported, stage / "pak1.pak")
        return stage, manifest

    def test_directory_matches_manifest_byte_for_byte(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output, manifest = self._import_fixture(Path(temporary))
            result = validate_runtime(_directory_assets(output), manifest=manifest, strict=True)
            self.assertEqual(result, {"assets": 12, "manifest_verified": 12})

    def test_packaged_runtime_matches_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output, manifest = self._import_fixture(root)
            pak = root / "runtime.pak"
            build_pak(output, pak)
            result = validate_runtime(_pak_assets(pak), manifest=manifest, strict=True)
            self.assertEqual(result["manifest_verified"], 12)

    def test_detects_tampered_asset(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output, manifest = self._import_fixture(Path(temporary))
            (output / "base.dat").write_bytes(b"tampered")
            with self.assertRaisesRegex(ValidationError, "differs from manifest"):
                validate_runtime(_directory_assets(output), manifest=manifest)

    def test_rejects_legacy_state_even_without_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "save").mkdir()
            (root / "save" / "server.ssv").write_bytes(b"legacy")
            with self.assertRaisesRegex(ValidationError, "Forbidden runtime member"):
                validate_runtime(_directory_assets(root))

    def test_strict_manifest_rejects_extra_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output, manifest = self._import_fixture(Path(temporary))
            (output / "extra.txt").write_text("extra", encoding="ascii")
            with self.assertRaisesRegex(ValidationError, "absent from strict manifest"):
                validate_runtime(_directory_assets(output), manifest=manifest, strict=True)

    def test_stage_preserves_project_import_and_loose_ownership(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            stage, manifest = self._stage_fixture(Path(temporary))
            self.assertEqual(
                validate_stage(stage, manifest=manifest),
                {
                    "project_assets": 1,
                    "imported_assets": 12,
                    "generated_assets": 0,
                    "manifest_verified": 12,
                },
            )

    def test_stage_rejects_project_import_path_collision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage, manifest = self._stage_fixture(root)
            project = root / "colliding-project"
            project.mkdir()
            (project / "base.dat").write_bytes(b"project override")
            build_pak(project, stage / "pak0.pak")
            with self.assertRaisesRegex(ValidationError, "ownership collision"):
                validate_stage(stage, manifest=manifest)

    def test_stage_rejects_project_import_file_directory_collision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage, manifest = self._stage_fixture(root)
            project = root / "file-project"
            project.mkdir()
            (project / "base.dat").write_bytes(b"project directory blocker")
            build_pak(project, stage / "pak0.pak")
            imported = root / "file-import"
            (imported / "base.dat").mkdir(parents=True)
            (imported / "base.dat" / "child.bin").write_bytes(b"imported child")
            build_pak(imported, stage / "pak1.pak")
            for relative in manifest["required_loose_paths"]:
                destination = stage.joinpath(*relative.split("/"))
                self.assertTrue(destination.is_file())
            with self.assertRaisesRegex(ValidationError, "file/directory ownership collision"):
                validate_stage(stage, manifest=manifest)

    def test_stage_rejects_imported_loose_member_collision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage, manifest = self._stage_fixture(root)
            imported = root / "colliding-import"
            imported.mkdir()
            loose_path = manifest["required_loose_paths"][0]
            imported.joinpath(*loose_path.split("/")).parent.mkdir(parents=True, exist_ok=True)
            imported.joinpath(*loose_path.split("/")).write_bytes(b"wrong place")
            build_pak(imported, stage / "pak1.pak")
            with self.assertRaisesRegex(ValidationError, "ownership collision"):
                validate_stage(stage, manifest=manifest)

    def test_stage_allows_noncolliding_private_generated_fixture_layer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage, manifest = self._stage_fixture(root)
            fixture = root / "fixture"
            (fixture / "maps").mkdir(parents=True)
            (fixture / "maps" / "zaereo_fixture_dm_partial.bsp").write_bytes(b"fixture")
            build_pak(fixture, stage / "pak2.pak")
            self.assertEqual(validate_stage(stage, manifest=manifest)["generated_assets"], 1)


if __name__ == "__main__":
    unittest.main()
