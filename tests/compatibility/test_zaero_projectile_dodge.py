"""Static and golden contracts for Zaero's projectile-dodge throttle."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCAL = (ROOT / "src" / "g_local.h").read_text(encoding="utf-8")
SAVE = (ROOT / "src" / "g_save.cpp").read_text(encoding="utf-8")
MONSTER = (ROOT / "src" / "g_monster.cpp").read_text(encoding="utf-8")
STOCK_WEAPON = (ROOT / "src" / "g_weapon.cpp").read_text(encoding="utf-8")
ZAERO_WEAPON = (
    ROOT / "src" / "zaero" / "g_zaero_weapons.cpp"
).read_text(encoding="utf-8")
ZAERO_HEADER = (
    ROOT / "src" / "zaero" / "g_zaero_weapons.h"
).read_text(encoding="utf-8")
SOURCE_AUDIT = json.loads(
    (ROOT / "docs" / "audits" / "source-delta.json").read_text(encoding="utf-8")
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


class ZaeroProjectileDodgeContractTests(unittest.TestCase):
    def test_supplied_source_oracles_are_identity_locked(self) -> None:
        expected = {
            "g_weapon.c": (
                "e3b24b2a959d8db4be77ad084b22a587109a3d643aebd9c84e13d0105dd1203b",
                "modified",
            ),
            "z_weapon.c": (
                "bd23c9d99bb4d7d5af6a0e329aa30db7baafc155a3d5cf0814166576e5669d90",
                "zaero_only",
            ),
        }
        records = {
            record["path"]: record
            for record in SOURCE_AUDIT["comparison"]["file_records"]
        }
        for path, (digest, status) in expected.items():
            self.assertEqual(records[path]["zaero_sha256"], digest)
            self.assertEqual(records[path]["status"], status)

    def test_timeout_flag_and_typed_deadline_round_trip_in_json(self) -> None:
        self.assertRegex(LOCAL, r"AI_ZAERO_DODGE_TIMEOUT\s*=\s*bit_v<43>")
        self.assertIn("gtime_t zaero_dodge_timeout;", LOCAL)
        self.assertEqual(
            SAVE.count("FIELD_AUTO( monsterinfo.zaero_dodge_timeout )"), 1
        )
        self.assertIn("FIELD_AUTO(monsterinfo.aiflags)", SAVE)

    def test_helper_preserves_trace_eligibility_and_easy_gate(self) -> None:
        self.assertIn("void Zaero_CheckProjectileDodge", ZAERO_HEADER)
        body = function_body(ZAERO_WEAPON, "void Zaero_CheckProjectileDodge")
        for contract in (
            "!level.zaero_mapper_contract",
            "!self->client",
            "speed <= 0",
            "skill->value == 0.0f && frandom() > 0.25f",
            "dir * 8192.0f",
            "gi.traceline(start, end, self, MASK_SHOT)",
            "target->svflags & SVF_MONSTER",
            "target->health <= 0",
            "!target->monsterinfo.dodge",
            "!infront(target, self)",
        ):
            self.assertIn(contract, body)
        self.assertIn("travel.length() - target->maxs[0]", body)
        self.assertIn(
            "target->monsterinfo.dodge(target, self, eta, &tr, false)", body
        )

    def test_two_stage_timeout_order_and_golden_skill_durations(self) -> None:
        body = function_body(ZAERO_WEAPON, "void Zaero_CheckProjectileDodge")
        clear = body.index("aiflags &= ~AI_ZAERO_DODGE_TIMEOUT")
        zero = body.index("zaero_dodge_timeout = 0_ms", clear)
        initial = body.index("zaero_dodge_timeout == 0_ms", zero)
        rearm = body.index("level.time > target->monsterinfo.zaero_dodge_timeout")
        set_flag = body.index("aiflags |= AI_ZAERO_DODGE_TIMEOUT", rearm)
        self.assertLess(clear, zero)
        self.assertLess(zero, initial)
        self.assertLess(initial, rearm)
        self.assertLess(rearm, set_flag)
        self.assertIn("std::min(skill->integer, 3)", body)
        self.assertIn("(4 - skill_level) * 1.1f", body)
        self.assertIn("skill_level * 4.0f", body)
        self.assertIn(
            "level.time <= target->monsterinfo.zaero_dodge_timeout", body
        )

        initial_seconds = [(4 - skill) * 1.1 for skill in range(4)]
        armed_seconds = [skill * 4 for skill in range(4)]
        self.assertEqual(initial_seconds, [4.4, 3.3000000000000003, 2.2, 1.1])
        self.assertEqual(armed_seconds, [0, 4, 8, 12])

    def test_only_client_rocket_bfg_and_flare_use_legacy_firing_trace(self) -> None:
        rocket = function_body(STOCK_WEAPON, "edict_t *fire_rocket")
        bfg = function_body(STOCK_WEAPON, "void fire_bfg")
        blaster = function_body(STOCK_WEAPON, "void fire_blaster")
        flare = function_body(ZAERO_WEAPON, "edict_t *Zaero_SpawnFlare")
        call = "Zaero_CheckProjectileDodge"
        self.assertEqual(rocket.count(call), 1)
        self.assertEqual(bfg.count(call), 1)
        self.assertEqual(flare.count(call), 1)
        self.assertNotIn(call, blaster)
        self.assertLess(rocket.index(call), rocket.index("gi.linkentity(rocket)"))
        self.assertLess(bfg.index(call), bfg.index("gi.linkentity(bfg)"))
        self.assertLess(flare.index(call), flare.index("gi.linkentity(flare)"))

    def test_zaero_maps_do_not_also_run_native_proximity_dodge(self) -> None:
        think = function_body(MONSTER, "THINK(monster_think)")
        condition = re.search(
            r"if \(!level\.zaero_mapper_contract && self->health > 0 && "
            r"self->monsterinfo\.dodge &&\s*"
            r"!\(globals\.server_flags & SERVER_FLAG_LOADING\)\)\s*"
            r"M_CheckDodge\(self\);",
            think,
        )
        self.assertIsNotNone(condition)
        self.assertIn("if (self->monsterinfo.dodge_time > level.time)", MONSTER)


if __name__ == "__main__":
    unittest.main()
