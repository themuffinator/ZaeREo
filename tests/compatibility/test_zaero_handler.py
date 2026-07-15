from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HANDLER = (ROOT / "src" / "zaero" / "g_zaero_handler.cpp").read_text(
    encoding="utf-8"
)
HOUND = (ROOT / "src" / "zaero" / "g_zaero_hound.cpp").read_text(
    encoding="utf-8"
)
INFANTRY = (ROOT / "src" / "m_infantry.cpp").read_text(encoding="utf-8")
SPAWN = (ROOT / "src" / "g_spawn.cpp").read_text(encoding="utf-8")


class ZaeroHandlerContractTests(unittest.TestCase):
    def test_exact_classname_and_project_integration(self) -> None:
        self.assertEqual(
            len(
                re.findall(
                    r'\{\s*"monster_handler"\s*,\s*SP_monster_handler\s*\}',
                    SPAWN,
                )
            ),
            1,
        )
        project = (ROOT / "src" / "game.vcxproj").read_text(encoding="utf-8")
        self.assertIn('ClCompile Include="zaero\\g_zaero_handler.cpp"', project)

    def test_combined_model_bounds_and_source_frames_are_exact(self) -> None:
        self.assertIn('"models/monsters/guard/handler/tris.md2"', HANDLER)
        self.assertIn('"models/monsters/guard/hound/tris.md2"', HANDLER)
        self.assertIn("self->mins = { -32, -32, -24 }", HANDLER)
        self.assertIn("self->maxs = { 32, 32, 32 }", HANDLER)
        for prefix, (start, end) in {
            "FRAME_STAND1": (0, 30),
            "FRAME_STAND2": (31, 59),
            "FRAME_STAND3": (60, 89),
            "FRAME_STAND4": (90, 100),
            "FRAME_STAND5": (101, 110),
            "FRAME_RELEASE": (111, 128),
        }.items():
            self.assertIn(f"{prefix}_START = {start}", HANDLER)
            self.assertIn(f"{prefix}_END = {end}", HANDLER)
        self.assertEqual(HANDLER.count("MMOVE_T(handler_move_"), 6)

    def test_pre_split_lethal_clamp_precedes_generic_kill_accounting(self) -> None:
        self.assertIn("self->flags |= FL_IMMORTAL", HANDLER)
        self.assertIn("self->health = 1", HANDLER)
        self.assertIn("self->flags &= ~FL_IMMORTAL", INFANTRY)
        self.assertLess(
            HANDLER.index("self->flags |= FL_IMMORTAL"),
            HANDLER.index("walkmonster_start(self)"),
        )

    def test_release_duplicates_remaining_health_with_stable_identity(self) -> None:
        self.assertIn('hound->classname = HOUND_CLASSNAME', HOUND)
        self.assertIn("hound->health = std::max(handler->health, 1)", HOUND)
        self.assertIn("hound->max_health = std::max(handler->max_health, 1)", HOUND)
        self.assertIn("FRAME_HANDLER_SEPARATE = 122", HOUND)
        self.assertIn("FRAME_HANDLER_RELEASE_END = 128", HOUND)
        self.assertIn("ZaeroCreateHandlerHound(self)", HANDLER)
        self.assertIn("self->s.modelindex2 = 0", HANDLER)

    def test_future_hound_count_is_reserved_without_double_counting(self) -> None:
        self.assertIn("level.total_monsters++", HANDLER)
        self.assertIn("SPAWNFLAG_ZAERO_MONSTER_NO_COUNT", HANDLER)
        self.assertIn("hound->monsterinfo.aiflags |= AI_DO_NOT_COUNT", HOUND)
        self.assertIn("hound->monsterinfo.aiflags &= ~AI_DO_NOT_COUNT", HOUND)
        self.assertIn("registered = hound", HOUND)

    def test_release_wait_loops_preserve_legacy_frame_semantics(self) -> None:
        self.assertIn("self->powerarmor_time = level.time + 3_sec", HANDLER)
        self.assertIn("gtime_t::from_sec(frandom(0.0f, 0.3f))", HANDLER)
        self.assertIn("self->s.frame--;", HANDLER)
        self.assertIn("self->s.frame -= 2;", HANDLER)
        self.assertNotIn("nextframe = self->s.frame - 1", HANDLER)

    def test_conversion_reuses_native_infantry_without_restarting_entity(self) -> None:
        self.assertIn("InfantryConfigureNativeBehavior(self, true)", INFANTRY)
        body = INFANTRY.split("void InfantryConvertFromZaeroHandler", 1)[1].split(
            "constexpr spawnflags_t SPAWNFLAG_INFANTRY_NOJUMPING", 1
        )[0]
        self.assertNotIn("monster_start", body)
        self.assertNotIn("walkmonster_start", body)
        self.assertIn("self->s.origin[0] -= 18.0f", body)
        self.assertIn("self->s.origin[1] -= 9.0f", body)
        self.assertIn("infantry_run(self)", body)

    def test_every_saved_callback_and_move_has_a_stable_registration(self) -> None:
        for callback, macro in {
            "handler_stand": "MONSTERINFO_STAND",
            "handler_walk": "MONSTERINFO_WALK",
            "handler_run": "MONSTERINFO_RUN",
            "handler_attack": "MONSTERINFO_ATTACK",
            "handler_sight": "MONSTERINFO_SIGHT",
            "handler_pain": "PAIN",
            "handler_die": "DIE",
        }.items():
            self.assertIn(f"{macro}({callback})", HANDLER)
        self.assertEqual(HANDLER.count("MMOVE_T(handler_move_"), 6)
        self.assertIn("MMOVE_T(hound_move_handler_jump)", HOUND)


if __name__ == "__main__":
    unittest.main()
