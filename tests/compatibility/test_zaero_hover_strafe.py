"""Static and golden contracts for Zaero Hover fly-strafe dodging."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AI = (ROOT / "src" / "g_ai.cpp").read_text(encoding="utf-8")
HOVER = (ROOT / "src" / "m_hover.cpp").read_text(encoding="utf-8")
LOCAL = (ROOT / "src" / "g_local.h").read_text(encoding="utf-8")
SAVE = (ROOT / "src" / "g_save.cpp").read_text(encoding="utf-8")
SAVE_COMPACT = re.sub(r"\s+", "", SAVE)
ZAERO_AI = (ROOT / "src" / "zaero" / "g_zaero_ai.cpp").read_text(
    encoding="utf-8"
)
SOURCE_AUDIT = json.loads(
    (ROOT / "docs" / "audits" / "source-delta.json").read_text(
        encoding="utf-8"
    )
)
BSP_AUDIT = json.loads(
    (ROOT / "docs" / "audits" / "bsp-entities.json").read_text(
        encoding="utf-8"
    )
)


def function_body(source: str, signature: str) -> str:
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1 : index]
    raise AssertionError(f"unterminated function: {signature}")


def selected_rolls(initial: float, step: float, clear_attempt: int | None) -> list[float]:
    """Independent model of the initial trace plus 36 rotated retries."""
    rolls: list[float] = []
    roll = initial
    for attempt in range(37):
        rolls.append(roll)
        if attempt == clear_attempt or attempt + 1 == 37:
            break
        roll += step
    return rolls


class ZaeroHoverStrafeContractTests(unittest.TestCase):
    def test_all_22_supplied_hover_placements_are_accounted_for(self) -> None:
        counts = {
            item["map_name"]: item["classname_counts"].get("monster_hover", 0)
            for item in BSP_AUDIT["maps"]
        }
        self.assertEqual(
            {name: count for name, count in counts.items() if count},
            {"zdef1": 11, "ztomb1": 5, "ztomb3": 3, "zwaste1": 3},
        )
        self.assertEqual(sum(counts.values()), 22)

    def test_supplied_ai_and_hover_oracles_are_identity_locked(self) -> None:
        records = {
            record["path"]: record
            for record in SOURCE_AUDIT["comparison"]["file_records"]
        }
        expected = {
            "g_ai.c": "9900846fdd8349b0fd75535705de98d2c1c270a0cbc4bc7a357d175dcbdd62ef",
            "m_hover.c": "d2b8dc0ad586c69d886b38ca404c65b2e211302ce6cc3b5cabf8d9c4e18d965a",
        }
        for path, digest in expected.items():
            self.assertEqual(records[path]["zaero_sha256"], digest)
            self.assertEqual(records[path]["status"], "modified")

        self.assertIn(
            "ai_fly_strafe",
            {item["name"] for item in records["g_ai.c"]["functions"]["added"]},
        )
        self.assertIn(
            "hover_dodge",
            {
                item["name"]
                for item in records["m_hover.c"]["functions"]["added"]
            },
        )

    def test_dedicated_state_and_typed_fields_round_trip_in_json(self) -> None:
        enum = re.search(
            r"AS_BLIND,.*?AS_ZAERO_FLY_STRAFE", LOCAL, flags=re.DOTALL
        )
        self.assertIsNotNone(enum)
        self.assertIn("float zaero_fly_strafe_roll;", LOCAL)
        self.assertIn("gtime_t zaero_fly_strafe_timeout;", LOCAL)
        for field in (
            "monsterinfo.attack_state",
            "monsterinfo.zaero_fly_strafe_roll",
            "monsterinfo.zaero_fly_strafe_timeout",
            "monsterinfo.dodge",
        ):
            self.assertEqual(SAVE_COMPACT.count(f"FIELD_AUTO({field})"), 1)

    def test_hover_callback_is_exactly_zaero_and_classname_scoped(self) -> None:
        dodge = function_body(HOVER, "MONSTERINFO_DODGE(hover_zaero_dodge)")
        for contract in (
            "!level.is_zaero",
            'strcmp(self->classname, "monster_hover") != 0',
            "active_move == &hover_move_attack1",
            "frandom() < 0.75f",
            "Zaero_BeginHoverFlyStrafe(self)",
        ):
            self.assertIn(contract, dodge)

        spawn = function_body(HOVER, "void SP_monster_hover")
        assignment = "self->monsterinfo.dodge = hover_zaero_dodge"
        self.assertEqual(spawn.count(assignment), 1)
        self.assertIn("level.is_zaero", spawn)
        self.assertIn('strcmp(self->classname, "monster_hover") == 0', spawn)

    def test_begin_selects_the_bounded_legacy_3d_direction(self) -> None:
        begin = function_body(ZAERO_AI, "void Zaero_BeginHoverFlyStrafe")
        for contract in (
            "AS_ZAERO_FLY_STRAFE",
            "crandom() * 180.0f",
            "ZAERO_FLY_STRAFE_ANGLE_STEP",
            "ZAERO_FLY_STRAFE_TRACE_COUNT",
            "RotatePointAroundVector(forward, right",
            "ZAERO_FLY_STRAFE_DISTANCE",
            "MASK_MONSTERSOLID",
            "level.time + ZAERO_FLY_STRAFE_DURATION",
        ):
            self.assertIn(contract, begin)
        self.assertIn("ZAERO_FLY_STRAFE_TRACE_COUNT = 37", ZAERO_AI)
        self.assertIn("ZAERO_FLY_STRAFE_DISTANCE = 96.0f", ZAERO_AI)
        self.assertIn("ZAERO_FLY_STRAFE_DURATION = 1_sec", ZAERO_AI)

        self.assertEqual(selected_rolls(17.0, 10.0, 0), [17.0])
        blocked = selected_rolls(17.0, 10.0, None)
        self.assertEqual(len(blocked), 37)
        self.assertEqual(blocked[-1], 377.0)

    def test_run_uses_typed_motion_and_explicitly_fixes_expiry(self) -> None:
        run = function_body(ZAERO_AI, "bool Zaero_RunFlyStrafe")
        for contract in (
            "zaero_fly_strafe_timeout < level.time",
            "Zaero_ResetFlyStrafe(self)",
            "distance * ZAERO_FLY_STRAFE_SCALE / FRAME_TIME_S.seconds()",
            "SV_FlyMove(self, FRAME_TIME_S.seconds(), MASK_SHOT)",
            "self->velocity != requested_velocity",
            "gi.linkentity(self)",
        ):
            self.assertIn(contract, run)
        self.assertIn("ZAERO_FLY_STRAFE_SCALE = 1.5f", ZAERO_AI)
        reset = function_body(ZAERO_AI, "void Zaero_ResetFlyStrafe")
        self.assertIn("attack_state = AS_STRAIGHT", reset)
        self.assertIn("zaero_fly_strafe_timeout = 0_ms", reset)
        self.assertIn("zaero_fly_strafe_roll = 0.0f", reset)

        # The source uses strict `<`: equality at the one-second boundary still
        # consumes a strafe frame, then the next 40 Hz tick resets safely.
        active_ticks = [tick for tick in range(42) if not 40 < tick]
        self.assertEqual(active_ticks[0], 0)
        self.assertEqual(active_ticks[-1], 40)
        self.assertNotIn(41, active_ticks)

    def test_ai_hook_precedes_native_attack_and_does_not_replace_it(self) -> None:
        run = function_body(AI, "void ai_run(edict_t *self, float dist)")
        hook = run.index("Zaero_RunFlyStrafe(self, dist)")
        attack = run.index("retval = ai_checkattack(self, dist)")
        self.assertLess(hook, attack)
        self.assertIn("if (Zaero_RunFlyStrafe(self, dist))\n        return;", run)
        for native_contract in (
            "AI_SOUND_TARGET",
            "AI_DODGING",
            "ai_run_slide(self, dist)",
            "M_MoveToGoal(self, dist)",
        ):
            self.assertIn(native_contract, run)


if __name__ == "__main__":
    unittest.main()
