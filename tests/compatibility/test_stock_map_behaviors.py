"""Compatibility contracts for Zaero extensions to stock map entities.

These deterministic models lock the source-derived boundary behavior while the
game DLL integration assertions ensure the models and JSON save fields remain
wired into the Rerelease implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MAX_QPATH = 64
MAX_TIMER_TARGETS = 16
ZAERO_PUSH_START_OFF = 2
ZAERO_PUSH_NO_SOUND = 4


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
        self.assertIn("if (!level.is_zaero && self->spawnflags.has(SPAWNFLAG_PUSH_PLUS))", source)
        self.assertIn("self->spawnflags ^= SPAWNFLAG_PUSH_ZAERO_START_OFF", source)
        self.assertIn("other->client && self->message", source)


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
            "if (!level.is_zaero && ent->spawnflags.has(SPAWNFLAG_ROTATING_ACCEL))",
            functions,
        )
        self.assertIn("make_savable_memory<uint8_t, TAG_LEVEL>", functions)
        self.assertIn("if (!level.is_zaero || !self->target", functions)


if __name__ == "__main__":
    unittest.main()
