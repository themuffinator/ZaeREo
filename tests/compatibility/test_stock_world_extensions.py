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
SPAWN = (ROOT / "src" / "g_spawn.cpp").read_text(encoding="utf-8")
SAVES = (ROOT / "src" / "g_save.cpp").read_text(encoding="utf-8")
AUDIT = json.loads(
    (ROOT / "docs" / "audits" / "bsp-entities.json").read_text(encoding="utf-8")
)
SOURCE_AUDIT = json.loads(
    (ROOT / "docs" / "audits" / "source-delta.json").read_text(encoding="utf-8")
)

VIPER_SMOKE = 1
VIPER_SOLID = 2
VIPER_CUSTOM_BOUNDS = 4
DOOR_ACTIVE_TOGGLE = 1
DOOR_ACTIVE_ON = 2
NON_DAMAGING_ROTATING_DOORS = {
    "zdef1": ((779, None), (780, None)),
    "zdef3": ((1392, None), (1393, None), (1397, "0")),
    "zdm5": ((56, None),),
    "ztomb2": ((292, None), (739, "0"), (1117, "0"), (1118, "0")),
    "zwaste1": ((231, "0"),),
    "zwaste3": ((188, "0"),),
}
PATH_CORNER_MAP_COUNTS = {
    "zbase1": (12, 5, 1),
    "zboss": (8, 3, 0),
    "zdef1": (47, 4, 0),
    "zdef2": (36, 11, 0),
    "zdef3": (67, 26, 3),
    "zdef4": (55, 4, 0),
    "ztomb1": (20, 9, 0),
    "ztomb2": (52, 14, 0),
    "ztomb3": (64, 18, 0),
    "zwaste1": (4, 2, 0),
    "zwaste2": (8, 0, 0),
    "zwaste3": (2, 0, 0),
}
PATH_CORNER_FLAG_COUNTS = {0: 78, 1: 3, 2048: 291, 2049: 1, 2816: 2}
FUNC_TRAIN_FLAG_COUNTS = {1: 5, 3: 20, 1793: 1, 2048: 1, 2050: 1}
ZDEF4_PATH_SPEEDS = {
    492: 110,
    493: 330,
    495: 500,
    496: 1000,
    1078: 5000,
}
TELEPORT_PATH_CORNERS = {
    "zbase1": ((63, 1),),
    "zdef3": ((907, 1), (1115, 1), (1736, 2049)),
}
ZERO_ASPEED_TRAINS = {
    "zdef3": (1956,),
    "ztomb2": (630, 632),
    "zwaste3": (189,),
}


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


@dataclass(frozen=True)
class SmoothTrainStep:
    remaining: float
    current_speed: float
    rate: float
    accelerating: bool
    velocity: float
    final: bool


def begin_zaero_smooth_step(
    *,
    remaining: float,
    target_speed: float,
    current_speed: float,
    corner_rate: float,
    train_decel: float = 0.0,
    automatic: bool,
) -> SmoothTrainStep:
    """Model the supplied DLL's immediate first 10 Hz smooth callback."""

    current_speed = current_speed or target_speed
    rate = corner_rate
    accelerating = target_speed > current_speed
    if target_speed > remaining:
        current_speed = target_speed
        rate = 0.0
    elif automatic:
        steps = remaining / ((target_speed + current_speed) * 0.5)
        rate = (target_speed - current_speed) / steps
    else:
        if train_decel < 0:
            rate = -rate
        if not accelerating:
            rate = -rate

    if remaining >= current_speed:
        remaining -= current_speed
    current_speed += rate
    if accelerating and current_speed > target_speed:
        current_speed = target_speed
    elif not accelerating and current_speed < target_speed:
        current_speed = target_speed

    final = remaining <= current_speed
    velocity = (remaining if final else current_speed) * 10.0
    return SmoothTrainStep(
        remaining,
        current_speed,
        rate,
        accelerating,
        velocity,
        final,
    )


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


def rotating_door_damage(authored: int | None, *, is_zaero_map: bool) -> int:
    value = authored or 0
    if value == 0 and not is_zaero_map:
        return 2
    return value


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
        self.assertIn("if (level.zaero_mapper_contract)", body)
        for number in (2, 3, 4):
            self.assertIn(f"ent->s.modelindex{number} = gi.modelindex(ent->model{number})", body)
        self.assertIn(
            'ent->s.modelindex = gi.modelindex("models/ships/viper/tris.md2")',
            body,
        )


class TrainPathCornerTests(unittest.TestCase):
    def test_source_identity_and_complete_shipped_inventory_are_locked(self) -> None:
        records = {
            record["path"]: record
            for record in SOURCE_AUDIT["comparison"]["file_records"]
        }
        self.assertEqual(
            records["g_func.c"]["zaero_sha256"],
            "aa7d05629c1213145e8fb74d14252d0b982b35cbc2dd4c75f1c27882f72adea6",
        )
        self.assertEqual(
            records["g_misc.c"]["zaero_sha256"],
            "60378a0a35864453e5d6a2e1a18a43cc73c327e28dc3a45a1bec087425515fe1",
        )
        self.assertEqual(
            AUDIT["global"]["classname_counts"]["path_corner"], 375
        )
        self.assertEqual(
            AUDIT["global"]["classname_counts"]["func_train"], 28
        )
        self.assertEqual(
            AUDIT["global"]["classname_counts"]["misc_viper"], 7
        )
        self.assertEqual(
            sum(counts[0] for counts in PATH_CORNER_MAP_COUNTS.values()), 375
        )
        self.assertEqual(
            sum(counts[1] for counts in PATH_CORNER_MAP_COUNTS.values()), 96
        )
        self.assertEqual(
            sum(counts[2] for counts in PATH_CORNER_MAP_COUNTS.values()), 4
        )
        self.assertEqual(sum(map(len, TELEPORT_PATH_CORNERS.values())), 4)
        self.assertEqual(len(ZDEF4_PATH_SPEEDS), 5)
        self.assertEqual(sum(map(len, ZERO_ASPEED_TRAINS.values())), 4)
        self.assertEqual(sum(PATH_CORNER_FLAG_COUNTS.values()), 375)
        self.assertFalse(
            any(flags & 6 for flags in PATH_CORNER_FLAG_COUNTS)
        )
        self.assertEqual(sum(FUNC_TRAIN_FLAG_COUNTS.values()), 28)
        self.assertFalse(
            any(flags & (8 | 16 | 32 | 64) for flags in FUNC_TRAIN_FLAG_COUNTS)
        )

    def test_per_corner_speed_accel_and_decel_preserve_zaero_state(self) -> None:
        self.assertEqual(
            ZDEF4_PATH_SPEEDS,
            {492: 110, 493: 330, 495: 500, 496: 1000, 1078: 5000},
        )
        body = function_body(
            FUNC, "THINK(train_next) (edict_t *self) -> void"
        )
        self.assertIn("if (ent->speed)", body)
        self.assertIn("self->moveinfo.speed = ent->speed", body)
        self.assertIn("self->moveinfo.accel = ent->accel", body)
        self.assertIn("self->moveinfo.accel = ent->speed", body)
        self.assertIn("self->moveinfo.decel = ent->decel", body)
        self.assertIn("self->moveinfo.decel = ent->speed", body)
        native = body.index("if (!level.zaero_mapper_contract)")
        self.assertIn("self->speed = ent->speed", body[native:])
        self.assertIn("self->moveinfo.current_speed = 0", body[native:])

    def test_misc_viper_uses_raw_origin_only_for_ordinary_next_segment(self) -> None:
        destination = function_body(
            FUNC,
            "static vec3_t train_destination(edict_t *self, edict_t *corner, bool allow_zaero_viper_origin)",
        )
        self.assertIn("if (level.zaero_mapper_contract)", destination)
        self.assertIn("allow_zaero_viper_origin", destination)
        self.assertIn('Q_strcasecmp(self->classname, "misc_viper") == 0', destination)
        self.assertIn("return corner->s.origin;", destination)
        self.assertIn("return corner->s.origin - self->mins;", destination)
        self.assertIn("SPAWNFLAG_TRAIN_USE_ORIGIN", destination)
        self.assertIn("SPAWNFLAG_TRAIN_FIX_OFFSET", destination)

        train_next = function_body(
            FUNC, "THINK(train_next) (edict_t *self) -> void"
        )
        self.assertEqual(
            train_next.count("train_destination(self, ent, true)"), 1
        )
        self.assertEqual(
            train_next.count("train_destination(self, ent, false)"), 1
        )
        self.assertIn(
            "train_destination(self, ent, false)",
            function_body(FUNC, "void train_resume(edict_t *self)"),
        )
        self.assertIn(
            "train_destination(self, ent, false)",
            function_body(FUNC, "THINK(func_train_find) (edict_t *self) -> void"),
        )

    def test_wait_turns_first_and_both_teleport_events_are_suppressed(self) -> None:
        corner = function_body(
            MISC,
            "TOUCH(path_corner_touch) (edict_t *self, edict_t *other, const trace_t &tr, bool other_touching_self) -> void",
        )
        wait = corner.index("if (self->wait)")
        yaw = corner.index("other->ideal_yaw = vectoyaw(v)", wait)
        pause = corner.index("other->monsterinfo.pausetime", wait)
        stand = corner.index("other->monsterinfo.stand(other)", wait)
        self.assertLess(yaw, pause)
        self.assertLess(pause, stand)
        self.assertIn("if (level.zaero_mapper_contract && other->goalentity)", corner)
        self.assertIn("if (!level.zaero_mapper_contract)\n\t\t\tother->s.event = EV_OTHER_TELEPORT", corner)

        train_next = function_body(
            FUNC, "THINK(train_next) (edict_t *self) -> void"
        )
        self.assertIn("if (!level.zaero_mapper_contract)\n\t\t\tself->s.event = EV_OTHER_TELEPORT", train_next)

    def test_auto_smooth_retains_10_hz_decisions_over_40_hz_motion(self) -> None:
        step = begin_zaero_smooth_step(
            remaining=2000.0,
            target_speed=300.0,
            current_speed=100.0,
            corner_rate=300.0,
            automatic=True,
        )
        self.assertEqual(step.remaining, 1900.0)
        self.assertEqual(step.current_speed, 120.0)
        self.assertEqual(step.rate, 20.0)
        self.assertEqual(step.velocity, 1200.0)
        self.assertFalse(step.final)
        distance_per_40_hz_tick = step.velocity * 0.025
        self.assertEqual(distance_per_40_hz_tick * 4, step.current_speed)

        short = begin_zaero_smooth_step(
            remaining=250.0,
            target_speed=300.0,
            current_speed=100.0,
            corner_rate=300.0,
            automatic=True,
        )
        self.assertTrue(short.final)
        self.assertEqual(short.velocity * 0.025 * 4, 250.0)

        calc = function_body(
            FUNC,
            "static void zaero_train_move_calc(edict_t *ent, const vec3_t &dest,",
        )
        self.assertIn("SPAWNFLAG_PATH_CORNER_ZAERO_AUTO_SMOOTH", calc)
        self.assertIn("SPAWNFLAG_PATH_CORNER_ZAERO_CUSTOM_SMOOTH", calc)
        self.assertIn("zaero_train_smooth_think(ent)", calc)
        think = function_body(
            FUNC, "THINK(zaero_train_smooth_think) (edict_t *ent) -> void"
        )
        self.assertIn("ent->moveinfo.current_speed * 10.0f", think)
        self.assertIn("level.time + 10_hz", think)
        final = function_body(
            FUNC, "static void zaero_train_smooth_final(edict_t *ent)"
        )
        self.assertIn(
            "ent->moveinfo.dir * (ent->moveinfo.remaining_distance * 10.0f)",
            final,
        )
        self.assertIn("level.time + 10_hz", final)

    def test_custom_smooth_and_rotation_bits_retain_native_fallback(self) -> None:
        step = begin_zaero_smooth_step(
            remaining=2000.0,
            target_speed=100.0,
            current_speed=300.0,
            corner_rate=25.0,
            automatic=False,
        )
        self.assertEqual(step.remaining, 1700.0)
        self.assertEqual(step.current_speed, 275.0)
        self.assertEqual(step.rate, -25.0)
        self.assertFalse(step.accelerating)

        for name, bit in (
            ("REVERSE", 8),
            ("X_AXIS", 16),
            ("Y_AXIS", 32),
            ("Z_AXIS", 64),
        ):
            self.assertIn(
                f"SPAWNFLAG_TRAIN_ZAERO_{name} = {bit}_spawnflag", FUNC
            )
        spawn = function_body(FUNC, "void SP_func_train(edict_t *self)")
        self.assertIn("if (level.zaero_mapper_contract)", spawn)
        self.assertIn("self->movedir = -self->movedir", spawn)
        self.assertIn("ent->avelocity = ent->movedir * ent->aspeed", FUNC)
        self.assertIn("if (level.zaero_mapper_contract)\n\t\tent->avelocity = {}", FUNC)

        train_next = function_body(
            FUNC, "THINK(train_next) (edict_t *self) -> void"
        )
        self.assertIn(
            "if (!level.zaero_mapper_contract && self->spawnflags.has(SPAWNFLAG_TRAIN_MOVE_TEAMCHAIN))",
            train_next,
        )
        fix_teams = function_body(SPAWN, "void G_FixTeams()")
        self.assertIn("if (!level.zaero_mapper_contract && !strcmp(e->classname, \"func_train\")", fix_teams)

    def test_smooth_callback_and_existing_mover_state_are_json_saveable(self) -> None:
        self.assertIn("THINK(zaero_train_smooth_think)", FUNC)
        for field in (
            "aspeed",
            "moveinfo.accel",
            "moveinfo.speed",
            "moveinfo.decel",
            "moveinfo.dir",
            "moveinfo.dest",
            "moveinfo.current_speed",
            "moveinfo.remaining_distance",
            "moveinfo.endfunc",
        ):
            self.assertIn(f"FIELD_AUTO({field})", SAVES)


class MiscExploboxTests(unittest.TestCase):
    def test_source_identity_and_all_31_shipped_placements_are_locked(self) -> None:
        records = {
            record["path"]: record
            for record in SOURCE_AUDIT["comparison"]["file_records"]
        }
        self.assertEqual(
            records["g_misc.c"]["zaero_sha256"],
            "60378a0a35864453e5d6a2e1a18a43cc73c327e28dc3a45a1bec087425515fe1",
        )
        self.assertEqual(records["g_misc.c"]["status"], "modified")

        counts = {
            record["map_name"]: record["classname_counts"].get(
                "misc_explobox", 0
            )
            for record in AUDIT["maps"]
            if record["classname_counts"].get("misc_explobox", 0)
        }
        self.assertEqual(
            counts,
            {
                "zbase1": 4,
                "zdef1": 2,
                "ztomb2": 6,
                "zwaste2": 7,
                "zwaste3": 12,
            },
        )
        self.assertEqual(sum(counts.values()), 31)

    def test_zaero_spawn_uses_fallfloat_mass_400_and_legacy_drop_start(self) -> None:
        body = function_body(MISC, "void SP_misc_explobox(edict_t *self)")
        self.assertIn(
            "self->movetype = level.zaero_mapper_contract ? MOVETYPE_FALLFLOAT : MOVETYPE_STEP",
            body,
        )
        self.assertIn("if (!self->mass)", body)
        self.assertIn("self->mass = level.zaero_mapper_contract ? 400 : 50", body)
        self.assertIn("self->monsterinfo.aiflags = AI_NOSTEP", body)
        self.assertIn("else\n\t\tself->flags |= FL_TRAP", body)
        self.assertIn("self->think = barrel_start", body)
        self.assertIn("level.zaero_mapper_contract ? 200_ms : 20_hz", body)

        start = function_body(
            MISC, "THINK(barrel_start) (edict_t *self) -> void"
        )
        drop = start.index("M_droptofloor(self)")
        zaero = start.index("if (level.zaero_mapper_contract)")
        native = start.index("self->think = barrel_think")
        self.assertLess(drop, zaero)
        self.assertLess(zaero, native)
        self.assertIn("self->think = nullptr", start[zaero:native])
        self.assertIn("self->nextthink = 0_ms", start[zaero:native])
        self.assertIn("return;", start[zaero:native])

    def test_zaero_touch_is_client_only_and_allows_airborne_pushers(self) -> None:
        body = function_body(
            MISC,
            "TOUCH(barrel_touch) (edict_t *self, edict_t *other, const trace_t &tr, bool other_touching_self) -> void",
        )
        native_start = body.index("\n\tfloat  ratio;")
        zaero = body[:native_start]
        native = body[native_start:]

        self.assertIn("if (level.zaero_mapper_contract)", zaero)
        self.assertIn("other->groundentity == self || !other->client", zaero)
        self.assertNotIn("!other->groundentity", zaero)
        self.assertNotIn("other_touching_self", zaero)
        self.assertIn("static_cast<float>(other->mass)", zaero)
        self.assertIn("static_cast<float>(self->mass)", zaero)
        self.assertIn("self->s.origin - other->s.origin", zaero)
        self.assertIn("20.0f * ratio * gi.frame_time_s", zaero)
        self.assertIn("SV_movestep(self, direction *", zaero)
        self.assertIn(", true);", zaero)

        # Native Rerelease barrels keep both their grounded-contact eligibility
        # and M_walkmove path on every non-Zaero map.
        self.assertIn("!other->groundentity", native)
        self.assertIn("!other_touching_self", native)
        self.assertIn("M_walkmove", native)

    def test_push_rate_is_tick_independent_and_preserves_mass_ratio(self) -> None:
        player_mass = 100.0
        barrel_mass = 400.0
        legacy_distance = 20.0 * (player_mass / barrel_mass) * 0.1
        target_tick_distance = 20.0 * (player_mass / barrel_mass) * 0.025
        self.assertEqual(legacy_distance, 0.5)
        self.assertEqual(target_tick_distance, 0.125)
        self.assertEqual(target_tick_distance * 4, legacy_distance)

    def test_existing_callbacks_and_explosion_path_remain_save_native(self) -> None:
        self.assertIn("TOUCH(barrel_touch)", MISC)
        self.assertIn("THINK(barrel_start)", MISC)
        self.assertIn("THINK(barrel_think)", MISC)
        self.assertIn("THINK(barrel_explode)", MISC)
        self.assertIn("DIE(barrel_delay)", MISC)
        self.assertIn("T_RadiusDamage", function_body(MISC, "THINK(barrel_explode)"))


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
        cosmetic = body.index("if (level.zaero_mapper_contract")
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
        active_branch = body.index("if (level.zaero_mapper_contract")
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
        self.assertIn("if (level.zaero_mapper_contract)", body)
        self.assertIn("ent->active = 0", body)
        self.assertIn(
            "(ent->health || ent->targetname) && !(ent->active & ZAERO_DOOR_ACTIVE_TOGGLE)",
            body,
        )
        self.assertIn(
            "else if (ent->spawnflags.has(SPAWNFLAG_DOOR_START_OPEN))",
            body,
        )


class RotatingDoorDamageTests(unittest.TestCase):
    def test_all_12_missing_or_zero_damage_placements_are_locked(self) -> None:
        records = {
            record["path"]: record
            for record in SOURCE_AUDIT["comparison"]["file_records"]
        }
        self.assertEqual(
            records["g_func.c"]["zaero_sha256"],
            "aa7d05629c1213145e8fb74d14252d0b982b35cbc2dd4c75f1c27882f72adea6",
        )
        self.assertEqual(
            sum(len(entries) for entries in NON_DAMAGING_ROTATING_DOORS.values()),
            12,
        )
        self.assertEqual(
            sum(
                value is None
                for entries in NON_DAMAGING_ROTATING_DOORS.values()
                for _, value in entries
            ),
            6,
        )
        self.assertEqual(
            sum(
                value == "0"
                for entries in NON_DAMAGING_ROTATING_DOORS.values()
                for _, value in entries
            ),
            6,
        )
        self.assertEqual(
            AUDIT["global"]["classname_counts"]["func_door_rotating"], 32
        )
        self.assertLessEqual(
            set(NON_DAMAGING_ROTATING_DOORS),
            set(AUDIT["global"]["classname_maps"]["func_door_rotating"]),
        )

    def test_zaero_missing_and_zero_stay_zero_but_positive_damage_is_exact(self) -> None:
        self.assertEqual(rotating_door_damage(None, is_zaero_map=True), 0)
        self.assertEqual(rotating_door_damage(0, is_zaero_map=True), 0)
        for damage in (1, 2, 6, 25):
            with self.subTest(damage=damage):
                self.assertEqual(
                    rotating_door_damage(damage, is_zaero_map=True), damage
                )

    def test_non_zaero_missing_and_zero_retain_rerelease_default(self) -> None:
        self.assertEqual(rotating_door_damage(None, is_zaero_map=False), 2)
        self.assertEqual(rotating_door_damage(0, is_zaero_map=False), 2)
        self.assertEqual(rotating_door_damage(6, is_zaero_map=False), 6)

    def test_spawn_and_blocked_paths_preserve_zero_without_stalling_motion(self) -> None:
        rotating = function_body(FUNC, "void SP_func_door_rotating(edict_t *ent)")
        self.assertIn("if (!ent->dmg && !level.zaero_mapper_contract)", rotating)
        self.assertIn("ent->dmg = 2", rotating)

        sliding = function_body(FUNC, "void SP_func_door(edict_t *ent)")
        self.assertIn("if (!ent->dmg)\n\t\tent->dmg = 2", sliding)
        self.assertNotIn("!ent->dmg && !level.zaero_mapper_contract", sliding)

        blocked = function_body(
            FUNC,
            "MOVEINFO_BLOCKED(door_blocked) (edict_t *self, edict_t *other) -> void",
        )
        damage = blocked.index("if (self->dmg")
        reversal = blocked.index("if (self->moveinfo.wait >= 0)")
        self.assertLess(damage, reversal)
        self.assertIn("T_Damage", blocked[damage:reversal])
        self.assertIn("door_go_up", blocked[reversal:])
        self.assertIn("door_go_down", blocked[reversal:])


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
