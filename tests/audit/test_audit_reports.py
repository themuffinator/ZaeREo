from __future__ import annotations

import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest


TOOLS = Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS))

from audit_assets import build_asset_report  # noqa: E402
from audit_bsp_entities import build_bsp_report  # noqa: E402
from audit_common import AuditError, BSP_HEADER, BSP_LUMP, PAK_ENTRY, PAK_HEADER, stable_json_text  # noqa: E402
from audit_source_delta import (  # noqa: E402
    build_baselines,
    build_source_delta,
    extract_c_functions,
    extract_c_globals,
)


def make_pak(path: Path, entries: list[tuple[str, bytes]]) -> None:
    payload = bytearray(PAK_HEADER.size)
    directory: list[bytes] = []
    for name, data in entries:
        encoded = name.encode("ascii")
        offset = len(payload)
        payload.extend(data)
        directory.append(PAK_ENTRY.pack(encoded.ljust(56, b"\0"), offset, len(data)))
    directory_offset = len(payload)
    packed_directory = b"".join(directory)
    payload.extend(packed_directory)
    PAK_HEADER.pack_into(payload, 0, b"PACK", directory_offset, len(packed_directory))
    path.write_bytes(payload)


def make_bsp(entities: list[list[tuple[str, str]]]) -> bytes:
    text = bytearray()
    for entity in entities:
        text.extend(b"{\n")
        for key, value in entity:
            text.extend(f'"{key}" "{value}"\n'.encode("latin-1"))
        text.extend(b"}\n")
    text.extend(b"\0")
    header_size = BSP_HEADER.size + 19 * BSP_LUMP.size
    data = bytearray(header_size)
    BSP_HEADER.pack_into(data, 0, b"IBSP", 38)
    BSP_LUMP.pack_into(data, BSP_HEADER.size, header_size, len(text))
    data.extend(text)
    return bytes(data)


class AssetReportTests(unittest.TestCase):
    def test_layering_and_loose_classification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "sprites").mkdir()
            (root / "sprites" / "flare.sp2").write_bytes(b"sprite")
            (root / "readme.txt").write_text("docs", encoding="utf-8")
            pak0 = root / "pak0.pak"
            pak1 = root / "pak1.pak"
            make_pak(pak0, [("default.cfg", b"old"), ("maps/a.bsp", b"a")])
            make_pak(pak1, [("default.cfg", b"new"), ("maps/b.bsp", b"b")])

            report = build_asset_report(root, [pak0, pak1])
            self.assertEqual(report["summary"]["pak_entry_count"], 4)
            self.assertEqual(report["summary"]["effective_pak_path_count"], 3)
            self.assertEqual(report["summary"]["pak_override_path_count"], 1)
            self.assertEqual(report["summary"]["loose_runtime_file_count"], 1)
            self.assertEqual(report["summary"]["loose_install_file_count"], 1)
            self.assertEqual(report["overrides"][0]["path"], "default.cfg")
            self.assertEqual(report["warnings"], [])
            self.assertEqual(stable_json_text(report), stable_json_text(report))

    def test_checked_in_legacy_override_winners_are_exact(self) -> None:
        root = Path(__file__).resolve().parents[2]
        report = json.loads(
            (root / "docs" / "audits" / "assets.json").read_text(encoding="utf-8")
        )
        overrides = {item["path"]: item["layers"] for item in report["overrides"]}
        self.assertEqual(
            overrides["default.cfg"],
            [
                {
                    "container": "pak0.pak",
                    "sha256": "b5ce2b12d5c77bca7dfe74e07d1a92a626f7d9a79de91e1942007da80a23c0da",
                    "size": 4085,
                },
                {
                    "container": "pak1.pak",
                    "sha256": "eabf975c709a60e59c7bb193959ef77a26d250f0ffe6223173071455803188f8",
                    "size": 4855,
                },
            ],
        )
        self.assertEqual(
            overrides["maps.lst"],
            [
                {
                    "container": "pak0.pak",
                    "sha256": "822fca8467b6d03c55d808cfd8038efc5bc94d4c400550070faed2e758e8a4e2",
                    "size": 368,
                },
                {
                    "container": "pak2.pak",
                    "sha256": "349da628983acd3d22a8bbbb307df075c4b17f32f1d32f41555b156ad6d9b77e",
                    "size": 491,
                },
            ],
        )
        effective = {item["path"]: item for item in report["effective_pak_entries"]}
        self.assertEqual(effective["default.cfg"], overrides["default.cfg"][-1] | {"path": "default.cfg"})
        self.assertEqual(effective["maps.lst"], overrides["maps.lst"][-1] | {"path": "maps.lst"})


class BspReportTests(unittest.TestCase):
    def test_counts_maps_entities_starts_and_registry_gap(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            assets = base / "assets"
            rerelease = base / "rerelease"
            assets.mkdir()
            rerelease.mkdir()
            (rerelease / "g_spawn.cpp").write_text(
                'static x = { { "worldspawn", SP_worldspawn }, '
                '{ "info_player_coop", SP_info_player_coop }, '
                '{ "info_player_deathmatch", SP_info_player_deathmatch } };',
                encoding="utf-8",
            )
            (rerelease / "g_items.cpp").write_text(
                '/* classname */ "item_health"', encoding="utf-8"
            )
            campaign = make_bsp(
                [
                    [("classname", "worldspawn")],
                    [("classname", "info_player_coop")],
                    [("classname", "info_player_deathmatch")],
                    [("classname", "custom_thing"), ("spawnflags2", "1")],
                    [("classname", "func_timer"), ("target", "a;b")],
                ]
            )
            deathmatch = make_bsp(
                [
                    [("classname", "worldspawn")],
                    [("classname", "info_player_deathmatch")],
                    [("classname", "info_player_deathmatch")],
                ]
            )
            pak0 = assets / "pak0.pak"
            make_pak(
                pak0,
                [("maps/campaign.bsp", campaign), ("maps/zdm1.bsp", deathmatch)],
            )

            report = build_bsp_report(assets, [pak0], rerelease)
            self.assertEqual(report["summary"]["map_count"], 2)
            self.assertEqual(report["summary"]["campaign_map_count"], 1)
            self.assertEqual(report["summary"]["deathmatch_map_count"], 1)
            self.assertEqual(report["summary"]["entity_count"], 8)
            self.assertEqual(report["summary"]["coop_start_count"], 1)
            self.assertEqual(report["summary"]["deathmatch_start_count"], 3)
            self.assertIn("custom_thing", report["rerelease_registry"]["map_classnames_missing"])
            self.assertEqual(
                report["global"]["classname_key_counts"]["custom_thing"],
                {"classname": 1, "spawnflags2": 1},
            )
            self.assertEqual(
                report["global"]["classname_value_counts"]["custom_thing"]["spawnflags2"],
                {"1": 1},
            )
            self.assertEqual(
                report["global"]["semicolon_timer_targets"][0]["target"], "a;b"
            )

    def test_changelevel_activation_and_destination_closure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            assets = base / "assets"
            rerelease = base / "rerelease"
            assets.mkdir()
            rerelease.mkdir()
            (rerelease / "g_spawn.cpp").write_text("", encoding="utf-8")
            (rerelease / "g_items.cpp").write_text("", encoding="utf-8")
            hub = make_bsp(
                [
                    [("classname", "worldspawn")],
                    [
                        ("classname", "trigger_multiple"),
                        ("target", "exit"),
                    ],
                    [
                        ("classname", "target_changelevel"),
                        ("targetname", "exit"),
                        ("map", "*other$start"),
                    ],
                    [
                        ("classname", "target_changelevel"),
                        ("targetname", "orphan"),
                        ("map", "absent"),
                    ],
                ]
            )
            other = make_bsp([[("classname", "worldspawn")]])
            pak0 = assets / "pak0.pak"
            make_pak(
                pak0,
                [("maps/hub.bsp", hub), ("maps/other.bsp", other)],
            )

            report = build_bsp_report(assets, [pak0], rerelease)
            self.assertEqual(report["summary"]["target_changelevel_count"], 2)
            self.assertEqual(report["summary"]["orphan_changelevel_count"], 1)
            self.assertEqual(report["summary"]["missing_changelevel_bsp_count"], 1)
            changelevels = report["global"]["changelevels"]
            reachable = next(item for item in changelevels if item["targetname"] == "exit")
            orphan = next(item for item in changelevels if item["targetname"] == "orphan")
            self.assertEqual(reachable["activation_reference_count"], 1)
            self.assertEqual(
                reachable["target_references"],
                [
                    {
                        "activates": True,
                        "classname": "trigger_multiple",
                        "entity_index": 1,
                        "key": "target",
                        "value": "exit",
                    }
                ],
            )
            self.assertEqual(reachable["destination_bsp"], "maps/other.bsp")
            self.assertTrue(reachable["destination_present"])
            self.assertEqual(orphan["activation_reference_count"], 0)
            self.assertEqual(orphan["target_references"], [])
            self.assertEqual(orphan["destination_bsp"], "maps/absent.bsp")
            self.assertFalse(orphan["destination_present"])


class SourceReportTests(unittest.TestCase):
    def test_function_extraction_and_delta(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            legacy = base / "legacy"
            zaero = base / "zaero"
            rerelease = base / "rerelease"
            assets = base / "assets"
            for root in (legacy, zaero, rerelease, assets):
                root.mkdir()
            old = legacy / "game.c"
            new = zaero / "game.c"
            old.write_text(
                "int same(void) { return 1; }\n"
                "int changed(void) { return 1; }\n"
                "int removed(void) { return 3; }\n"
                "int global_same = 1;\n"
                "int global_changed = 1;\n"
                "int global_removed = 1;\n",
                encoding="utf-8",
            )
            new.write_text(
                "int same(void) { return 1; }\n"
                "int changed(void) { return 2; }\n"
                "int added(void) { return 4; }\n"
                "int global_same = 1;\n"
                "int global_changed = 2;\n"
                "int global_added = 1;\n",
                encoding="utf-8",
            )
            (rerelease / "game.cpp").write_text("int api() { return 2023; }\n", encoding="utf-8")
            (assets / "asset.bin").write_bytes(b"asset")
            (zaero / "only.c").write_text("int zaero_only_global = 1;\n", encoding="utf-8")
            (legacy / "old_only.c").write_text("int legacy_only_global = 1;\n", encoding="utf-8")

            functions = extract_c_functions(new)
            self.assertEqual(set(functions), {"same", "changed", "added"})
            self.assertEqual(
                set(extract_c_globals(new)),
                {"global_same", "global_changed", "global_added"},
            )
            report = build_source_delta(zaero, legacy, rerelease)
            record = report["comparison"]["file_records"][0]
            self.assertEqual(record["functions"]["added_count"], 1)
            self.assertEqual(record["functions"]["changed_count"], 1)
            self.assertEqual(record["functions"]["removed_count"], 1)
            self.assertEqual(record["globals"]["added_count"], 1)
            self.assertEqual(record["globals"]["changed_count"], 1)
            self.assertEqual(record["globals"]["removed_count"], 1)
            only_record = next(
                item
                for item in report["comparison"]["file_records"]
                if item["path"] == "only.c"
            )
            self.assertEqual(only_record["globals"]["added_count"], 1)
            removed_only_record = next(
                item
                for item in report["comparison"]["file_records"]
                if item["path"] == "old_only.c"
            )
            self.assertEqual(removed_only_record["globals"]["removed_count"], 1)
            baselines = build_baselines(zaero, legacy, rerelease, assets)
            self.assertEqual(set(baselines["baselines"]), {
                "legacy_quake2_game", "quake2_rerelease", "zaero_install", "zaero_source"
            })
            rerelease_identity = baselines["baselines"]["quake2_rerelease"]
            upstream_match = {
                "baseline": {
                    "key": "quake2_rerelease",
                    "file_count": rerelease_identity["file_count"],
                    "total_size": rerelease_identity["total_size"],
                    "tree_sha256": rerelease_identity["tree_sha256"],
                },
                "repository": {
                    "origin_url": "https://example.invalid/official.git",
                    "subtree": "rerelease",
                },
                "verification": {
                    "verified_on": "2026-07-14",
                    "match_status": "verified-exact-content-match",
                },
                "selected_match": {
                    "commit": "a" * 40,
                    "subtree_tree_oid": "b" * 40,
                },
            }
            enriched = build_baselines(
                zaero,
                legacy,
                rerelease,
                assets,
                rerelease_upstream_match=upstream_match,
            )["baselines"]["quake2_rerelease"]
            self.assertEqual(enriched["origin_status"], "verified-exact-content-match")
            self.assertEqual(enriched["official_git"]["commit"], "a" * 40)

            upstream_match["baseline"]["tree_sha256"] = "0" * 64
            with self.assertRaisesRegex(AuditError, "different baseline"):
                build_baselines(
                    zaero,
                    legacy,
                    rerelease,
                    assets,
                    rerelease_upstream_match=upstream_match,
                )


if __name__ == "__main__":
    unittest.main()
