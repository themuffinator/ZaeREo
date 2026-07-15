from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "src" / "zaero" / "g_zaero_sentien.cpp").read_text(
    encoding="utf-8"
)
LOCAL = (ROOT / "src" / "g_local.h").read_text(encoding="utf-8")
SAVE = (ROOT / "src" / "g_save.cpp").read_text(encoding="utf-8")
COMBAT = (ROOT / "src" / "g_combat.cpp").read_text(encoding="utf-8")
SPAWN = (ROOT / "src" / "g_spawn.cpp").read_text(encoding="utf-8")


class ZaeroSentienContractTests(unittest.TestCase):
    def test_exact_legacy_classname_and_project_integration(self) -> None:
        self.assertEqual(
            len(
                re.findall(
                    r'\{\s*"monster_sentien"\s*,\s*SP_monster_sentien\s*\}',
                    SPAWN,
                )
            ),
            1,
        )
        project = (ROOT / "src" / "game.vcxproj").read_text(encoding="utf-8")
        self.assertIn('ClCompile Include="zaero\\g_zaero_sentien.cpp"', project)

    def test_all_supplied_animation_ranges_are_exact(self) -> None:
        expected_ranges = {
            "FRAME_STAND1": (0, 28),
            "FRAME_STAND2": (29, 48),
            "FRAME_STAND3": (49, 79),
            "FRAME_WALK_START": (80, 87),
            "FRAME_WALK_LOOP": (88, 103),
            "FRAME_WALK_END": (104, 111),
            "FRAME_BLAST_PRE": (112, 115),
            "FRAME_BLAST": (116, 121),
            "FRAME_BLAST_POST": (122, 125),
            "FRAME_LASER_PRE": (126, 130),
            "FRAME_LASER": (131, 141),
            "FRAME_LASER_POST": (142, 145),
            "FRAME_FEND": (168, 182),
            "FRAME_PAIN1": (183, 186),
            "FRAME_PAIN2": (187, 192),
            "FRAME_PAIN3": (193, 213),
            "FRAME_DEATH1": (214, 241),
            "FRAME_DEATH2": (242, 270),
        }
        for prefix, (start, end) in expected_ranges.items():
            self.assertIn(f"{prefix}_START = {start}", SOURCE)
            self.assertIn(f"{prefix}_END = {end}", SOURCE)
        self.assertIn("FRAME_FEND_HOLD = 173", SOURCE)
        self.assertEqual(SOURCE.count("MMOVE_T(sentien_move_"), 21)

    def test_spawn_preserves_grounded_legacy_lifecycle_and_stats(self) -> None:
        self.assertIn("if (!M_AllowSpawn(self))", SOURCE)
        self.assertIn('"models/monsters/sentien/tris.md2"', SOURCE)
        self.assertIn("self->mins = { -32, -32, -16 }", SOURCE)
        self.assertIn("self->maxs = { 32, 32, 72 }", SOURCE)
        self.assertIn("self->movetype = MOVETYPE_STEP", SOURCE)
        self.assertIn("walkmonster_start(self);", SOURCE)
        self.assertNotIn("flymonster_start(self)", SOURCE)
        self.assertIn("self->health = 900 * st.health_multiplier", SOURCE)
        self.assertIn("self->gib_health = -425", SOURCE)
        self.assertIn("self->mass = 500", SOURCE)

    def test_burst_keeps_hardcoded_two_damage_quirk_and_emp_calls(self) -> None:
        helper = SOURCE.split("void sentien_fire_bullet", 1)[1].split(
            "void sentien_do_blast", 1
        )[0]
        self.assertIn("(void) damage", helper)
        self.assertRegex(
            helper,
            r"fire_bullet\(self, start, dir, 2, 4,\s*"
            r"DEFAULT_BULLET_HSPREAD, DEFAULT_BULLET_VSPREAD, MOD_UNKNOWN\)",
        )
        self.assertIn("sentien_fire_bullet(self, start, aim, 5)", SOURCE)
        self.assertGreaterEqual(SOURCE.count("Zaero_EMPNukeCheck("), 3)
        self.assertGreaterEqual(SOURCE.count("Zaero_PlayEMPMisfire("), 3)

    def test_laser_is_skill_scaled_locked_and_generation_safe(self) -> None:
        self.assertIn('SENTIEN_LASER_CLASSNAME = "laser_yaya"', SOURCE)
        self.assertIn("laser->dmg = 8", SOURCE)
        self.assertIn("self->beam->dmg * 1.5f", SOURCE)
        self.assertIn("self->beam->dmg * 2.5f", SOURCE)
        self.assertIn("self->yaw_speed *= 1.5f", SOURCE)
        self.assertIn("self->yaw_speed *= 2.0f", SOURCE)
        self.assertIn("self->beam->s.angles = vectoangles(aim)", SOURCE)
        self.assertIn("laser->count = self->spawn_count", SOURCE)
        self.assertIn("sentien->spawn_count != self->count", SOURCE)
        self.assertIn("sentien->beam != self", SOURCE)
        self.assertIn("G_FreeEdict(self->beam)", SOURCE)
        self.assertIn("FIELD_AUTO( beam )", SAVE)

    def test_fend_uses_typed_time_saved_scale_and_distinct_flag(self) -> None:
        self.assertRegex(LOCAL, r"AI_ZAERO_REDUCED_DAMAGE\s*=\s*bit_v<41>")
        self.assertRegex(
            LOCAL, r"AI_ZAERO_MONSTER_REDUCED_DAMAGE\s*=\s*bit_v<42>"
        )
        self.assertIn("float zaero_damage_scale", LOCAL)
        self.assertIn("FIELD_AUTO(monsterinfo.zaero_damage_scale)", SAVE)
        self.assertIn("self->monsterinfo.zaero_damage_scale = 0.85f", SOURCE)
        self.assertIn("self->monsterinfo.pausetime = level.time + 1_sec", SOURCE)
        self.assertIn("skill->integer == 0 ? 0.45f", SOURCE)
        self.assertIn("skill->integer == 1 ? 0.60f", SOURCE)
        self.assertIn("AI_HOLD_FRAME | AI_ZAERO_REDUCED_DAMAGE", SOURCE)

    def test_damage_reduction_hook_is_zaero_gated_and_boss_reusable(self) -> None:
        self.assertIn("if (level.is_zaero && (targ->svflags & SVF_MONSTER)", COMBAT)
        self.assertIn("targ->monsterinfo.zaero_damage_scale > 0.0f", COMBAT)
        self.assertIn("AI_ZAERO_REDUCED_DAMAGE", COMBAT)
        self.assertIn("AI_ZAERO_MONSTER_REDUCED_DAMAGE", COMBAT)
        self.assertIn("inflictor->svflags & SVF_MONSTER", COMBAT)
        self.assertRegex(
            COMBAT,
            r"damage\s*=\s*static_cast<int32_t>\("
            r"damage \* targ->monsterinfo\.zaero_damage_scale\)",
        )

    def test_every_saved_runtime_callback_and_move_is_registered(self) -> None:
        for callback, macro in {
            "sentien_laser_think": "THINK",
            "sentien_stand": "MONSTERINFO_STAND",
            "sentien_walk": "MONSTERINFO_WALK",
            "sentien_run": "MONSTERINFO_RUN",
            "sentien_attack": "MONSTERINFO_ATTACK",
            "sentien_fend": "MONSTERINFO_DODGE",
            "sentien_pain": "PAIN",
            "sentien_setskin": "MONSTERINFO_SETSKIN",
            "sentien_die": "DIE",
        }.items():
            self.assertIn(f"{macro}({callback})", SOURCE)


if __name__ == "__main__":
    unittest.main()
