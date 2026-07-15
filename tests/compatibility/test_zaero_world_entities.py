from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPAWN_SOURCE = (ROOT / "src" / "g_spawn.cpp").read_text(encoding="utf-8")
ENTITY_SOURCE = (ROOT / "src" / "zaero" / "g_zaero_entities.cpp").read_text(
    encoding="utf-8"
)
EDITOR_SCHEMA = json.loads(
    (ROOT / "editor" / "entities.json").read_text(encoding="utf-8")
)
SOURCE_AUDIT = json.loads(
    (ROOT / "docs" / "audits" / "source-delta.json").read_text(encoding="utf-8")
)


def function_body(source: str, signature: str) -> str:
    """Return a C++ function body using balanced braces, not a fragile regex."""

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


class ZaeroWorldEntityContractTests(unittest.TestCase):
    CLASSNAMES = {
        "sound_echo": "SP_sound_echo",
        "load_mirrorlevel": "SP_load_mirrorlevel",
        "trigger_laser": "SP_trigger_laser",
        "misc_commdish": "SP_misc_commdish",
        "misc_securitycamera": "SP_misc_securitycamera",
        "misc_crate": "SP_misc_crate",
        "misc_crate_medium": "SP_misc_crate_medium",
        "misc_crate_small": "SP_misc_crate_small",
        "func_barrier": "SP_func_barrier",
        "misc_seat": "SP_misc_seat",
        "target_zboss_target": "SP_target_zboss_target",
    }

    def test_exact_classnames_are_registered_once(self) -> None:
        for classname, spawn in self.CLASSNAMES.items():
            entry = rf'\{{\s*"{re.escape(classname)}"\s*,\s*{spawn}\s*\}}'
            self.assertEqual(
                len(re.findall(entry, SPAWN_SOURCE)),
                1,
                f"expected one registry entry for {classname}",
            )

    def test_source_only_entities_remain_explicit_noops(self) -> None:
        for spawn in ("SP_sound_echo", "SP_load_mirrorlevel"):
            body = function_body(ENTITY_SOURCE, f"void {spawn}(edict_t *self)")
            statements = [
                line.strip()
                for line in body.splitlines()
                if line.strip() and not line.lstrip().startswith("//")
            ]
            self.assertEqual(statements, ["G_FreeEdict(self);"])

    def test_stateful_callbacks_are_save_registered(self) -> None:
        for callback, macro in {
            "zaero_trigger_laser_on": "THINK",
            "zaero_trigger_laser_think": "THINK",
            "zaero_commdish_animate": "THINK",
            "zaero_commdish_use": "USE",
            "zaero_securitycamera_use": "USE",
            "zaero_securitycamera_think": "THINK",
            "zaero_securitycamera_pain": "PAIN",
            "zaero_barrier_think": "THINK",
            "zaero_barrier_pain": "PAIN",
            "zaero_barrier_touch": "TOUCH",
            "zaero_zboss_target_use": "USE",
        }.items():
            self.assertRegex(ENTITY_SOURCE, rf"{macro}\({callback}\)")

    def test_legacy_tick_duration_is_explicit(self) -> None:
        self.assertIn("constexpr gtime_t ZAERO_LEGACY_TICK = 100_ms;", ENTITY_SOURCE)
        self.assertNotIn("level.time + FRAME_TIME", ENTITY_SOURCE)

    def test_trigger_laser_keeps_mapper_contract(self) -> None:
        records = {
            record["path"]: record
            for record in SOURCE_AUDIT["comparison"]["file_records"]
        }
        self.assertEqual(
            records["z_trigger.c"]["zaero_sha256"],
            "1db62252c19019ce8568014acd4502a3289e45f0e88ad4ac46150bc68f1c3af4",
        )
        self.assertEqual(records["z_trigger.c"]["status"], "zaero_only")

        body = function_body(ENTITY_SOURCE, "void SP_trigger_laser(edict_t *self)")
        self.assertIn("if (!self->target)", body)
        self.assertIn("G_FreeEdict(self);", body)
        self.assertIn("self->wait = 4.0f;", body)
        self.assertIn("G_SetMovedir(self->s.angles, self->movedir);", body)
        self.assertIn("RF_BEAM | RF_TRANSLUCENT", body)
        self.assertIn("self->s.modelindex = MODELINDEX_WORLD;", body)
        self.assertIn("SPAWNFLAG_LASER_ZAP", body)
        self.assertIn("level.time + ZAERO_LEGACY_TICK", body)
        self.assertIn("self->svflags |= SVF_NOCLIENT", body)
        self.assertNotIn("self->use", body)

        think = function_body(
            ENTITY_SOURCE,
            "THINK(zaero_trigger_laser_think) (edict_t *self) -> void",
        )
        self.assertIn("level.time + ZAERO_LEGACY_TICK", think)
        self.assertIn("self->movedir * 2048.0f", think)
        self.assertIn(
            "CONTENTS_SOLID | CONTENTS_MONSTER |\n"
            "\t\tCONTENTS_PLAYER | CONTENTS_DEADMONSTER",
            think,
        )
        self.assertIn("TE_LASER_SPARKS", think)
        self.assertIn("gi.WriteByte(8);", think)
        self.assertIn("G_UseTargets(self, tr.ent);", think)
        self.assertIn("const int32_t trigger_spawn_count = self->spawn_count", think)
        self.assertIn(
            "if (!self->inuse || self->spawn_count != trigger_spawn_count)",
            think,
        )
        self.assertIn("SPAWNFLAG_TRIGGER_LASER_MULTIPLE", think)
        self.assertIn("self->svflags |= SVF_NOCLIENT", think)
        self.assertIn("gtime_t::from_sec(self->wait)", think)
        self.assertIn("G_FreeEdict(self);", think)

        on = function_body(
            ENTITY_SOURCE,
            "THINK(zaero_trigger_laser_on) (edict_t *self) -> void",
        )
        self.assertIn("self->svflags &= ~SVF_NOCLIENT", on)
        self.assertIn("zaero_trigger_laser_think(self);", on)

        editor = next(
            entity
            for entity in EDITOR_SCHEMA["entities"]
            if entity["classname"] == "trigger_laser"
        )
        self.assertEqual(
            {entry["name"] for entry in editor["properties"]},
            {"angle", "delay", "message", "target", "wait"},
        )
        self.assertEqual(
            editor["spawnflags"], [{"bit": 1, "name": "Trigger multiple"}]
        )

    def test_crate_variants_keep_models_bounds_and_mass(self) -> None:
        for model, extent, height in (
            ("crate64.md2", "32.0f", "64.0f"),
            ("crate48.md2", "24.0f", "48.0f"),
            ("crate32.md2", "16.0f", "32.0f"),
        ):
            self.assertIn(model, ENTITY_SOURCE)
            self.assertIn(f"{{ {extent}, {extent}, {height} }}", ENTITY_SOURCE)

        setup = function_body(ENTITY_SOURCE, "void setup_crate(edict_t *self)")
        self.assertIn("self->movetype = MOVETYPE_FALLFLOAT;", setup)
        self.assertIn("self->mass = 400;", setup)
        self.assertIn("self->touch = barrel_touch;", setup)

    def test_camera_and_barrier_use_rerelease_immortality(self) -> None:
        camera = function_body(
            ENTITY_SOURCE, "void SP_misc_securitycamera(edict_t *self)"
        )
        self.assertIn("if (!self->message)", camera)
        self.assertIn("self->move_angles = self->mangle;", camera)
        self.assertIn("self->takedamage = true;", camera)
        self.assertIn("self->flags |= FL_IMMORTAL;", camera)

        barrier = function_body(ENTITY_SOURCE, "void SP_func_barrier(edict_t *self)")
        self.assertIn("self->svflags |= SVF_NOCLIENT;", barrier)
        self.assertIn("self->takedamage = true;", barrier)
        self.assertIn("self->flags |= FL_IMMORTAL;", barrier)
        self.assertIn("self->touch = zaero_barrier_touch;", barrier)

    def test_barrier_trace_has_defined_no_hit_result(self) -> None:
        body = function_body(
            ENTITY_SOURCE,
            "bool Zaero_TraceThroughBarrier(edict_t *target, edict_t *inflictor)",
        )
        self.assertIn('Q_strcasecmp(tr.ent->classname, "func_barrier")', body)
        self.assertIn("traversals < MAX_EDICTS", body)
        self.assertTrue(body.rstrip().endswith("return false;"))

    def test_zboss_target_marker_queues_one_shot_attack_safely(self) -> None:
        spawn = function_body(
            ENTITY_SOURCE, "void SP_target_zboss_target(edict_t *self)"
        )
        self.assertIn("if (!self->target)", spawn)
        self.assertIn("G_FreeEdict(self);", spawn)
        self.assertIn("self->svflags |= SVF_NOCLIENT;", spawn)
        self.assertIn("self->solid = SOLID_NOT;", spawn)
        self.assertIn("self->use = zaero_zboss_target_use;", spawn)

        use = function_body(
            ENTITY_SOURCE,
            "USE(zaero_zboss_target_use) (edict_t *self, edict_t *other, edict_t *activator) -> void",
        )
        self.assertIn("G_FindByString<&edict_t::targetname>", use)
        self.assertIn("boss->health <= 0 || !boss->monsterinfo.attack", use)
        self.assertIn("boss->monsterinfo.zaero_shot_target = self->s.origin;", use)
        self.assertIn("AI_ZAERO_ONESHOT_TARGET", use)
        self.assertIn("boss->monsterinfo.attack(boss);", use)


if __name__ == "__main__":
    unittest.main()
