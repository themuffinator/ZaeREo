from __future__ import annotations

import math
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCAL = (ROOT / "src" / "g_local.h").read_text(encoding="utf-8")
PHYS = (ROOT / "src" / "g_phys.cpp").read_text(encoding="utf-8")
SAVE = (ROOT / "src" / "g_save.cpp").read_text(encoding="utf-8")


class ZaeroPhysicsContractTests(unittest.TestCase):
    def test_custom_movetypes_preserve_native_save_ids_and_dispatch(self) -> None:
        enum = re.search(r"enum movetype_t\s*\{(?P<body>.*?)\n\};", LOCAL, re.S)
        self.assertIsNotNone(enum)
        body = enum.group("body")

        ordered = [
            "MOVETYPE_NEWTOSS",
            "MOVETYPE_BOUNCEFLY",
            "MOVETYPE_FALLFLOAT",
            "MOVETYPE_RIDE",
        ]
        positions = [body.index(name) for name in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("MOVETYPE_NEWTOSS == 11", LOCAL)

        for name in ordered[1:]:
            self.assertRegex(PHYS, rf"case\s+{name}\s*:")

    def test_bouncefly_is_gravity_free_and_restores_incident_speed(self) -> None:
        self.assertRegex(
            PHYS,
            r"ent->movetype\s*!=\s*MOVETYPE_BOUNCEFLY[\s\S]*?SV_AddGravity\(ent\)",
        )
        self.assertIn("bouncefly_speed", PHYS)
        self.assertIn("ent->velocity.normalize()", PHYS)
        self.assertIn("ent->velocity *= bouncefly_speed", PHYS)
        self.assertRegex(
            PHYS,
            r"MOVETYPE_WALLBOUNCE\s*\|\|\s*ent->movetype\s*==\s*MOVETYPE_BOUNCEFLY",
        )

        # A perfect reflection changes direction, not magnitude.
        incident = (300.0, 400.0, 0.0)
        reflected = (-incident[0], incident[1], incident[2])
        self.assertAlmostEqual(math.dist((0.0, 0.0, 0.0), incident), 500.0)
        self.assertAlmostEqual(
            math.dist((0.0, 0.0, 0.0), reflected),
            math.dist((0.0, 0.0, 0.0), incident),
        )

    def test_fallfloat_time_scaling_matches_the_legacy_tenth_second(self) -> None:
        self.assertIn("ZAERO_REFERENCE_FRAME_SECONDS = 0.1f", PHYS)
        self.assertIn("frame_seconds / ZAERO_REFERENCE_FRAME_SECONDS", PHYS)
        self.assertIn("gravity_acceleration * frame_seconds", PHYS)
        self.assertIn("displaced_mass > 0.f", PHYS)
        self.assertIn("max(1.f, static_cast<float>(ent->mass))", PHYS)
        self.assertIn("malformed zero-volume object now sinks normally", PHYS)
        self.assertIn("legacy_was_on_ground = ent->groundentity == nullptr", PHYS)

        reference_step = 0.1
        rerelease_step = 0.025
        damping_at_40_hz = 0.7 ** (rerelease_step / reference_step)
        self.assertAlmostEqual(damping_at_40_hz**4, 0.7, places=7)

        gravity = 800.0
        legacy_velocity_delta = gravity * reference_step
        rerelease_velocity_delta = 4 * gravity * rerelease_step
        self.assertAlmostEqual(rerelease_velocity_delta, legacy_velocity_delta)

        legacy_threshold_per_second = 4.0 / reference_step
        self.assertAlmostEqual(legacy_threshold_per_second, 40.0)

    def test_riders_are_bounded_generation_safe_and_saved(self) -> None:
        self.assertIn("ZAERO_MAX_RIDERS = 2", LOCAL)
        for field in (
            "ride_with",
            "ride_with_offset",
            "ride_with_spawn_count",
        ):
            self.assertIn(f"FIELD_AUTO({field})", SAVE)

        self.assertIn("rider->spawn_count != carrier->ride_with_spawn_count[slot]", PHYS)
        self.assertIn("slot >= edict_t::ZAERO_MAX_RIDERS", PHYS)
        self.assertIn("moved < pushed_p", PHYS)
        self.assertRegex(
            PHYS,
            r"every part of the pusher team succeeds[\s\S]*?SV_AdjustZaeroRiders\(moved->ent\)[\s\S]*?SV_RunThink",
        )


if __name__ == "__main__":
    unittest.main()
