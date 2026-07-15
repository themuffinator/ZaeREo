from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "src" / "zaero" / "g_zaero_hound.cpp").read_text(
    encoding="utf-8"
)
LOCAL = (ROOT / "src" / "g_local.h").read_text(encoding="utf-8")
SPAWN = (ROOT / "src" / "g_spawn.cpp").read_text(encoding="utf-8")


class ZaeroHoundContractTests(unittest.TestCase):
    def test_exact_classname_and_source_are_integrated_once(self) -> None:
        self.assertEqual(
            len(re.findall(r'\{\s*"monster_hound"\s*,\s*SP_monster_hound\s*\}', SPAWN)),
            1,
        )
        project = (ROOT / "src" / "game.vcxproj").read_text(encoding="utf-8")
        self.assertIn('ClCompile Include="zaero\\g_zaero_hound.cpp"', project)

    def test_schooling_flag_is_noncolliding_and_mapper_bit_is_consumed(self) -> None:
        self.assertRegex(LOCAL, r"AI_ZAERO_SCHOOLING\s*=\s*bit_v<40>")
        self.assertIn("SPAWNFLAG_HOUND_SCHOOLING = 8_spawnflag", SOURCE)
        self.assertIn("self->spawnflags &= ~SPAWNFLAG_HOUND_SCHOOLING", SOURCE)
        self.assertIn("self->monsterinfo.aiflags |= AI_ZAERO_SCHOOLING", SOURCE)

    def test_legacy_schooling_quirks_are_explicit(self) -> None:
        self.assertIn("HOUND_SCHOOL_RADIUS = 500.0f", SOURCE)
        self.assertIn("HOUND_NEIGHBOR_SCAN_RADIUS = 2000.0f", SOURCE)
        self.assertIn("total_bearing += anglemod(peer->s.angles[YAW])", SOURCE)
        self.assertIn("self->ideal_yaw = total_bearing / visible_ahead", SOURCE)
        self.assertIn("self->ideal_yaw = nearest->s.angles[YAW]", SOURCE)
        self.assertIn("!hound_is_live_peer(self, peer)", SOURCE)

    def test_schooling_does_not_mutate_neighbor_scratch_state(self) -> None:
        self.assertNotIn("zDistance", SOURCE)
        self.assertNotIn("zRadius", SOURCE)
        self.assertNotIn("zSchoolChain", SOURCE)
        self.assertEqual(SOURCE.count("findradius("), 4)

    def test_bite_and_unbounded_leap_contracts_are_present(self) -> None:
        self.assertIn("irandom(30, 35)", SOURCE)
        self.assertEqual(SOURCE.count("hound_bite_followup"), 5)
        self.assertIn("irandom(40, 50)", SOURCE)
        self.assertIn("self->velocity = forward * 400.0f", SOURCE)
        self.assertIn("self->velocity[2] = 200.0f", SOURCE)
        self.assertIn("no upper range cap", SOURCE)

    def test_source_animation_ranges_are_exact(self) -> None:
        expected_ranges = {
            "FRAME_STAND1": (129, 147),
            "FRAME_STAND2": (148, 168),
            "FRAME_WALK": (169, 176),
            "FRAME_RUN": (177, 183),
            "FRAME_LEAP": (184, 190),
            "FRAME_ATTACK1": (191, 194),
            "FRAME_ATTACK2": (195, 207),
            "FRAME_PAIN1": (208, 211),
            "FRAME_PAIN2": (212, 219),
            "FRAME_DEATH": (220, 231),
        }
        for prefix, (start, end) in expected_ranges.items():
            self.assertIn(f"{prefix}_START = {start}", SOURCE)
            self.assertIn(f"{prefix}_END = {end}", SOURCE)

    def test_every_runtime_callback_and_move_is_save_registered(self) -> None:
        for callback, macro in {
            "hound_sight": "MONSTERINFO_SIGHT",
            "hound_stand": "MONSTERINFO_STAND",
            "hound_run": "MONSTERINFO_RUN",
            "hound_walk": "MONSTERINFO_WALK",
            "hound_pain": "PAIN",
            "hound_setskin": "MONSTERINFO_SETSKIN",
            "hound_melee": "MONSTERINFO_MELEE",
            "hound_jump_touch": "TOUCH",
            "hound_jump": "MONSTERINFO_ATTACK",
            "hound_checkattack": "MONSTERINFO_CHECKATTACK",
            "hound_die": "DIE",
        }.items():
            self.assertIn(f"{macro}({callback})", SOURCE)
        self.assertEqual(SOURCE.count("MMOVE_T(hound_move_"), 11)

    def test_spawn_uses_native_monster_lifecycle(self) -> None:
        self.assertIn("if (!M_AllowSpawn(self))", SOURCE)
        self.assertIn("walkmonster_start(self);", SOURCE)
        self.assertIn("self->health = 175 * st.health_multiplier", SOURCE)
        self.assertIn("self->gib_health = -50", SOURCE)
        self.assertIn("self->mass = 250", SOURCE)


if __name__ == "__main__":
    unittest.main()
