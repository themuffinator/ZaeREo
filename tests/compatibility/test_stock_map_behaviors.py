"""Compatibility contracts for Zaero extensions to stock map entities.

These deterministic models lock the source-derived boundary behavior while the
game DLL integration assertions ensure the models and JSON save fields remain
wired into the Rerelease implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MAX_QPATH = 64
MAX_TIMER_TARGETS = 16
ZAERO_PUSH_START_OFF = 2
ZAERO_PUSH_NO_SOUND = 4
ZAERO_PLAT_LOW_TRIGGER_2 = 2
PLAT_LOW_TRIGGER_2_MAPS = {
    "zbase2": 1,
    "zdef1": 1,
    "zdef2": 2,
    "zdef4": 1,
    "zdm1": 1,
    "zdm3": 1,
    "zdm4": 2,
    "ztomb3": 2,
}
SOURCE_AUDIT = json.loads(
    (REPOSITORY_ROOT / "docs" / "audits" / "source-delta.json").read_text(
        encoding="utf-8"
    )
)
BSP_AUDIT = json.loads(
    (REPOSITORY_ROOT / "docs" / "audits" / "bsp-entities.json").read_text(
        encoding="utf-8"
    )
)


def parse_timer_targets(value: str) -> tuple[str, ...] | None:
    """Model the bounded parser used only for semicolon target lists."""

    if ";" not in value:
        return None
    targets = tuple(part for part in value.split(";") if part)
    if not targets:
        raise ValueError("empty target list")
    if len(targets) > MAX_TIMER_TARGETS:
        raise ValueError("too many targets")
    if any(len(target) >= MAX_QPATH for target in targets):
        raise ValueError("target exceeds MAX_QPATH")
    return targets


def zaero_low_plat_touch_activates(
    *,
    is_player: bool,
    health: int,
    is_zaero_map: bool,
    spawnflags: int,
    feet_z: float,
    lowered_top_z: float,
) -> bool:
    """Model Touch_Plat_Center while the platform is at STATE_BOTTOM."""

    if not is_player or health <= 0:
        return False
    if (
        is_zaero_map
        and spawnflags & ZAERO_PLAT_LOW_TRIGGER_2
        and feet_z > lowered_top_z + 8
    ):
        return False
    return True


@dataclass(frozen=True)
class Rotation:
    state: str
    current_speed: float
    sound_on: bool


def use_rotation(
    rotation: Rotation, *, speed: float, accel: float, decel: float
) -> Rotation:
    """Model Zaero's stateful func_rotating use callback."""

    if rotation.state in {"top_speed", "accelerating"}:
        if decel <= 0:
            return Rotation("stopped", 0.0, False)
        return Rotation("decelerating", rotation.current_speed, rotation.sound_on)
    if accel <= 0:
        return Rotation("top_speed", speed, True)
    return Rotation("accelerating", rotation.current_speed, True)


def think_rotation(
    rotation: Rotation,
    *,
    speed: float,
    accel: float,
    decel: float,
    frame_seconds: float = 0.025,
) -> Rotation:
    """Advance the legacy 10 Hz rate formula at a Rerelease 40 Hz tick."""

    state = rotation.state
    current = rotation.current_speed
    sound = rotation.sound_on
    if state == "decelerating":
        if current <= 0:
            return Rotation("stopped", 0.0, False)
        current -= decel * frame_seconds
    elif state == "accelerating":
        if current >= speed:
            return Rotation("top_speed", speed, sound)
        current += accel * frame_seconds
    return Rotation(state, current, sound)


class TimerTargetTests(unittest.TestCase):
    def test_literal_target_retains_native_behavior(self) -> None:
        self.assertIsNone(parse_timer_targets("ordinary_target"))

    def test_all_shipped_lists_are_bounded_and_select_only_listed_targets(self) -> None:
        shipped = {
            "zdm6": "thud;alien1;alien2",
            "ztomb2": "tombsound1;tombsound2",
            "ztomb4": "stomb1;stomb2;stomb3;stomb4",
        }
        expected = {
            "zdm6": ("thud", "alien1", "alien2"),
            "ztomb2": ("tombsound1", "tombsound2"),
            "ztomb4": ("stomb1", "stomb2", "stomb3", "stomb4"),
        }
        for map_name, target_list in shipped.items():
            with self.subTest(map_name=map_name):
                parsed = parse_timer_targets(target_list)
                self.assertEqual(parsed, expected[map_name])
                self.assertEqual({parsed[index] for index in range(len(parsed))}, set(expected[map_name]))

    def test_empty_fields_follow_legacy_strtok_behavior(self) -> None:
        self.assertEqual(parse_timer_targets(";one;;two;"), ("one", "two"))

    def test_bounds_reject_unsafe_legacy_inputs(self) -> None:
        self.assertEqual(
            len(parse_timer_targets(";".join(f"t{i}" for i in range(16)))),
            16,
        )
        with self.assertRaisesRegex(ValueError, "too many"):
            parse_timer_targets(";".join(f"t{i}" for i in range(17)))
        self.assertEqual(parse_timer_targets("x" * 63 + ";ok")[0], "x" * 63)
        with self.assertRaisesRegex(ValueError, "MAX_QPATH"):
            parse_timer_targets("x" * 64 + ";ok")
        with self.assertRaisesRegex(ValueError, "empty"):
            parse_timer_targets(";;;")


class TriggerPushTests(unittest.TestCase):
    def test_zaero_use_toggles_bit_two_without_disturbing_no_sound(self) -> None:
        flags = ZAERO_PUSH_START_OFF | ZAERO_PUSH_NO_SOUND
        self.assertTrue(flags & ZAERO_PUSH_START_OFF)
        flags ^= ZAERO_PUSH_START_OFF
        self.assertFalse(flags & ZAERO_PUSH_START_OFF)
        self.assertTrue(flags & ZAERO_PUSH_NO_SOUND)
        flags ^= ZAERO_PUSH_START_OFF
        self.assertTrue(flags & ZAERO_PUSH_START_OFF)

    def test_native_and_zaero_bit_two_paths_are_explicitly_separated(self) -> None:
        source = (REPOSITORY_ROOT / "src" / "g_trigger.cpp").read_text(encoding="utf-8")
        self.assertIn("SPAWNFLAG_PUSH_PLUS = 0x02_spawnflag", source)
        self.assertIn("SPAWNFLAG_PUSH_ZAERO_START_OFF = 0x02_spawnflag", source)
        self.assertIn("if (!level.zaero_mapper_contract && self->spawnflags.has(SPAWNFLAG_PUSH_PLUS))", source)
        self.assertIn("self->spawnflags ^= SPAWNFLAG_PUSH_ZAERO_START_OFF", source)
        self.assertIn("other->client && self->message", source)


class PlatLowTriggerTests(unittest.TestCase):
    def test_legacy_source_and_all_shipped_placements_are_identity_locked(self) -> None:
        records = {
            record["path"]: record
            for record in SOURCE_AUDIT["comparison"]["file_records"]
        }
        self.assertEqual(
            records["g_func.c"]["zaero_sha256"],
            "aa7d05629c1213145e8fb74d14252d0b982b35cbc2dd4c75f1c27882f72adea6",
        )
        self.assertEqual(records["g_func.c"]["status"], "modified")
        self.assertEqual(sum(PLAT_LOW_TRIGGER_2_MAPS.values()), 11)
        self.assertEqual(
            set(PLAT_LOW_TRIGGER_2_MAPS),
            {
                "zbase2",
                "zdef1",
                "zdef2",
                "zdef4",
                "zdm1",
                "zdm3",
                "zdm4",
                "ztomb3",
            },
        )
        func_plat_maps = set(BSP_AUDIT["global"]["classname_maps"]["func_plat"])
        self.assertLessEqual(set(PLAT_LOW_TRIGGER_2_MAPS), func_plat_maps)

    def test_exact_eight_unit_feet_boundary_is_inclusive(self) -> None:
        common = {
            "is_player": True,
            "health": 100,
            "is_zaero_map": True,
            "spawnflags": ZAERO_PLAT_LOW_TRIGGER_2,
            "lowered_top_z": 64.0,
        }
        self.assertTrue(zaero_low_plat_touch_activates(feet_z=71.999, **common))
        self.assertTrue(zaero_low_plat_touch_activates(feet_z=72.0, **common))
        self.assertFalse(zaero_low_plat_touch_activates(feet_z=72.001, **common))

    def test_non_players_and_dead_players_never_activate(self) -> None:
        common = {
            "is_zaero_map": True,
            "spawnflags": ZAERO_PLAT_LOW_TRIGGER_2,
            "feet_z": 64.0,
            "lowered_top_z": 64.0,
        }
        self.assertFalse(
            zaero_low_plat_touch_activates(is_player=False, health=100, **common)
        )
        self.assertFalse(
            zaero_low_plat_touch_activates(is_player=True, health=0, **common)
        )

    def test_bit_two_collision_is_dispatched_by_positive_zaero_map_identity(self) -> None:
        source = (REPOSITORY_ROOT / "src" / "g_func.cpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("SPAWNFLAG_PLAT_NO_MONSTER = 2_spawnflag", source)
        self.assertIn("SPAWNFLAG_PLAT_ZAERO_LOW_TRIGGER_2 = 2_spawnflag", source)
        self.assertIn(
            "const bool native_no_monster = !level.zaero_mapper_contract && "
            "ent->spawnflags.has(SPAWNFLAG_PLAT_NO_MONSTER);",
            source,
        )

        touch_start = source.index("TOUCH(Touch_Plat_Center)")
        touch_end = source.index("edict_t *plat_spawn_inside_trigger", touch_start)
        touch = source[touch_start:touch_end]
        self.assertIn("if (!other->client)", touch)
        self.assertIn("if (other->health <= 0)", touch)
        self.assertIn("if (ent->moveinfo.state == STATE_BOTTOM)", touch)
        self.assertIn(
            "level.zaero_mapper_contract && "
            "ent->spawnflags.has(SPAWNFLAG_PLAT_ZAERO_LOW_TRIGGER_2)",
            touch,
        )
        self.assertIn(
            "other->s.origin[2] + other->mins[2] > "
            "ent->moveinfo.end_origin[2] + ent->maxs[2] + 8.0f",
            touch,
        )
        height_check = touch.index("other->s.origin[2] + other->mins[2]")
        height_rejection = touch.index("return;", height_check)
        self.assertLess(height_rejection, touch.index("plat_go_up(ent);"))

        self.assertIn(
            "if (ent->spawnflags.has(SPAWNFLAG_PLAT_LOW_TRIGGER))",
            source,
        )
        self.assertIn("tmax[2] = tmin[2] + 8;", source)

    def test_non_zaero_bit_two_retains_native_touch_and_no_monster_meaning(self) -> None:
        common = {
            "is_player": True,
            "health": 100,
            "spawnflags": ZAERO_PLAT_LOW_TRIGGER_2,
            "feet_z": 256.0,
            "lowered_top_z": 64.0,
        }
        self.assertTrue(
            zaero_low_plat_touch_activates(is_zaero_map=False, **common)
        )

        source = (REPOSITORY_ROOT / "src" / "g_func.cpp").read_text(
            encoding="utf-8"
        )
        use_start = source.index("USE(Use_Plat)")
        use_end = source.index("TOUCH(Touch_Plat_Center)", use_start)
        use = source[use_start:use_end]
        self.assertIn(
            "if ((other->svflags & SVF_MONSTER) && !native_no_monster)", use
        )


class RotatingTests(unittest.TestCase):
    def test_zdef1_acceleration_and_deceleration_are_tick_rate_independent(self) -> None:
        rotation = use_rotation(
            Rotation("stopped", 0.0, False), speed=630, accel=200, decel=150
        )
        self.assertEqual(rotation, Rotation("accelerating", 0.0, True))
        for _ in range(126):
            rotation = think_rotation(rotation, speed=630, accel=200, decel=150)
        self.assertEqual(rotation, Rotation("accelerating", 630.0, True))
        rotation = think_rotation(rotation, speed=630, accel=200, decel=150)
        self.assertEqual(rotation, Rotation("top_speed", 630, True))

        rotation = use_rotation(rotation, speed=630, accel=200, decel=150)
        self.assertEqual(rotation.state, "decelerating")
        for _ in range(168):
            rotation = think_rotation(rotation, speed=630, accel=200, decel=150)
        self.assertEqual(rotation, Rotation("decelerating", 0.0, True))
        rotation = think_rotation(rotation, speed=630, accel=200, decel=150)
        self.assertEqual(rotation, Rotation("stopped", 0.0, False))

    def test_zdm6_negative_accel_means_immediate_start_and_boundary_is_preserved(self) -> None:
        rotation = use_rotation(
            Rotation("stopped", 0.0, False), speed=800, accel=-1, decel=240
        )
        self.assertEqual(rotation, Rotation("top_speed", 800, True))
        rotation = use_rotation(rotation, speed=800, accel=-1, decel=240)
        for _ in range(134):
            rotation = think_rotation(rotation, speed=800, accel=-1, decel=240)
        self.assertEqual(rotation, Rotation("decelerating", -4.0, True))
        rotation = think_rotation(rotation, speed=800, accel=-1, decel=240)
        self.assertEqual(rotation, Rotation("stopped", 0.0, False))

    def test_toggle_during_deceleration_restarts_from_current_speed(self) -> None:
        rotation = Rotation("decelerating", 300.0, True)
        restarted = use_rotation(rotation, speed=630, accel=200, decel=150)
        self.assertEqual(restarted, Rotation("accelerating", 300.0, True))

    def test_start_on_reset_quirk_is_explicit_pending_q021_decision(self) -> None:
        source = (REPOSITORY_ROOT / "src" / "g_func.cpp").read_text(encoding="utf-8")
        start_on = source.index("if (ent->spawnflags.has(SPAWNFLAG_ROTATING_START_ON))")
        reset_note = source.index("The original DLL reset these after START_ON")
        self.assertLess(start_on, reset_note)
        self.assertIn(
            "ent->zaero_rotating_state = zaero_rotating_state_t::stopped",
            source[reset_note:],
        )


class IntegrationContractTests(unittest.TestCase):
    def test_transient_and_phase_state_are_in_json_save_schema(self) -> None:
        header = (REPOSITORY_ROOT / "src" / "g_local.h").read_text(encoding="utf-8")
        saves = (REPOSITORY_ROOT / "src" / "g_save.cpp").read_text(encoding="utf-8")
        functions = (REPOSITORY_ROOT / "src" / "g_func.cpp").read_text(encoding="utf-8")

        for field in (
            "zaero_rotating_state",
            "zaero_timer_targets",
            "zaero_timer_target_count",
        ):
            self.assertIn(field, header)
            self.assertIn(f"FIELD_AUTO({field})", saves)

        self.assertIn("THINK(zaero_rotating_think)", functions)
        self.assertIn("self->decel * gi.frame_time_s", functions)
        self.assertIn("self->accel * gi.frame_time_s", functions)
        self.assertIn("THINK(rotating_accel)", functions)
        self.assertIn(
            "if (!level.zaero_mapper_contract && ent->spawnflags.has(SPAWNFLAG_ROTATING_ACCEL))",
            functions,
        )
        self.assertIn("make_savable_memory<uint8_t, TAG_LEVEL>", functions)
        self.assertIn("if (!level.zaero_mapper_contract || !self->target", functions)


if __name__ == "__main__":
    unittest.main()
