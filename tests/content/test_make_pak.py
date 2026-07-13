from __future__ import annotations

import hashlib
import struct
import sys
import tempfile
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS))

from make_pak import (  # noqa: E402
    PAK_ENTRY,
    PAK_HEADER,
    PAK_MAGIC,
    PakError,
    build_pak,
    read_entry,
    read_pak_index,
)


def write_raw_pak(path: Path, members: list[tuple[str, bytes]]) -> None:
    directory: list[tuple[str, int, int]] = []
    with path.open("wb") as stream:
        stream.write(PAK_HEADER.pack(PAK_MAGIC, 0, 0))
        for name, data in members:
            offset = stream.tell()
            stream.write(data)
            directory.append((name, offset, len(data)))
        directory_offset = stream.tell()
        for name, offset, size in directory:
            encoded = name.encode("ascii")
            stream.write(PAK_ENTRY.pack(encoded.ljust(56, b"\0"), offset, size))
        stream.seek(0)
        stream.write(
            PAK_HEADER.pack(PAK_MAGIC, directory_offset, len(directory) * PAK_ENTRY.size)
        )


class MakePakTests(unittest.TestCase):
    def test_build_is_sorted_and_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            (source / "sound").mkdir(parents=True)
            (source / "z.txt").write_bytes(b"last")
            (source / "A.txt").write_bytes(b"first")
            (source / "sound" / "tone.wav").write_bytes(b"wave")

            first = root / "first.pak"
            second = root / "second.pak"
            build_pak(source, first)
            build_pak(source, second)

            self.assertEqual(first.read_bytes(), second.read_bytes())
            entries = read_pak_index(first)
            self.assertEqual([entry.path for entry in entries], ["A.txt", "sound/tone.wav", "z.txt"])
            self.assertEqual(read_entry(first, entries[1]), b"wave")
            self.assertEqual(
                hashlib.sha256(first.read_bytes()).hexdigest(),
                hashlib.sha256(second.read_bytes()).hexdigest(),
            )

    def test_exclude_patterns_are_case_insensitive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            (source / "keep.cfg").write_text("keep", encoding="ascii")
            (source / "README.MD").write_text("omit", encoding="ascii")
            output = root / "out.pak"
            build_pak(source, output, exclude_patterns=["readme.md"])
            self.assertEqual([entry.path for entry in read_pak_index(output)], ["keep.cfg"])

    def test_rejects_traversal_member(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pak = Path(temporary) / "unsafe.pak"
            write_raw_pak(pak, [("../escape.txt", b"bad")])
            with self.assertRaisesRegex(PakError, "unsafe component"):
                read_pak_index(pak)

    def test_rejects_case_colliding_members(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pak = Path(temporary) / "collision.pak"
            write_raw_pak(pak, [("pics/Icon.pcx", b"a"), ("pics/icon.pcx", b"b")])
            with self.assertRaisesRegex(PakError, "case-colliding"):
                read_pak_index(pak)

    def test_rejects_directory_outside_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pak = Path(temporary) / "truncated.pak"
            pak.write_bytes(PAK_HEADER.pack(PAK_MAGIC, 999, PAK_ENTRY.size))
            with self.assertRaisesRegex(PakError, "extends past"):
                read_pak_index(pak)

    def test_rejects_output_inside_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            source.mkdir()
            (source / "one.txt").write_text("one", encoding="ascii")
            with self.assertRaisesRegex(PakError, "must not be inside"):
                build_pak(source, source / "out.pak")


if __name__ == "__main__":
    unittest.main()
