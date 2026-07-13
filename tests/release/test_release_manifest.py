from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


TOOLS = Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS))

from audit_common import stable_json_text  # noqa: E402
from release_manifest import (  # noqa: E402
    ReleaseManifestError,
    create_manifest,
    verify_manifest,
)


class ReleaseManifestTests(unittest.TestCase):
    def test_round_trip_is_deterministic_and_excludes_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "nested").mkdir()
            (root / "nested" / "b").write_bytes(b"b")
            (root / "a").write_bytes(b"a")
            path = root / "MANIFEST.json"
            manifest = create_manifest(
                root,
                path,
                version="0.1.0-dev.0",
                commit="abc",
                distribution_mode="importer-kit",
            )
            path.write_text(stable_json_text(manifest), encoding="utf-8")
            self.assertEqual([entry["path"] for entry in manifest["files"]], ["a", "nested/b"])
            self.assertEqual(verify_manifest(root, path), manifest)

    def test_detects_changed_and_extra_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = root / "payload"
            payload.write_bytes(b"one")
            path = root / "MANIFEST.json"
            manifest = create_manifest(
                root, path, version="1.0.0", commit="abc", distribution_mode="local-full"
            )
            path.write_text(stable_json_text(manifest), encoding="utf-8")
            payload.write_bytes(b"two")
            (root / "extra").write_bytes(b"x")
            with self.assertRaisesRegex(ReleaseManifestError, "differs"):
                verify_manifest(root, path)


if __name__ == "__main__":
    unittest.main()
