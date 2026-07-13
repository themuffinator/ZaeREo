from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
import zipfile


TOOLS = Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS))

from make_release_zip import FIXED_TIMESTAMP, ReleaseZipError, build_release_zip  # noqa: E402


class ReleaseZipTests(unittest.TestCase):
    def test_archive_is_sorted_prefixed_and_byte_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage = root / "stage"
            (stage / "nested").mkdir(parents=True)
            (stage / "z.txt").write_text("last", encoding="utf-8")
            (stage / "nested" / "a.bin").write_bytes(b"first")
            first = root / "first.zip"
            second = root / "second.zip"

            digest1 = build_release_zip(stage, first, prefix="zaereo")
            # Source mtimes must not affect output.
            (stage / "z.txt").touch()
            digest2 = build_release_zip(stage, second, prefix="zaereo")
            self.assertEqual(digest1, digest2)
            self.assertEqual(first.read_bytes(), second.read_bytes())

            with zipfile.ZipFile(first) as archive:
                self.assertEqual(
                    archive.namelist(),
                    ["zaereo/nested/a.bin", "zaereo/z.txt"],
                )
                self.assertTrue(all(info.date_time == FIXED_TIMESTAMP for info in archive.infolist()))

    def test_rejects_output_inside_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            stage = Path(temporary)
            (stage / "file").write_bytes(b"x")
            with self.assertRaisesRegex(ReleaseZipError, "must not be inside"):
                build_release_zip(stage, stage / "release.zip")

    def test_rejects_unsafe_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage = root / "stage"
            stage.mkdir()
            (stage / "file").write_bytes(b"x")
            with self.assertRaises(Exception):
                build_release_zip(stage, root / "release.zip", prefix="../escape")


if __name__ == "__main__":
    unittest.main()
