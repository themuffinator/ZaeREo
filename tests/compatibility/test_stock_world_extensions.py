"""Source and mapper contracts for Zaero extensions to stock world entities."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
MISC = (ROOT / "src" / "g_misc.cpp").read_text(encoding="utf-8")
TARGET = (ROOT / "src" / "g_target.cpp").read_text(encoding="utf-8")
FUNC = (ROOT / "src" / "g_func.cpp").read_text(encoding="utf-8")
AUDIT = json.loads(
    (ROOT / "docs" / "audits" / "bsp-entities.json").read_text(encoding="utf-8")
)

VIPER_SMOKE = 1
VIPER_SOLID = 2
VIPER_CUSTOM_BOUNDS = 4
DOOR_ACTIVE_TOGGLE = 1
DOOR_ACTIVE_ON = 2


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


@dataclass(frozen=True)
class ViperPresentation:
    flags_after_spawn: int
    smoke: bool
    solid: bool
    model: str
    attachments: tuple[str | None, str | None, str | None]
    mins: tuple[int, int, int]
    maxs: tuple[int, int, int]


def spawn_viper(
    *,
    flags: int,
    model: str | None = None,
    model2: str | None = None,
    model3: str | None = None,
    model4: str | None = None,
    mins: tuple[int, int, int] = (0, 0, 0),
    maxs: tuple[int, int, int] = (0, 0, 0),
) -> ViperPresentation:
    smoke = bool(flags & VIPER_SMOKE)
    if smoke:
        flags &= ~VIPER_SMOKE
    if not flags & VIPER_CUSTOM_BOUNDS:
        mins = (-16, -16, 0)
        maxs = (16, 16, 32)
    return ViperPresentation(
        flags_after_spawn=flags,
        smoke=smoke,
        solid=bool(flags & VIPER_SOLID),
        model=model or "models/ships/viper/tris.md2",
        attachments=(model2, model3, model4),
        mins=mins,
        maxs=maxs,
    )


@dataclass(frozen=True)
class DoorPart:
    active: int
    touch: str | None


def toggle_door_eligibility(parts: tuple[DoorPart, ...]) -> tuple[DoorPart, ...]:
    if not parts or not parts[0].active & DOOR_ACTIVE_TOGGLE:
        return parts
    toggled = []
    for part in parts:
        if part.active & DOOR_ACTIVE_ON:
            toggled.append(
                DoorPart(part.active & ~DOOR_ACTIVE_ON, "door_touch")
            )
        else:
            toggled.append(DoorPart(part.active | DOOR_ACTIVE_ON, None))
    return tuple(toggled)


def zaero_door_spawn_path(*, health: int, targetname: bool, active: int) -> str:
    if not active & DOOR_ACTIVE_TOGGLE:
        active = 0
    if (health or targetname) and not active & DOOR_ACTIVE_TOGGLE:
        return "Think_CalcMoveSpeed"
    return "Think_SpawnDoorTrigger"


def zaero_door_trigger_accepts(active: int) -> bool:
    return not active & DOOR_ACTIVE_TOGGLE or bool(active & DOOR_ACTIVE_ON)


class MiscViperTests(unittest.TestCase):
    def test_smoke_is_consumed_before_train_logic(self) -> None:
        viper = spawn_viper(flags=VIPER_SMOKE)
        self.assertTrue(viper.smoke)
        self.assertEqual(viper.flags_after_spawn, 0)
        self.assertFalse(viper.solid)

        body = function_body(MISC, "void SP_misc_viper(edict_t *ent)")
        effect = body.index("ent->s.effects |= EF_ROCKET")
        consume = body.index(
            "ent->spawnflags &= ~SPAWNFLAG_VIPER_ZAERO_SMOKE"
        )
        train = body.index("ent->think = func_train_find")
        self.assertLess(effect, consume)
        self.assertLess(consume, train)

    def test_shipped_bulldog_keeps_solid_custom_bounds_and_parts(self) -> None:
        viper = spawn_viper(
            flags=6,
            model="models/ships/bulldog_l/main/tris.md2",
            model2="models/ships/bulldog_l/right/tris.md2",
            model3="models/ships/bulldog_l/left/tris.md2",
            mins=(-210, -456, -32),
            maxs=(210, 156, 160),
        )
        self.assertFalse(viper.smoke)
        self.assertTrue(viper.solid)
        self.assertEqual(viper.mins, (-210, -456, -32))
        self.assertEqual(viper.maxs, (210, 156, 160))
        self.assertEqual(
            viper.attachments[:2],
            (
                "models/ships/bulldog_l/right/tris.md2",
                "models/ships/bulldog_l/left/tris.md2",
            ),
        )

    def test_all_attachment_slots_and_stock_fallback_are_explicit(self) -> None:
        body = function_body(MISC, "void SP_misc_viper(edict_t *ent)")
        self.assertIn("if (level.is_zaero)", body)
        for number in (2, 3, 4):
            self.assertIn(f"ent->s.modelindex{number} = gi.modelindex(ent->model{number})", body)
        self.assertIn(
            'ent->s.modelindex = gi.modelindex("models/ships/viper/tris.md2")',
            body,
        )


class TargetExplosionTests(unittest.TestCase):
    def test_shipped_flag_one_pattern_is_cosmetic_only(self) -> None:
        # The only three bit-1 placements are zbase2's 300/400/500 damage
        # finale sequence at delays 0/.1/.2.  Presentation must not alter it.
        shipped = ((300, 0.0), (400, 0.1), (500, 0.2))
        self.assertEqual(sum(damage for damage, _ in shipped), 1200)
        self.assertEqual([delay for _, delay in shipped], [0.0, 0.1, 0.2])

        body = function_body(
            TARGET, "THINK(target_explosion_explode) (edict_t *self) -> void"
        )
        cosmetic = body.index("if (level.is_zaero")
        damage = body.index("T_RadiusDamage")
        targets = body.index("G_UseTargets")
        self.assertLess(cosmetic, damage)
        self.assertLess(damage, targets)
        self.assertEqual(body.count("T_RadiusDamage"), 1)
        self.assertEqual(body.count("G_UseTargets"), 1)
        self.assertNotIn("self->active", body)

    def test_a2k_animation_and_sound_match_supplied_six_tenth_sequence(self) -> None:
        body = function_body(
            TARGET, "THINK(target_explosion_explode) (edict_t *self) -> void"
        )
        self.assertIn("weapons/a2k/ak_exp01.wav", body)
        self.assertIn("models/objects/b_explode/tris.md2", body)
        self.assertIn("self->s.skinnum = 6", body)
        self.assertIn("self->s.frame = 0", body)
        self.assertIn("level.time + 10_hz", body)

        animation = function_body(
            TARGET,
            "THINK(target_explosion_explode_think) (edict_t *self) -> void",
        )
        self.assertIn("if (self->s.frame >= 5)", animation)
        self.assertIn("self->svflags |= SVF_NOCLIENT", animation)
        self.assertIn("self->s.frame++", animation)
        self.assertIn("self->s.skinnum++", animation)
        self.assertIn("level.time + 10_hz", animation)

    def test_callbacks_and_target_restore_are_save_and_generation_safe(self) -> None:
        for callback in (
            "target_explosion_explode_think",
            "target_explosion_explode",
        ):
            self.assertIn(f"THINK({callback})", TARGET)
        self.assertIn("USE(use_target_explosion)", TARGET)

        body = function_body(
            TARGET, "THINK(target_explosion_explode) (edict_t *self) -> void"
        )
        self.assertIn("const int32_t spawn_count = self->spawn_count", body)
        self.assertIn("self->inuse && self->spawn_count == spawn_count", body)
        use = function_body(
            TARGET,
            "USE(use_target_explosion) (edict_t *self, edict_t *other, edict_t *activator) -> void",
        )
        self.assertIn("gtime_t::from_sec(self->delay)", use)


class FuncDoorTests(unittest.TestCase):
    def test_bit_one_use_toggles_touch_and_bit_two_across_team(self) -> None:
        initial = (
            DoorPart(3, None),
            DoorPart(3, None),
            DoorPart(1, "door_touch"),
        )
        disabled = toggle_door_eligibility(initial)
        self.assertEqual(
            disabled,
            (
                DoorPart(1, "door_touch"),
                DoorPart(1, "door_touch"),
                DoorPart(3, None),
            ),
        )
        self.assertEqual(toggle_door_eligibility(disabled), initial)

        body = function_body(
            FUNC,
            "USE(door_use) (edict_t *self, edict_t *other, edict_t *activator) -> void",
        )
        active_branch = body.index("if (level.is_zaero")
        move_branch = body.index("door_openclose(self, other, activator)")
        self.assertLess(active_branch, move_branch)
        self.assertIn("for (edict_t *ent = self; ent; ent = ent->teamchain)", body)
        self.assertIn("ent->touch = door_touch", body)
        self.assertIn("ent->touch = nullptr", body)
        self.assertIn("return;", body[active_branch:move_branch])

        movement = function_body(
            FUNC,
            "void door_openclose(edict_t *self, edict_t *other, edict_t *activator)",
        )
        self.assertIn("if (self->flags & FL_TEAMSLAVE)", movement)
        self.assertIn("SPAWNFLAG_DOOR_TOGGLE", movement)

    def test_inactive_auto_trigger_is_ignored_without_consuming_debounce(self) -> None:
        self.assertFalse(zaero_door_trigger_accepts(1))
        self.assertTrue(zaero_door_trigger_accepts(3))
        self.assertTrue(zaero_door_trigger_accepts(0))

        body = function_body(
            FUNC,
            "TOUCH(Touch_DoorTrigger) (edict_t *self, edict_t *other, const trace_t &tr, bool other_touching_self) -> void",
        )
        gate = body.index("self->owner->active & ZAERO_DOOR_ACTIVE_TOGGLE")
        debounce = body.index("self->touch_debounce_time = level.time + 1_sec")
        move = body.index("door_openclose(self->owner, other, other)")
        self.assertLess(gate, debounce)
        self.assertLess(debounce, move)
        self.assertIn("self->owner->spawn_count != self->count", body)

        # The supplied Zaero trigger bypasses door_use's eligibility toggle;
        # an enabled auto-trigger opens the door instead of disabling itself.
        door_use = function_body(
            FUNC,
            "USE(door_use) (edict_t *self, edict_t *other, edict_t *activator) -> void",
        )
        self.assertIn("door_openclose(self, other, activator)", door_use)
        self.assertNotIn("door_use(self->owner", body)

        spawn = function_body(
            FUNC, "THINK(Think_SpawnDoorTrigger) (edict_t *ent) -> void"
        )
        self.assertIn("other->count = ent->spawn_count", spawn)

        door_touch = function_body(
            FUNC,
            "TOUCH(door_touch) (edict_t *self, edict_t *other, const trace_t &tr, bool other_touching_self) -> void",
        )
        self.assertIn("if (!self->message)", door_touch)

    def test_zaero_spawn_path_uses_active_before_health_or_targetname(self) -> None:
        self.assertEqual(
            zaero_door_spawn_path(health=0, targetname=True, active=0),
            "Think_CalcMoveSpeed",
        )
        self.assertEqual(
            zaero_door_spawn_path(health=100, targetname=False, active=0),
            "Think_CalcMoveSpeed",
        )
        for active in (1, 3):
            self.assertEqual(
                zaero_door_spawn_path(
                    health=0, targetname=True, active=active
                ),
                "Think_SpawnDoorTrigger",
            )

        body = function_body(FUNC, "void SP_func_door(edict_t *ent)")
        self.assertIn("if (level.is_zaero)", body)
        self.assertIn("ent->active = 0", body)
        self.assertIn(
            "(ent->health || ent->targetname) && !(ent->active & ZAERO_DOOR_ACTIVE_TOGGLE)",
            body,
        )
        self.assertIn(
            "else if (ent->spawnflags.has(SPAWNFLAG_DOOR_START_OPEN))",
            body,
        )


class ShippedMapPatternTests(unittest.TestCase):
    def test_normalized_audit_locks_counts_maps_and_active_values(self) -> None:
        global_data = AUDIT["global"]
        self.assertEqual(global_data["classname_counts"]["misc_viper"], 7)
        self.assertEqual(global_data["classname_counts"]["target_explosion"], 35)
        self.assertEqual(global_data["classname_counts"]["func_door"], 318)
        self.assertEqual(
            global_data["classname_maps"]["misc_viper"],
            ["zbase1", "zboss", "zdef4"],
        )
        self.assertEqual(
            global_data["classname_maps"]["target_explosion"],
            ["zbase1", "zbase2", "zdef3", "ztomb1", "ztomb3", "zwaste3"],
        )
        self.assertEqual(
            global_data["value_counts"]["active"],
            {"0": 81, "1": 37, "3": 16},
        )


if __name__ == "__main__":
    unittest.main()
