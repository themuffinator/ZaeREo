from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
