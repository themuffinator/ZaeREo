from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from audit_common import BSP_HEADER, BSP_LUMP, PAK_ENTRY, PAK_HEADER, parse_bsp_entity_lump
from make_dm_runtime_fixture import (
    AuditError,
    DM_ITEM_CLASSNAMES,
    Q2_BRUSH,
    Q2_BRUSHSIDE,
    Q2_LEAF,
    Q2_MODEL,
    Q2_NODE,
    Q2_PLANE,
    build_existing_member_fixture_bsp,
    build_fixture_bsp,
    main,
)
import make_dm_runtime_fixture as fixture_tool


INSTALLER = (ROOT / "tools" / "install_dev.ps1").read_text(encoding="utf-8")


def make_source_bsp() -> bytes:
    header_size = BSP_HEADER.size + 19 * BSP_LUMP.size
    entity_text = (
        b'{\n"classname" "worldspawn"\n}\n'
        b'{\n"classname" "info_player_deathmatch"\n'
        b'"origin" "128 256 384"\n"angle" "90"\n}\n\0'
    )
    capacity = 1024
    lumps: dict[int, bytes] = {
        0: entity_text + b"\0" * (capacity - len(entity_text)),
        1: Q2_PLANE.pack(1.0, 0.0, 0.0, 0.0, 0),
        4: Q2_NODE.pack(0, -1, -2, -1024, -1024, -1024, 1024, 1024, 1024, 0, 0),
        8: (
            Q2_LEAF.pack(0, -1, 0, -1024, -1024, -1024, 1024, 1024, 1024, 0, 0, 0, 0)
            + Q2_LEAF.pack(1, -1, 0, -1024, -1024, -1024, 1024, 1024, 1024, 0, 0, 0, 0)
        ),
        13: Q2_MODEL.pack(
            -1024.0,
            -1024.0,
            -1024.0,
            1024.0,
            1024.0,
            1024.0,
            0.0,
            0.0,
            0.0,
            0,
            0,
            0,
        ),
        14: Q2_BRUSH.pack(0, 1, 1),
        15: Q2_BRUSHSIDE.pack(0, 0),
    }
    data = bytearray(header_size + sum(len(payload) for payload in lumps.values()))
    BSP_HEADER.pack_into(data, 0, b"IBSP", 38)
    cursor = header_size
    for index in range(19):
        payload = lumps.get(index, b"")
        BSP_LUMP.pack_into(data, BSP_HEADER.size + index * BSP_LUMP.size, cursor, len(payload))
        data[cursor : cursor + len(payload)] = payload
        cursor += len(payload)
    return bytes(data)


def make_pak(member: str, payload: bytes) -> bytes:
    data = bytearray(PAK_HEADER.size)
    entry_offset = len(data)
    data.extend(payload)
    directory_offset = len(data)
    encoded = member.encode("ascii")
    data.extend(PAK_ENTRY.pack(encoded.ljust(56, b"\0"), entry_offset, len(payload)))
    PAK_HEADER.pack_into(data, 0, b"PACK", directory_offset, PAK_ENTRY.size)
    return bytes(data)


class DmRuntimeFixtureTests(unittest.TestCase):
    def test_fixture_replaces_only_entity_lump_and_has_expected_partial_contract(self) -> None:
        source = make_source_bsp()
        fixture, contract = build_fixture_bsp(source)
        self.assertEqual(len(fixture), len(source))
        self.assertEqual(fixture[: BSP_HEADER.size], source[: BSP_HEADER.size])
        parsed = parse_bsp_entity_lump(fixture)
        classnames = [dict(entity).get("classname") for entity in parsed.entities]
        self.assertEqual(classnames.count("worldspawn"), 1)
        self.assertEqual(classnames.count("info_player_deathmatch"), 5)
        self.assertEqual(classnames.count("info_player_start"), 1)
        self.assertEqual(contract["expected_added_count"], 4)
        self.assertEqual(contract["expected_set_indices"], [0, 2, 4, 6])
        self.assertEqual(contract["expected_success_ordinals"], [1, 6, 11, 16])

    def test_each_existing_member_control_contains_only_its_historical_item(self) -> None:
        source = make_source_bsp()
        for item_classname in DM_ITEM_CLASSNAMES:
            fixture, contract = build_existing_member_fixture_bsp(
                source, item_classname
            )
            self.assertEqual(len(fixture), len(source))
            parsed = parse_bsp_entity_lump(fixture)
            classnames = [dict(entity).get("classname") for entity in parsed.entities]
            self.assertEqual(classnames.count("worldspawn"), 1)
            self.assertEqual(classnames.count("info_player_deathmatch"), 1)
            self.assertEqual(classnames.count("info_player_start"), 1)
            self.assertEqual(classnames.count(item_classname), 1)
            self.assertEqual(len(classnames), 4)
            self.assertEqual(contract["existing_member_classname"], item_classname)
            self.assertEqual(contract["expected_added_count"], 0)

        with self.assertRaisesRegex(AuditError, "unsupported DM item classname"):
            build_existing_member_fixture_bsp(source, "item_quad")

    def test_cli_is_deterministic_and_writes_only_below_owned_private_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="zaereo-dm-fixture-") as temporary:
            temporary_path = Path(temporary)
            owned = temporary_path / ".install" / "runtime-fixtures"
            source_pak = temporary_path / "pak0.pak"
            source_pak.write_bytes(make_pak("maps/q2dm1.bsp", make_source_bsp()))
            overlay = owned / "zaereo_fixture_dm_partial"
            manifest = owned / "zaereo_fixture_dm_partial-manifest.json"
            argv = [
                "--source-pak",
                str(source_pak),
                "--fixture-name",
                "zaereo_fixture_dm_partial",
                "--output-root",
                str(overlay),
                "--manifest-output",
                str(manifest),
                "--include-existing-member-controls",
            ]
            with mock.patch.object(fixture_tool, "OWNED_ROOT", owned):
                self.assertEqual(main(argv), 0)
                map_path = overlay / "maps" / "zaereo_fixture_dm_partial.bsp"
                first = map_path.read_bytes()
                first_hash = hashlib.sha256(first).hexdigest()
                self.assertEqual(main(argv), 0)
                self.assertEqual(map_path.read_bytes(), first)
                report = json.loads(manifest.read_text(encoding="utf-8"))
                self.assertEqual(report["publication_status"], "private-local-only")
                self.assertEqual(report["output"]["sha256"], first_hash)
                self.assertEqual(len(report["outputs"]), 9)
                self.assertEqual(len(report["member_controls"]), 8)
                self.assertEqual(
                    [control["existing_member_classname"] for control in report["member_controls"]],
                    list(DM_ITEM_CLASSNAMES),
                )
                self.assertEqual(
                    sorted(path.name for path in (overlay / "maps").glob("*.bsp")),
                    sorted(
                        ["zaereo_fixture_dm_partial.bsp"]
                        + [f"zaereo_fixture_dm_m{index}.bsp" for index in range(8)]
                    ),
                )
                self.assertNotIn(str(temporary_path), manifest.read_text(encoding="utf-8"))

                with self.assertRaisesRegex(AuditError, "must remain below"):
                    main(
                        [
                            "--source-pak",
                            str(source_pak),
                            "--output-root",
                            str(temporary_path / "escape"),
                            "--manifest-output",
                            str(manifest),
                        ]
                    )

    def test_installer_overlay_is_private_path_scoped_and_collision_safe(self) -> None:
        for fragment in (
            '[string]$RuntimeFixtureRoot = ""',
            '".install\\runtime-fixtures"',
            '"runtime fixture root"',
            "^maps/zaereo_fixture_[a-z0-9_]+\\.bsp$",
            "Runtime fixture refuses to replace existing content",
            "Copy-TreeFiles $runtimeFixturePath $fixtureWork",
            '"pak2.pak"',
            "Import/runtime fixture content",
        ):
            self.assertIn(fragment, INSTALLER)


if __name__ == "__main__":
    unittest.main()
