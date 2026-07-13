from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest


TOOLS = Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS))

from audit_common import (  # noqa: E402
    AuditError,
    BSP_HEADER,
    BSP_LUMP,
    PAK_ENTRY,
    PAK_HEADER,
    case_collision_groups,
    normalize_runtime_path,
    parse_bsp_entity_lump,
    parse_pak,
    tree_manifest,
)


def make_pak(path: Path, entries: list[tuple[str, bytes]]) -> None:
    payload = bytearray(PAK_HEADER.size)
    directory: list[bytes] = []
    for name, data in entries:
        encoded = name.encode("ascii")
        if len(encoded) > 55:
            raise ValueError("test PAK name is too long")
        offset = len(payload)
        payload.extend(data)
        directory.append(PAK_ENTRY.pack(encoded.ljust(56, b"\0"), offset, len(data)))
    directory_offset = len(payload)
    directory_data = b"".join(directory)
    payload.extend(directory_data)
    PAK_HEADER.pack_into(
        payload, 0, b"PACK", directory_offset, len(directory_data)
    )
    path.write_bytes(payload)


def make_bsp(entity_text: bytes, *, version: int = 38) -> bytes:
    header_size = BSP_HEADER.size + 19 * BSP_LUMP.size
    data = bytearray(header_size)
    BSP_HEADER.pack_into(data, 0, b"IBSP", version)
    BSP_LUMP.pack_into(data, BSP_HEADER.size, header_size, len(entity_text))
    data.extend(entity_text)
    return bytes(data)


class RuntimePathTests(unittest.TestCase):
    def test_normalizes_backslashes_without_changing_case(self) -> None:
        self.assertEqual(normalize_runtime_path(r"Maps\ZBASE1.BSP"), "Maps/ZBASE1.BSP")

    def test_rejects_traversal_absolute_and_drive_paths(self) -> None:
        for value in ("../evil", "maps/../evil", "/maps/a.bsp", r"C:\a.bsp", "a//b"):
            with self.subTest(value=value), self.assertRaises(AuditError):
                normalize_runtime_path(value)

    def test_case_collision_grouping_is_explicit(self) -> None:
        self.assertEqual(
            case_collision_groups(["maps/a.bsp", "Maps/A.BSP", "maps/b.bsp"]),
            [["Maps/A.BSP", "maps/a.bsp"]],
        )


class PakTests(unittest.TestCase):
    def test_parses_and_hashes_valid_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "test.pak"
            make_pak(path, [("maps/a.bsp", b"abc"), ("sound/a.wav", b"xyz")])
            archive = parse_pak(path)
            self.assertEqual([entry.runtime_path for entry in archive.entries], ["maps/a.bsp", "sound/a.wav"])
            self.assertEqual(archive.entries[0].sha256, hashlib.sha256(b"abc").hexdigest())
            self.assertEqual(archive.read_entry(archive.entries[1]), b"xyz")

    def test_rejects_traversal_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "unsafe.pak"
            make_pak(path, [("../outside", b"data")])
            with self.assertRaises(AuditError):
                parse_pak(path)

    def test_rejects_out_of_bounds_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.pak"
            make_pak(path, [("maps/a.bsp", b"data")])
            data = bytearray(path.read_bytes())
            _, directory_offset, _ = PAK_HEADER.unpack_from(data, 0)
            name, _, _ = PAK_ENTRY.unpack_from(data, directory_offset)
            PAK_ENTRY.pack_into(data, directory_offset, name, len(data) - 1, 100)
            path.write_bytes(data)
            with self.assertRaises(AuditError):
                parse_pak(path)

    def test_rejects_duplicate_exact_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.pak"
            make_pak(path, [("a.txt", b"1"), ("a.txt", b"2")])
            with self.assertRaises(AuditError):
                parse_pak(path)

    def test_rejects_hidden_bytes_after_name_terminator(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "hidden-name.pak"
            make_pak(path, [("a.txt", b"1")])
            data = bytearray(path.read_bytes())
            _, directory_offset, _ = PAK_HEADER.unpack_from(data, 0)
            raw_name, offset, size = PAK_ENTRY.unpack_from(data, directory_offset)
            poisoned = bytearray(raw_name)
            poisoned[10] = ord("x")
            PAK_ENTRY.pack_into(data, directory_offset, bytes(poisoned), offset, size)
            path.write_bytes(data)
            with self.assertRaises(AuditError):
                parse_pak(path)

            archive = parse_pak(path, allow_nonzero_name_padding=True)
            self.assertEqual([entry.runtime_path for entry in archive.entries], ["a.txt"])
            self.assertEqual(archive.read_entry(archive.entries[0]), b"1")


class BspTests(unittest.TestCase):
    def test_parses_entity_pairs_and_comments(self) -> None:
        bsp = make_bsp(
            b'// comment\n{\n"classname" "worldspawn"\n}\n'
            b'{ "classname" "func_timer" "target" "a;b" }\0'
        )
        parsed = parse_bsp_entity_lump(bsp)
        self.assertEqual(parsed.version, 38)
        self.assertEqual(len(parsed.entities), 2)
        self.assertIn(("target", "a;b"), parsed.entities[1])

    def test_rejects_bad_version(self) -> None:
        with self.assertRaises(AuditError):
            parse_bsp_entity_lump(make_bsp(b'{"classname" "worldspawn"}', version=39))

    def test_rejects_out_of_bounds_lump(self) -> None:
        bsp = bytearray(make_bsp(b'{"classname" "worldspawn"}'))
        BSP_LUMP.pack_into(bsp, BSP_HEADER.size, len(bsp) - 2, 10)
        with self.assertRaises(AuditError):
            parse_bsp_entity_lump(bytes(bsp))

    def test_rejects_malformed_entity_text(self) -> None:
        with self.assertRaises(AuditError):
            parse_bsp_entity_lump(make_bsp(b'{ "classname" }'))


class TreeManifestTests(unittest.TestCase):
    def test_manifest_is_independent_of_file_creation_order(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_root = Path(first)
            second_root = Path(second)
            (first_root / "b.txt").write_bytes(b"b")
            (first_root / "a.txt").write_bytes(b"a")
            (second_root / "a.txt").write_bytes(b"a")
            (second_root / "b.txt").write_bytes(b"b")
            first_manifest = tree_manifest(first_root)
            second_manifest = tree_manifest(second_root)
            self.assertEqual(first_manifest, second_manifest)


if __name__ == "__main__":
    unittest.main()
