from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HEADER = (ROOT / "src" / "zaero" / "g_zaero_ired.h").read_text(encoding="utf-8")
SOURCE = (ROOT / "src" / "zaero" / "g_zaero_ired.cpp").read_text(
    encoding="utf-8"
)
ASSET_REPORT = json.loads(
    (ROOT / "docs" / "audits" / "assets.json").read_text(encoding="utf-8")
)
EFFECTIVE_ASSET_PATHS = {
    entry["path"] for entry in ASSET_REPORT["effective_pak_entries"]
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


class ZaeroIREDContractTests(unittest.TestCase):
    def test_public_integration_surface_is_explicit(self) -> None:
        for contract in (
            "using zaero_ired_emp_check_t",
            "void Zaero_SetIREDEMPCheck",
            "void Weapon_ZaeroIRED(edict_t *ent)",
            "void SP_misc_ired(edict_t *self)",
            "bool Zaero_FireIRED",
        ):
            self.assertIn(contract, HEADER)

        self.assertIn("MOD_ZAERO_TRIPBOMB", SOURCE)
        self.assertIn("if (!level.is_zaero", SOURCE)
        self.assertIn("THINK(Zaero_IREDExplode)", SOURCE)
        self.assertIn("THINK(Zaero_IREDLaserThink)", SOURCE)
        self.assertIn("THINK(Zaero_IREDLaserOn)", SOURCE)
        self.assertIn("THINK(Zaero_CreateIREDLaser)", SOURCE)
        self.assertIn("THINK(Zaero_IREDThink)", SOURCE)
        self.assertIn("TOUCH(Zaero_IREDShrapnelTouch)", SOURCE)
        self.assertIn("USE(Zaero_IREDUse)", SOURCE)
        self.assertIn("PAIN(Zaero_IREDPain)", SOURCE)

    def test_placement_arm_timeout_and_limit_constants_match_supplied_source(self) -> None:
        for contract in (
            "ZAERO_IRED_REFERENCE_TICK = 100_ms",
            "ZAERO_IRED_ARM_DELAY = 1_sec",
            "ZAERO_IRED_BEAM_TIMEOUT = 180_sec",
            "ZAERO_IRED_PLACEMENT_RANGE = 64.0f",
            "ZAERO_IRED_WALL_OFFSET = 3.0f",
            "ZAERO_IRED_BEAM_RANGE = 2048.0f",
            "ZAERO_IRED_TRIGGER_EPSILON = 1.0f",
            "ZAERO_IRED_PHASE_SKIP_CHANCE = 0.1f",
            "ZAERO_IRED_MAX_DEPLOYED = 25",
            "ZAERO_IRED_BEAM_SKIN = static_cast<int32_t>(0xb0b1b2b3u)",
        ):
            self.assertIn(contract, SOURCE)

        deploy = function_body(SOURCE, "bool Zaero_FireIRED")
        self.assertIn("direction * ZAERO_IRED_PLACEMENT_RANGE", deploy)
        self.assertIn("tr.fraction == 1.0f", deploy)
        self.assertIn('Zaero_IREDHasClassname(tr.ent, "worldspawn")', deploy)
        self.assertIn("tr.plane.normal * ZAERO_IRED_WALL_OFFSET", deploy)
        self.assertIn("bomb->teleport_time = level.time + arm_delay", deploy)
        self.assertIn("Zaero_RemoveOldestIRED();", deploy)

        oldest = function_body(SOURCE, "void Zaero_RemoveOldestIRED()")
        self.assertIn("G_FindByString<&edict_t::classname>", oldest)
        self.assertIn("candidate->timestamp < oldest->timestamp", oldest)
        self.assertIn("count > ZAERO_IRED_MAX_DEPLOYED", oldest)
        self.assertIn("oldest->think = Zaero_IREDExplode", oldest)

    def test_beam_endpoint_detection_emp_skip_and_visibility_quirk_are_preserved(self) -> None:
        think = function_body(SOURCE, "THINK(Zaero_IREDLaserThink)")
        for contract in (
            "level.time > self->timestamp",
            "zaero_ired_emp_check(self, self->s.origin)",
            "frandom() < ZAERO_IRED_PHASE_SKIP_CHANCE",
            "self->svflags &= ~SVF_NOCLIENT",
            "self->movedir * ZAERO_IRED_BEAM_RANGE",
            "self, MASK_SHOT",
            "self->s.origin == self->move_origin",
            "self->move_origin = tr.endpos",
            "delta.length() > ZAERO_IRED_TRIGGER_EPSILON",
            "self->s.old_origin = self->move_origin",
        ):
            self.assertIn(contract, think)

        phase_branch = think[think.index("if ((zaero_ired_emp_check") :]
        phase_branch = phase_branch[: phase_branch.index("self->svflags &=")]
        self.assertNotIn("self->svflags |= SVF_NOCLIENT", phase_branch)
        self.assertNotIn("self->svflags &= ~SVF_NOCLIENT", phase_branch)
        self.assertIn("SPAWNFLAG_IRED_INITIAL_SPARKS", think)
        self.assertIn("TE_LASER_SPARKS", think)
        self.assertIn("ZAERO_IRED_INITIAL_SPARK_COUNT", think)

        create = function_body(SOURCE, "THINK(Zaero_CreateIREDLaser)")
        for contract in (
            'laser->classname = ZAERO_IRED_BEAM_CLASSNAME',
            "G_SetMovedir(laser->s.angles, laser->movedir)",
            "RF_BEAM | RF_TRANSLUCENT",
            "laser->s.modelindex = 1",
            "laser->svflags |= SVF_NOCLIENT",
            "laser->timestamp = level.time + ZAERO_IRED_BEAM_TIMEOUT",
        ):
            self.assertIn(contract, create)

    def test_damage_shrapnel_and_immortal_pain_contract_are_exact(self) -> None:
        for contract in (
            "ZAERO_IRED_DAMAGE = 150",
            "ZAERO_IRED_DAMAGE_RADIUS = 384.0f",
            "ZAERO_IRED_HEALTH = 1",
            "ZAERO_IRED_SHRAPNEL_COUNT = 5",
            "ZAERO_IRED_SHRAPNEL_DAMAGE = 15",
            "ZAERO_IRED_SHRAPNEL_KNOCKBACK = 8",
            "ZAERO_IRED_SHRAPNEL_FORWARD_SPEED = 500.0f",
            "ZAERO_IRED_SHRAPNEL_RANDOM_SPEED = 500.0f",
            "ZAERO_IRED_SHRAPNEL_BASE_LIFETIME = 3_sec",
            "ZAERO_IRED_SHRAPNEL_LIFETIME_VARIANCE_SECONDS = 1.5f",
        ):
            self.assertIn(contract, SOURCE)

        setup = function_body(SOURCE, "void Zaero_SetupIREDBomb")
        self.assertIn("bomb->mins = {-8.0f, -8.0f, -8.0f}", setup)
        self.assertIn("bomb->maxs = {8.0f, 8.0f, 8.0f}", setup)
        self.assertIn("bomb->takedamage = true", setup)
        self.assertIn("bomb->flags |= FL_IMMORTAL", setup)
        self.assertIn("bomb->pain = Zaero_IREDPain", setup)

        explode = function_body(SOURCE, "THINK(Zaero_IREDExplode)")
        self.assertIn("T_RadiusDamage", explode)
        self.assertIn("MOD_ZAERO_TRIPBOMB", explode)
        self.assertIn("i < ZAERO_IRED_SHRAPNEL_COUNT", explode)
        self.assertIn("MOVETYPE_BOUNCE", explode)
        self.assertIn("EF_GRENADE", explode)
        self.assertIn("crandom() * ZAERO_IRED_SHRAPNEL_RANDOM_SPEED", explode)
        self.assertNotIn("gi.linkentity(shrapnel)", explode)

        pain = function_body(SOURCE, "PAIN(Zaero_IREDPain)")
        self.assertIn("level.time + ZAERO_IRED_GLOW_TIME", pain)
        self.assertIn("if (!self->think)", pain)
        self.assertIn("EF_COLOR_SHELL", pain)
        self.assertIn("RF_SHELL_GREEN", pain)

    def test_weapon_frames_ammo_and_success_only_model_swap_match_legacy(self) -> None:
        for contract in (
            "ZAERO_IRED_ACTIVATE_LAST = 6",
            "ZAERO_IRED_FIRE_FIRST = 7",
            "ZAERO_IRED_PLACE_FRAME = 10",
            "ZAERO_IRED_RESTORE_MODEL_FRAME = 15",
            "ZAERO_IRED_IDLE_FIRST = 16",
            "ZAERO_IRED_READY_FRAME = 17",
            "ZAERO_IRED_IDLE_LAST = 43",
            "ZAERO_IRED_DEACTIVATE_FIRST = 44",
            "ZAERO_IRED_DEACTIVATE_LAST = 48",
            "static const int32_t pause_frames[] = {24, 33, 43, 0}",
        ):
            self.assertIn(contract, SOURCE)

        fire = function_body(SOURCE, "void Zaero_IREDWeaponFireFrame")
        self.assertIn("ent->viewheight * 0.75f", fire)
        self.assertIn("ent->client->quad_time > level.time", fire)
        self.assertIn("ZAERO_IRED_DAMAGE * 4", fire)
        self.assertIn("G_RemoveAmmo(ent, 1)", fire)
        self.assertIn("ZAERO_IRED_HAND_MODEL", fire)
        self.assertIn("ZAERO_IRED_VIEW_MODEL", fire)
        self.assertIn("ent->client->ps.gunframe = 0", fire)
        self.assertIn("ent->client->ps.gunframe = ZAERO_IRED_IDLE_FIRST", fire)
        self.assertLess(fire.index("if (Zaero_FireIRED"), fire.index("G_RemoveAmmo(ent, 1)"))

        weapon = function_body(SOURCE, "void Weapon_ZaeroIRED(edict_t *ent)")
        self.assertIn("ps.gunrate = 0", weapon)
        self.assertIn("pers.inventory[ent->client->pers.weapon->ammo] > 0", weapon)
        self.assertIn("NoAmmoWeaponChange(ent, true)", weapon)
        self.assertIn("ent->client->weapon_fire_buffered", weapon)

    def test_mapper_misc_ired_back_wall_and_toggle_contract(self) -> None:
        spawn = function_body(SOURCE, "void SP_misc_ired(edict_t *self)")
        for contract in (
            "SPAWNFLAG_IRED_CHECK_BACK_WALL",
            "forward * ZAERO_IRED_PLACEMENT_RANGE",
            "self, MASK_SOLID",
            "self->s.origin = tr.endpos",
            "self->s.angles = vectoangles(tr.plane.normal)",
            "Zaero_SetupIREDBomb(self, ZAERO_IRED_MAP_CLASSNAME",
            "if (self->targetname)",
            "self->use = Zaero_IREDUse",
            "self->think = Zaero_CreateIREDLaser",
            "self->nextthink = level.time + ZAERO_IRED_ARM_DELAY",
        ):
            self.assertIn(contract, spawn)

        use = function_body(SOURCE, "USE(Zaero_IREDUse)")
        self.assertIn("Zaero_IREDValidatedBeam(self)", use)
        self.assertIn("Zaero_IREDDetachBeam(self)", use)
        self.assertIn("Zaero_CreateIREDLaser(self)", use)

    def test_relationship_cleanup_is_generation_checked_and_save_native(self) -> None:
        beam = function_body(SOURCE, "edict_t *Zaero_IREDValidatedBeam")
        bomb = function_body(SOURCE, "edict_t *Zaero_IREDValidatedBomb")
        self.assertIn("beam->spawn_count == bomb->count", beam)
        self.assertIn("bomb->spawn_count == beam->count", bomb)

        create = function_body(SOURCE, "THINK(Zaero_CreateIREDLaser)")
        self.assertIn("bomb->count = laser->spawn_count", create)
        self.assertIn("laser->count = bomb->spawn_count", create)
        self.assertIn("laser->chain = bomb", create)

        deploy = function_body(SOURCE, "bool Zaero_FireIRED")
        self.assertIn("bomb->style = owner->spawn_count", deploy)
        owner = function_body(SOURCE, "edict_t *Zaero_IREDValidatedOwner")
        self.assertIn("entity->owner->spawn_count == entity->style", owner)

        # All relationship/timer/function storage uses fields already present in
        # the Rerelease JSON schema; root only needs to register these callbacks.
        for field in ("chain", "count", "style", "timestamp", "teleport_time"):
            self.assertIn(f"FIELD_AUTO({field})", (ROOT / "src" / "g_save.cpp").read_text(encoding="utf-8"))

    def test_runtime_asset_paths_are_case_exact_and_unused_sounds_stay_unused(self) -> None:
        source_paths = (
            "models/objects/ired/tris.md2",
            "models/objects/shrapnel/tris.md2",
            "models/weapons/v_ired/tris.md2",
            "models/weapons/v_ired/hand.md2",
            "weapons/ired/las_set.wav",
            "weapons/ired/las_arm.wav",
        )
        for path in source_paths:
            self.assertIn(path, SOURCE)

        for path in source_paths:
            audit_path = path if path.startswith("models/") else f"sound/{path}"
            self.assertIn(audit_path, EFFECTIVE_ASSET_PATHS)

        # These three calls are commented out in the supplied implementation;
        # las_exp is shipped but likewise never used by the IRED code.
        for unused in (
            "weapons/ired/las_tink.wav",
            "weapons/ired/las_trig.wav",
            "weapons/ired/las_glow.wav",
            "weapons/ired/las_exp.wav",
        ):
            self.assertNotIn(unused, SOURCE)

    def test_shared_project_item_spawn_and_emp_integration_is_live(self) -> None:
        project = (ROOT / "src" / "game.vcxproj").read_text(encoding="utf-8")
        filters = (ROOT / "src" / "game.vcxproj.filters").read_text(encoding="utf-8")
        items = (ROOT / "src" / "g_items.cpp").read_text(encoding="utf-8")
        spawn = (ROOT / "src" / "g_spawn.cpp").read_text(encoding="utf-8")
        main = (ROOT / "src" / "g_main.cpp").read_text(encoding="utf-8")

        for manifest in (project, filters):
            self.assertIn("zaero\\g_zaero_ired.h", manifest)
            self.assertIn("zaero\\g_zaero_ired.cpp", manifest)
        self.assertIn("Weapon_ZaeroIRED", items)
        self.assertNotIn("Weapon_ZaeroIREDPending", items)
        ired_item = items[items.index('/* classname */ "ammo_ired"') :]
        ired_item = ired_item[: ired_item.index("\n\t},")]
        self.assertIn("IF_AMMO | IF_WEAPON", ired_item)
        self.assertNotIn("IF_PENDING_IMPLEMENTATION", ired_item)
        self.assertNotIn("IF_NO_INFINITE_AMMO", ired_item)
        self.assertIn('{ "misc_ired", SP_misc_ired }', spawn)
        self.assertIn("Zaero_SetIREDEMPCheck(Zaero_EMPNukeCheck)", main)


if __name__ == "__main__":
    unittest.main()
