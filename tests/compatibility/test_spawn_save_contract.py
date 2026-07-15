from __future__ import annotations

from pathlib import Path
import re
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from generate_shipped_map_identity import load_records, render  # noqa: E402

LOCAL = (ROOT / "src" / "g_local.h").read_text(encoding="utf-8")
SPAWN = (ROOT / "src" / "g_spawn.cpp").read_text(encoding="utf-8")
SAVE = (ROOT / "src" / "g_save.cpp").read_text(encoding="utf-8")
MAIN = (ROOT / "src" / "g_main.cpp").read_text(encoding="utf-8")
BG = (ROOT / "src" / "bg_local.h").read_text(encoding="utf-8")
MAP_AUDIT = ROOT / "docs" / "audits" / "bsp-entities.json"
MAP_IDENTITY_HEADER = ROOT / "src" / "zaero" / "g_zaero_shipped_map_identity.h"


class ZaeroSpawnSaveContractTests(unittest.TestCase):
    def test_second_spawnflag_namespace_is_typed_and_filtered_exactly(self) -> None:
        for symbol, value in (
            ("ZAERO_SPAWNFLAG2_MIRRORLEVEL", "1u << 0"),
            ("ZAERO_SPAWNFLAG2_NOT_COOP", "1u << 1"),
            ("ZAERO_SPAWNFLAG2_NOT_SINGLE", "1u << 2"),
        ):
            self.assertRegex(LOCAL, rf"{symbol}\s*=\s*{re.escape(value)}")
        self.assertIn("FIELD_AUTO(spawnflags2)", SPAWN)
        self.assertIn("FIELD_AUTO(spawnflags2)", SAVE)
        inhibit = SPAWN[SPAWN.index("inline bool G_InhibitEntity") : SPAWN.index("void setup_shadow_lights")]
        self.assertGreaterEqual(inhibit.count("ZAERO_SPAWNFLAG2_NOT_SINGLE"), 2)
        self.assertIn("ZAERO_SPAWNFLAG2_NOT_COOP", inhibit)
        self.assertNotIn("ZAERO_SPAWNFLAG2_MIRRORLEVEL", inhibit)

    def test_all_retained_map_fields_are_parsed_and_saved_where_stateful(self) -> None:
        parsed = {
            "model2",
            "model3",
            "model4",
            "spawnflags2",
            "aspeed",
            "active",
            "mteam",
            "mangle",
            "mins",
            "maxs",
        }
        for field in parsed:
            self.assertRegex(SPAWN, rf"FIELD_AUTO\({field}\)")
        for ignored in ("mirrortarget", "mirrorlevelsave"):
            self.assertRegex(SPAWN, rf'\{{\s*"{ignored}"\s*\}}')
        for field in ("model2", "model3", "model4", "mteam"):
            self.assertRegex(SAVE, rf"FIELD_LEVEL_STRING\({field}\)")
        for field in ("spawnflags2", "aspeed", "active", "mangle"):
            self.assertRegex(SAVE, rf"FIELD_AUTO\({field}\)")

    def test_mapper_classifier_separates_content_from_colliding_stock_semantics(self) -> None:
        expected = {
            "zbase1", "zbase2", "zdef1", "zdef2", "zdef3", "zdef4",
            "zwaste1", "zwaste2", "zwaste3", "ztomb1", "ztomb2", "ztomb3",
            "ztomb4", "zboss", "zdm1", "zdm2", "zdm3", "zdm4", "zdm5", "zdm6",
        }
        records = load_records(MAP_AUDIT)
        self.assertEqual({record["map_name"] for record in records}, expected)
        self.assertTrue(all(record["sha256"] for record in records))
        self.assertTrue(all(record["entity_lump_sha256"] for record in records))
        self.assertEqual(MAP_IDENTITY_HEADER.read_text(encoding="utf-8"), render(records))
        self.assertIn('"zaero_mapper_contract"', SPAWN)
        self.assertIn("G_ParseZaeroMapperMetadata", SPAWN)
        self.assertIn("G_ZaeroMapperSignature", SPAWN)
        self.assertIn("Zaero_FindShippedMapEntityIdentity", SPAWN)
        self.assertNotIn('"spawnflags2"', SPAWN[SPAWN.index("G_ZaeroMapperSignature"):SPAWN.index("G_ClassifyZaeroMapperContract")])
        self.assertIn("level.zaero_content_active = true", SPAWN)
        self.assertIn("level.zaero_mapper_contract = mapper_classification.enabled", SPAWN)
        self.assertIn("level.zaero_mapper_contract_reason = mapper_classification.reason", SPAWN)
        self.assertIn("entity-sha256", SPAWN)
        self.assertNotIn("G_IsZaeroMap", SPAWN)

    def test_mapper_scope_identity_is_registered_and_save_mismatches_fail_closed(self) -> None:
        self.assertIn("bool zaero_content_active;", LOCAL)
        self.assertIn("bool zaero_mapper_contract;", LOCAL)
        self.assertIn("zaero_mapper_contract_reason_t zaero_mapper_contract_reason;", LOCAL)
        self.assertIn("std::array<uint8_t, 32> zaero_entity_lump_sha256;", LOCAL)
        for field in (
            "zaero_content_active",
            "zaero_mapper_contract",
            "zaero_mapper_contract_reason",
            "zaero_entity_lump_sha256",
        ):
            self.assertIn(f"FIELD_AUTO({field})", SAVE)
            self.assertIn(f'json["level"].isMember("{field}")', SAVE)
        self.assertIn("predates Zaero mapper classification; no safe migration", SAVE)
        self.assertIn("Zaero map identity/classification mismatch", SAVE)
        self.assertIn("memset(&level, 0, sizeof(level))", SAVE)

    def test_map_only_native_adaptations_use_mapper_scope_not_content_scope(self) -> None:
        expected = {
            "g_items.cpp": "SPAWNFLAG_ITEM_MAX",
            "g_monster.cpp": "SPAWNFLAG_ZAERO_MONSTER_NO_COUNT",
            "g_target.cpp": "Zaero_MonsterKillBox(ent)",
            "g_utils.cpp": "bool Zaero_MonsterKillBox",
            "m_hover.cpp": "hover_zaero_dodge",
            "p_client.cpp": 'Q_strcasecmp(level.mapname, "zboss")',
            "p_weapon.cpp": "Weapon_RocketLauncher_Fire",
        }
        for filename, contract in expected.items():
            source = (ROOT / "src" / filename).read_text(encoding="utf-8")
            self.assertIn(contract, source)
            self.assertIn("level.zaero_mapper_contract", source)

        for filename in (
            "g_zaero_ai.cpp",
            "g_zaero_finale.cpp",
            "g_zaero_weapons.cpp",
        ):
            source = (ROOT / "src" / "zaero" / filename).read_text(encoding="utf-8")
            self.assertIn("level.zaero_mapper_contract", source)

    def test_cvar_hud_and_capacity_contracts_are_named(self) -> None:
        self.assertIn('gi.cvar("zdmflags", "0", CVAR_SERVERINFO)', MAIN)
        hud_names = [
            "STAT_ZAERO_SHOW_ORIGIN",
            "STAT_ZAERO_ORIGIN_X",
            "STAT_ZAERO_ORIGIN_Y",
            "STAT_ZAERO_ORIGIN_Z",
            "STAT_ZAERO_CAMERA_ICON",
            "STAT_ZAERO_CAMERA_TIMER",
            "STAT_ZAERO_CAMERA_LABEL",
        ]
        positions = [BG.index(name) for name in hud_names]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("STAT_ZAERO_CAMERA_LABEL < MAX_STATS", BG)

    def test_zboss_one_shot_target_state_is_noncolliding_and_saved(self) -> None:
        self.assertRegex(LOCAL, r"AI_ZAERO_ONESHOT_TARGET\s*=\s*bit_v<39>")
        self.assertIn("vec3_t zaero_shot_target;", LOCAL)
        self.assertIn("FIELD_AUTO(monsterinfo.zaero_shot_target)", SAVE)


if __name__ == "__main__":
    unittest.main()
