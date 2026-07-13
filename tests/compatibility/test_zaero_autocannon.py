"""Legacy-evidence and source contracts for Zaero's multipart autocannons."""

from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = ROOT / "src" / "zaero" / "g_zaero_autocannon.cpp"
HEADER_PATH = ROOT / "src" / "zaero" / "g_zaero_autocannon.h"
SOURCE = SOURCE_PATH.read_text(encoding="utf-8")
HEADER = HEADER_PATH.read_text(encoding="utf-8")
LOCAL = (ROOT / "src" / "g_local.h").read_text(encoding="utf-8")
SAVE = (ROOT / "src" / "g_save.cpp").read_text(encoding="utf-8")
SPAWN = (ROOT / "src" / "g_spawn.cpp").read_text(encoding="utf-8")
CLIENT = (ROOT / "src" / "p_client.cpp").read_text(encoding="utf-8")
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


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def source_delta_record(path: str) -> dict[str, object]:
    files = SOURCE_AUDIT["comparison"]["file_records"]
    return next(record for record in files if record["path"] == path)


# Normalized from supplied z_acannon.c (source audit SHA below). These tables
# are small enough to serve as an independent cadence oracle.
FIRING = {
    1: (
        (False, False, 11),
        (False, False, 11),
        (False, False, 11),
        (False, False, 11),
        (False, False, 11),
        (False, False, 11),
        (False, True, 11),
        (False, False, 12),
        (False, True, 13),
        (False, False, 14),
        (False, True, 15),
        (False, False, 16),
        (False, True, 17),
        (False, False, 18),
        (False, True, 19),
        (False, False, 20),
        (False, True, 21),
        (True, False, 2),
    ),
    2: (
        *((False, False, 11),) * 6,
        (False, True, 11),
        (False, False, 11),
        (False, False, 12),
        (False, False, 12),
        (False, False, 13),
        (False, False, 13),
        (False, False, 14),
        (False, False, 14),
        (False, False, 15),
        (False, False, 15),
        (False, False, 16),
        (True, False, 16),
    ),
    3: (
        *((False, False, 11),) * 6,
        (False, True, 11),
        *((False, False, 11),) * 4,
        (True, False, 11),
    ),
    4: (
        *((False, False, 11),) * 6,
        (False, True, 11),
        *((False, False, 11),) * 10,
        (True, False, 11),
    ),
}


def firing_ticks(style: int, ticks: int) -> list[int]:
    sequence = FIRING[style]
    index = 0
    fired: list[int] = []
    for tick in range(ticks):
        last, fire, _ = sequence[index]
        if fire:
            fired.append(tick)
        index = 6 if last else index + 1
    return fired


class EvidenceTests(unittest.TestCase):
    def test_implementation_is_tied_to_the_audited_legacy_source_revision(self) -> None:
        record = source_delta_record("z_acannon.c")
        self.assertEqual(record["status"], "zaero_only")
        self.assertEqual(record["additions"], 919)
        self.assertEqual(
            record["zaero_sha256"],
            "156f834e729ec02287b0ac9e592a5e1041c791b0933f1d7d1de5e5c2a29f615b",
        )

    def test_all_shipped_classname_counts_and_maps_are_locked(self) -> None:
        global_audit = BSP_AUDIT["global"]
        self.assertEqual(
            global_audit["classname_counts"]["monster_autocannon"], 13
        )
        self.assertEqual(
            global_audit["classname_counts"]["monster_autocannon_floor"], 2
        )
        self.assertEqual(
            global_audit["classname_maps"]["monster_autocannon"],
            ["zdef2", "zdef3", "zdef4", "ztomb2", "zwaste1", "zwaste2"],
        )
        self.assertEqual(
            global_audit["classname_maps"]["monster_autocannon_floor"],
            ["ztomb3"],
        )

        # Direct extraction from the same audited retail PAK revision found
        # five ceiling style-4 placements and two floor style-4 placements;
        # all floor cannons therefore exercise the old four-entry idle-table
        # overrun that this port resolves deterministically. In the audited
        # gamei386.so, nm places turretIdle at 0x7b4bc and the zero-valued
        # turretIdleStart at 0x7b4cc, exactly the address read by index four.
        shipped_style_4 = {"ceiling": 5, "floor": 2}
        self.assertEqual(sum(shipped_style_4.values()), 7)

        assets = json.loads(
            (ROOT / "docs" / "audits" / "assets.json").read_text(
                encoding="utf-8"
            )
        )
        elf = next(
            record
            for record in assets["loose_install_files"]
            if record["path"] == "gamei386.so"
        )
        self.assertEqual(
            elf["sha256"],
            "db0fab26d46a74314142b6a1c268fd4986450932588352bd89c772b3964a3d12",
        )


class SpawnAndAssemblyTests(unittest.TestCase):
    def test_both_exact_mapper_classnames_have_entry_points(self) -> None:
        for name in (
            "SP_monster_autocannon",
            "SP_monster_autocannon_floor",
        ):
            self.assertIn(f"void {name}(edict_t *self);", HEADER)
            self.assertIn(f"void {name}(edict_t *self)", SOURCE)

    def test_spawnflags_style_defaults_and_difficulty_transform_match(self) -> None:
        for declaration in (
            "SPAWNFLAG_AUTOCANNON_START_OFF = 1_spawnflag",
            "SPAWNFLAG_AUTOCANNON_BERSERK = 2_spawnflag",
            "SPAWNFLAG_AUTOCANNON_BERSERK_TOGGLE = 4_spawnflag",
        ):
            self.assertIn(declaration, SOURCE)

        ceiling = function_body(SOURCE, "void SP_monster_autocannon(edict_t *self)")
        self.assertIn("if (deathmatch->integer)", ceiling)
        self.assertIn("if (self->style < 1 || self->style > 4)", ceiling)
        self.assertIn("self->style = 1", ceiling)
        self.assertIn("skill->value >= 2.0f && self->style == 4", ceiling)
        self.assertIn("self->style = 3", ceiling)

        floor = function_body(
            SOURCE, "void SP_monster_autocannon_floor(edict_t *self)"
        )
        fatal = floor.index("self->style == 1")
        fallback = floor.index("self->style < 1 || self->style > 4")
        delegate = floor.index("SP_monster_autocannon(self)")
        self.assertLess(fatal, fallback)
        self.assertLess(fallback, delegate)
        self.assertIn(
            'gi.Com_Error("monster_autocannon_floor does not permit bullet style")',
            floor,
        )
        self.assertIn("self->style = 2", floor)

    def test_three_piece_models_offsets_bounds_and_nonmonster_quirk_are_exact(self) -> None:
        body = function_body(SOURCE, "void SP_monster_autocannon(edict_t *self)")
        for value in (
            'base->classname = "autocannon base"',
            'turret->classname = "autocannon turret"',
            '"models/objects/acannon/base/tris.md2"',
            '"models/objects/acannon/base2/tris.md2"',
            '"models/objects/acannon/turret/tris.md2"',
            '"models/objects/acannon/turret2/tris.md2"',
            "self->s.origin[2] += on_floor ? 20.0f : -20.0f",
            "self->mins = { -12.0f, -12.0f, -16.0f }",
            "self->maxs = { 12.0f, 12.0f, 28.0f }",
            "self->mins = { -12.0f, -12.0f, -28.0f }",
            "self->maxs = { 12.0f, 12.0f, 16.0f }",
        ):
            self.assertIn(value, body)
        self.assertNotIn("SVF_MONSTER", body)
        self.assertNotIn("M_AllowSpawn", body)

    def test_floor_base_uses_generation_safe_two_child_ride_contract(self) -> None:
        spawn = function_body(SOURCE, "void SP_monster_autocannon(edict_t *self)")
        self.assertIn("on_floor ? MOVETYPE_RIDE : MOVETYPE_NONE", spawn)
        self.assertIn("turret->chain = base", spawn)
        self.assertIn("self->chain = turret", spawn)
        self.assertIn("G_SetZaeroRider(base, 0, turret)", spawn)
        self.assertIn("G_SetZaeroRider(base, 1, self)", spawn)

        validation = function_body(
            SOURCE,
            "bool Zaero_AutocannonRiderIsValid(const edict_t *base, size_t slot, const edict_t *rider)",
        )
        self.assertIn("slot < edict_t::ZAERO_MAX_RIDERS", validation)
        self.assertIn("base->ride_with[slot] == rider", validation)
        self.assertIn(
            "base->ride_with_spawn_count[slot] == rider->spawn_count",
            validation,
        )

    def test_lip_yaw_and_state_reuse_only_already_saved_fields(self) -> None:
        spawn = function_body(SOURCE, "void SP_monster_autocannon(edict_t *self)")
        self.assertIn(
            "static_cast<float>(static_cast<int32_t>(self->s.angles[YAW]))",
            spawn,
        )
        self.assertIn(
            "st.lip > 0.0f ? static_cast<int32_t>(st.lip) : 0", spawn
        )
        self.assertIn("self->count = 0; // legacy seq", spawn)

        for field in (
            "FIELD_AUTO(count)",
            "FIELD_AUTO(chain)",
            "FIELD_AUTO(enemy)",
            "FIELD_AUTO(oldenemy)",
            "FIELD_AUTO(timestamp)",
            "FIELD_AUTO(teleport_time)",
            "FIELD_AUTO(move_angles)",
            "FIELD_AUTO(monsterinfo.last_sighting)",
            "FIELD_AUTO(monsterinfo.lefty)",
            "FIELD_AUTO(monsterinfo.linkcount)",
            "FIELD_AUTO(active)",
            "FIELD_AUTO(ride_with)",
            "FIELD_AUTO(ride_with_offset)",
            "FIELD_AUTO(ride_with_spawn_count)",
        ):
            self.assertIn(field, SAVE)


class TargetingAndFireTests(unittest.TestCase):
    def test_target_filters_range_arc_pitch_and_berserk_scope_match(self) -> None:
        self.assertIn("AUTOCANNON_RANGE = 2048.0f", SOURCE)
        self.assertIn("AUTOCANNON_TIMEOUT = 2_sec", SOURCE)

        find = function_body(
            SOURCE, "void Zaero_AutocannonFindEnemy(edict_t *self)"
        )
        for contract in (
            "findradius(candidate, self->s.origin, AUTOCANNON_RANGE)",
            "!candidate->client && !(candidate->svflags & SVF_MONSTER)",
            "else if (!candidate->client)",
            "candidate->flags & FL_NOTARGET",
            'Q_strcasecmp(candidate->classname, "monster_autocannon")',
            "!visible(self, candidate)",
            "!Zaero_AutocannonInFront(self, candidate)",
            "level.time > self->timestamp",
        ):
            self.assertIn(contract, find)

        can_shoot = function_body(
            SOURCE,
            "bool Zaero_AutocannonCanShoot(edict_t *self, edict_t *candidate)",
        )
        self.assertIn("candidate_angles[PITCH] < 0.0f", can_shoot)
        self.assertIn("candidate_angles[PITCH] > 0.0f", can_shoot)
        self.assertIn("self->monsterinfo.linkcount > 0", can_shoot)
        self.assertIn("Zaero_AngleBetween", can_shoot)

        in_front = function_body(
            SOURCE,
            "bool Zaero_AutocannonInFront(edict_t *self, edict_t *other)",
        )
        self.assertIn("float minimum = -30.0f", in_front)
        self.assertIn("float maximum = 30.0f", in_front)

    def test_turning_retains_scan_pause_midpoint_and_mutating_wrap_quirks(self) -> None:
        turn = function_body(SOURCE, "void Zaero_AutocannonTurn(edict_t *self)")
        for contract in (
            "AUTOCANNON_TURN_SPEED = 6.0f",
            "AUTOCANNON_TURN_DELAY = 1_sec",
            "self->monsterinfo.lefty",
            "(self->enemy->mins + self->enemy->maxs) * 0.65f",
            "self->monsterinfo.last_sighting = destination",
            "self->timestamp = level.time + AUTOCANNON_TIMEOUT",
            "self->s.angles[PITCH] -= 4.0f",
            "self->s.angles[PITCH] += 4.0f",
        ):
            self.assertIn(contract, SOURCE if contract.startswith("AUTOCANNON_") else turn)

        angle_between = function_body(
            SOURCE,
            "bool Zaero_AngleBetween(float &angle, float &minimum, float &maximum)",
        )
        self.assertIn("while (angle < minimum)", angle_between)
        self.assertIn("angle += 360.0f", angle_between)
        self.assertNotIn("<=", angle_between)

        think = function_body(
            SOURCE, "THINK(Zaero_AutocannonThink) (edict_t *self) -> void"
        )
        self.assertIn("level.time > self->teleport_time", think)
        self.assertIn(
            "self->teleport_time = level.time + AUTOCANNON_TURN_DELAY", think
        )

    def test_weapon_parameters_offsets_effects_and_mod_hooks_are_exact(self) -> None:
        expected_constants = {
            "AUTOCANNON_BULLET_DAMAGE": "4",
            "AUTOCANNON_BULLET_KICK": "2",
            "AUTOCANNON_ROCKET_DAMAGE": "100",
            "AUTOCANNON_ROCKET_SPEED": "650",
            "AUTOCANNON_ROCKET_RADIUS_DAMAGE": "120",
            "AUTOCANNON_ROCKET_DAMAGE_RADIUS": "120.0f",
            "AUTOCANNON_BLASTER_DAMAGE": "20",
            "AUTOCANNON_BLASTER_SPEED": "1000",
        }
        for name, value in expected_constants.items():
            self.assertRegex(SOURCE, rf"{name}\s*=\s*{re.escape(value)};")

        offsets = compact(
            SOURCE[
                SOURCE.index("AUTOCANNON_FIRE_OFFSETS") : SOURCE.index(
                    "AUTOCANNON_MODELS"
                )
            ]
        )
        for offset in (
            "{24.0f,-4.0f,0.0f}",
            "{0.0f,-4.0f,0.0f}",
            "{24.0f,-5.0f,0.0f}",
        ):
            self.assertIn(offset, offsets)

        fire = function_body(SOURCE, "void Zaero_AutocannonFire(edict_t *self)")
        self.assertIn("axes.right = -axes.right", fire)
        self.assertIn("MOD_ZAERO_AUTOCANNON", fire)
        self.assertIn("EF_HYPERBLASTER,MOD_HYPERBLASTER", compact(fire))
        for flash in ("MZ_CHAINGUN2", "MZ_ROCKET", "MZ_HYPERBLASTER"):
            self.assertIn(f"Zaero_AutocannonMuzzleflash(self, {flash})", fire)

    def test_emp_suppression_uses_the_shared_query_and_legacy_misfire(self) -> None:
        fire = function_body(SOURCE, "void Zaero_AutocannonFire(edict_t *self)")
        self.assertLess(
            fire.index("Zaero_EMPNukeCheck(self, start)"),
            fire.index("switch (self->style)"),
        )
        self.assertIn("Zaero_PlayEMPMisfire(self)", fire)
        self.assertIn('#include "g_zaero_emp.h"', SOURCE)
        self.assertNotIn("Zaero_AutocannonEMPBlocked", SOURCE)

    def test_independent_legacy_animation_oracle_locks_fire_cadence(self) -> None:
        self.assertEqual(firing_ticks(1, 25), [6, 8, 10, 12, 14, 16, 18, 20, 22, 24])
        self.assertEqual(firing_ticks(2, 32), [6, 18, 30])
        self.assertEqual(firing_ticks(3, 25), [6, 12, 18, 24])
        self.assertEqual(firing_ticks(4, 32), [6, 18, 30])

        table = SOURCE[
            SOURCE.index("AUTOCANNON_FIRING_FRAMES") : SOURCE.index(
                "AUTOCANNON_FIRE_OFFSETS"
            )
        ]
        self.assertEqual(table.count("{ false, true,"), 9)
        self.assertEqual(table.count("{ true, false,"), 5)
        self.assertIn("frame.fire", SOURCE)
        self.assertIn(
            "self->count = frame.last ? 0 : self->count + 1", SOURCE
        )
        self.assertIn(
            "self->count = frame.last ? animation.first_non_pause : self->count + 1",
            SOURCE,
        )


class LifecycleAndSaveTests(unittest.TestCase):
    def test_shared_registry_mod_and_obituary_wiring_is_complete(self) -> None:
        for classname, callback in (
            ("monster_autocannon", "SP_monster_autocannon"),
            ("monster_autocannon_floor", "SP_monster_autocannon_floor"),
        ):
            self.assertEqual(
                len(
                    re.findall(
                        rf'\{{\s*"{classname}"\s*,\s*{callback}\s*\}}', SPAWN
                    )
                ),
                1,
            )
        self.assertIn("MOD_ZAERO_AUTOCANNON", LOCAL)
        self.assertIn("MOD_ZAERO_TRIPBOMB", LOCAL)
        self.assertIn("{} was in the wrong place\\n", CLIENT)
        self.assertIn("{} tripped over {}'s trip bomb\\n", CLIENT)

    def test_all_persistent_callbacks_are_named_save_registrations(self) -> None:
        callbacks = {
            "THINK": (
                "Zaero_AutocannonThink",
                "Zaero_AutocannonExplode",
                "Zaero_AutocannonActivate",
                "Zaero_AutocannonDeactivate",
                "Zaero_AutocannonUseStub",
            ),
            "USE": ("Zaero_AutocannonUse",),
            "PAIN": ("Zaero_AutocannonPain",),
            "DIE": ("Zaero_AutocannonDie",),
        }
        for macro, names in callbacks.items():
            for name in names:
                self.assertIn(f"{macro}({name})", SOURCE)

        self.assertIn("ZAERO_AUTOCANNON_TICK = 10_hz", SOURCE)
        for callback in (
            "Zaero_AutocannonThink",
            "Zaero_AutocannonActivate",
            "Zaero_AutocannonDeactivate",
        ):
            body = function_body(SOURCE, f"THINK({callback})")
            self.assertIn(
                "self->nextthink = level.time + ZAERO_AUTOCANNON_TICK", body
            )

    def test_death_is_delayed_and_preserves_tripbomb_attribution_and_base_debris(self) -> None:
        die = function_body(
            SOURCE,
            "DIE(Zaero_AutocannonDie) (edict_t *self, edict_t *inflictor, edict_t *attacker,",
        )
        self.assertIn("self->takedamage = false", die)
        self.assertIn("self->think = Zaero_AutocannonExplode", die)
        self.assertIn(
            "self->nextthink = level.time + ZAERO_AUTOCANNON_TICK", die
        )

        explode = function_body(
            SOURCE, "THINK(Zaero_AutocannonExplode) (edict_t *self) -> void"
        )
        self.assertIn("AUTOCANNON_EXPLOSION_DAMAGE = 150", SOURCE)
        self.assertIn("AUTOCANNON_EXPLOSION_RADIUS = 384.0f", SOURCE)
        self.assertIn(
            "AUTOCANNON_EXPLOSION_DAMAGE, self->enemy", explode
        )
        self.assertIn("MOD_ZAERO_TRIPBOMB", explode)
        for event in (
            "TE_GRENADE_EXPLOSION_WATER",
            "TE_ROCKET_EXPLOSION_WATER",
            "TE_GRENADE_EXPLOSION",
            "TE_ROCKET_EXPLOSION",
        ):
            self.assertIn(event, explode)
        self.assertIn("base->s.skinnum = 1", explode)
        self.assertIn("G_ClearZaeroRiders(base)", explode)
        self.assertIn("G_FreeEdict(turret)", explode)
        self.assertIn("G_FreeEdict(self)", explode)
        self.assertNotIn("G_FreeEdict(base)", explode)
        self.assertNotIn("ThrowGib", explode)

    def test_style_four_idle_quirk_is_bounded_and_explicit(self) -> None:
        match = re.search(
            r"TURRET_COLLAPSES_WHEN_IDLE\[5\]\s*=\s*\{(?P<body>[^}]+)\}",
            SOURCE,
        )
        self.assertIsNotNone(match)
        values = [value.strip() for value in match.group("body").split(",")]
        self.assertEqual(values, ["false", "false", "true", "true", "false"])
        self.assertIn(
            "preserves the retail frame quirk without retaining UB", SOURCE
        )


if __name__ == "__main__":
    unittest.main()
