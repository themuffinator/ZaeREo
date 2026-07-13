from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
LOCAL = (ROOT / "src" / "g_local.h").read_text(encoding="utf-8")
SPAWN = (ROOT / "src" / "g_spawn.cpp").read_text(encoding="utf-8")
SAVE = (ROOT / "src" / "g_save.cpp").read_text(encoding="utf-8")
MAIN = (ROOT / "src" / "g_main.cpp").read_text(encoding="utf-8")
BG = (ROOT / "src" / "bg_local.h").read_text(encoding="utf-8")


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

    def test_zaero_map_discriminator_covers_all_retail_bsps(self) -> None:
        start = SPAWN.index("static bool G_IsZaeroMap")
        body = SPAWN[start : start + 2200]
        expected = {
            "zbase1", "zbase2", "zdef1", "zdef2", "zdef3", "zdef4",
            "zwaste1", "zwaste2", "zwaste3", "ztomb1", "ztomb2", "ztomb3",
            "ztomb4", "zboss", "zdm1", "zdm2", "zdm3", "zdm4", "zdm5", "zdm6",
        }
        names = set(re.findall(r'"(z(?:base|def|waste|tomb|boss|dm)[0-9]*)"', body))
        self.assertEqual(names, expected)
        self.assertIn("level.is_zaero = G_IsZaeroMap", SPAWN)

    def test_cvar_hud_and_capacity_contracts_are_named(self) -> None:
        self.assertIn('gi.cvar("zdmflags", "0", CVAR_SERVERINFO)', MAIN)
        hud_names = [
            "STAT_ZAERO_SHOW_ORIGIN",
            "STAT_ZAERO_ORIGIN_X",
            "STAT_ZAERO_ORIGIN_Y",
            "STAT_ZAERO_ORIGIN_Z",
            "STAT_ZAERO_CAMERA_ICON",
            "STAT_ZAERO_CAMERA_TIMER",
        ]
        positions = [BG.index(name) for name in hud_names]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("STAT_ZAERO_CAMERA_TIMER < MAX_STATS", BG)


if __name__ == "__main__":
    unittest.main()
