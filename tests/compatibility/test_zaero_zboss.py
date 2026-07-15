from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "src" / "zaero" / "g_zaero_zboss.cpp").read_text(
    encoding="utf-8"
)
SPAWN = (ROOT / "src" / "g_spawn.cpp").read_text(encoding="utf-8")
LOCAL = (ROOT / "src" / "g_local.h").read_text(encoding="utf-8")
SAVE = (ROOT / "src" / "g_save.cpp").read_text(encoding="utf-8")
ENTITIES = (ROOT / "src" / "zaero" / "g_zaero_entities.cpp").read_text(
    encoding="utf-8"
)
WEAPONS = (ROOT / "src" / "zaero" / "g_zaero_weapons.cpp").read_text(
    encoding="utf-8"
)
CLIENT = (ROOT / "src" / "p_client.cpp").read_text(encoding="utf-8")
FINALE = (ROOT / "src" / "zaero" / "g_zaero_finale.cpp").read_text(
    encoding="utf-8"
)
MAIN = (ROOT / "src" / "g_main.cpp").read_text(encoding="utf-8")
HUD = (ROOT / "src" / "p_hud.cpp").read_text(encoding="utf-8")
BSP_AUDIT = (ROOT / "docs" / "audits" / "bsp-entities.json").read_text(
    encoding="utf-8"
)


class ZaeroZBossContractTests(unittest.TestCase):
    def test_exact_classname_and_project_integration(self) -> None:
        self.assertEqual(
            len(
                re.findall(
                    r'\{\s*"monster_zboss"\s*,\s*SP_monster_zboss\s*\}', SPAWN
                )
            ),
            1,
        )
        project = (ROOT / "src" / "game.vcxproj").read_text(encoding="utf-8")
        self.assertIn('ClCompile Include="zaero\\g_zaero_zboss.cpp"', project)
        self.assertIn('ClCompile Include="zaero\\g_zaero_finale.cpp"', project)

    def test_all_supplied_animation_ranges_and_moves_are_locked(self) -> None:
        expected = {
            "STAND1": (1, 31),
            "STAND2": (32, 56),
            "PRE_HOOK": (57, 66),
            "PRE_CANNON": (67, 70),
            "ATTACK_ROCKET": (71, 91),
            "RELOAD": (92, 98),
            "HOOK_FIRE": (99, 106),
            "HOOK_REEL": (107, 109),
            "HOOK_MELEE": (110, 118),
            "ATTACK_CANNON": (119, 132),
            "POST_CANNON": (133, 135),
            "POST_HOOK": (136, 141),
            "HOOK_TO_CANNON": (142, 147),
            "CANNON_TO_HOOK": (148, 153),
            "PRE_WALK": (154, 160),
            "WALK": (161, 176),
            "POST_WALK": (177, 184),
            "PAIN1": (185, 187),
            "PAIN2": (188, 192),
            "PAIN3": (193, 217),
            "DEATH1": (218, 236),
            "DEATH2": (237, 281),
        }
        for name, (start, end) in expected.items():
            self.assertIn(f"FRAME_{name}_START = {start}", SOURCE)
            self.assertIn(f"FRAME_{name}_END = {end}", SOURCE)
        self.assertEqual(SOURCE.count("MMOVE_T(zboss_move_"), 25)
        self.assertGreaterEqual(SOURCE.count("static_assert(std::size(zboss_frames_"), 25)

    def test_spawn_stats_models_and_monster_damage_rule(self) -> None:
        for model in (
            "models/monsters/bossz/mech/tris.md2",
            "models/monsters/bossz/pilot/tris.md2",
            "models/monsters/bossz/grapple/tris.md2",
        ):
            self.assertIn(model, SOURCE)
        self.assertIn("self->mins = { -32, -74, -30 }", SOURCE)
        self.assertIn("self->maxs = { 32, 50, 74 }", SOURCE)
        self.assertIn("self->movetype = MOVETYPE_STEP", SOURCE)
        self.assertIn("walkmonster_start(self);", SOURCE)
        self.assertIn("3000", SOURCE)
        self.assertIn("4500", SOURCE)
        self.assertIn("6000", SOURCE)
        self.assertIn("8000", SOURCE)
        self.assertIn("self->gib_health = -700", SOURCE)
        self.assertIn("self->mass = 1000", SOURCE)
        self.assertIn("AI_ZAERO_MONSTER_REDUCED_DAMAGE", SOURCE)
        self.assertIn("self->monsterinfo.zaero_damage_scale = 0.25f", SOURCE)

    def test_rocket_flare_plasma_and_one_shot_contracts(self) -> None:
        self.assertIn("Zaero_FireFlare(self, start, direction, 10, 1000, 10.0f, 10)", SOURCE)
        self.assertIn("ZBOSS_ROCKET_DAMAGE = 70", SOURCE)
        self.assertIn("ZBOSS_ROCKET_SPEED = 500", SOURCE)
        self.assertIn("ZBOSS_PLASMA_DAMAGE = 90", SOURCE)
        self.assertIn("ZBOSS_PLASMA_RADIUS = 130.0f", SOURCE)
        self.assertIn("distance * (skill->integer < 3 ? 1.2f : 1.6f)", SOURCE)
        self.assertIn("monsterinfo.zaero_shot_target", SOURCE)
        self.assertIn("AI_ZAERO_ONESHOT_TARGET", SOURCE)
        self.assertIn('strcmp(boss->classname, "monster_zboss")', ENTITIES)

    def test_hook_is_generation_owned_saved_and_cleanup_safe(self) -> None:
        self.assertIn('ZBOSS_HOOK_CLASSNAME = "bosshook"', SOURCE)
        self.assertIn("hook->count = self->spawn_count", SOURCE)
        self.assertIn("boss->spawn_count == hook->count", SOURCE)
        self.assertIn("boss->beam == hook", SOURCE)
        self.assertIn("boss->beam->enemy->velocity = {}", SOURCE)
        self.assertIn("zaero_child_target_spawn_count", SOURCE)
        self.assertIn("FIELD_AUTO(zaero_child_target_spawn_count)", SAVE)
        self.assertIn("G_FreeEdict(boss->beam)", SOURCE)
        self.assertIn("if (zboss_hook_owned(self))\n\t\tzboss_free_hook(self);", SOURCE)
        self.assertIn("FIELD_AUTO( beam )", SAVE)

    def test_emp_pressure_threshold_and_typed_cooldowns(self) -> None:
        self.assertIn("zaero_boss_fire_count > 40", SOURCE)
        self.assertIn("self->health < self->max_health / 4", SOURCE)
        self.assertIn("ZBOSS_FIRE_PRESSURE_WINDOW = 1_sec", SOURCE)
        self.assertIn("ZBOSS_EMP_COOLDOWN = 30_sec", SOURCE)
        self.assertIn("gtime_t::from_sec(frandom() * 5.0f)", SOURCE)
        self.assertIn("Zaero_FireEMPNuke(self, self->s.origin, 1024)", SOURCE)

    def test_boss_state_and_callbacks_are_json_registered(self) -> None:
        fields = (
            "zaero_boss_fire_count",
            "zaero_boss_fire_timeout",
            "zaero_boss_emp_cooldown",
            "zaero_boss_cannon_spread",
        )
        for field in fields:
            self.assertIn(field, LOCAL)
            self.assertIn(f"FIELD_AUTO(monsterinfo.{field})", SAVE)
        for callback, macro in {
            "zboss_hook_drag_think": "THINK",
            "zboss_hook_touch": "TOUCH",
            "zboss_hook_fly_think": "THINK",
            "zboss_plasma_blast_anim": "THINK",
            "zboss_plasma_explode": "THINK",
            "zboss_plasma_touch": "TOUCH",
            "zboss_dead_hook_expire": "THINK",
            "zboss_dead_hook_touch": "TOUCH",
            "zboss_stand": "MONSTERINFO_STAND",
            "zboss_walk": "MONSTERINFO_WALK",
            "zboss_run": "MONSTERINFO_RUN",
            "zboss_attack_start": "MONSTERINFO_ATTACK",
            "zboss_melee": "MONSTERINFO_MELEE",
            "zboss_sight": "MONSTERINFO_SIGHT",
            "zboss_pain": "PAIN",
            "zboss_die": "DIE",
        }.items():
            self.assertIn(f"{macro}({callback})", SOURCE)

    def test_projectile_owner_generation_and_explosion_fix_are_explicit(self) -> None:
        self.assertIn("plasma->count = self->spawn_count", SOURCE)
        self.assertIn("self->owner->spawn_count == self->count", SOURCE)
        self.assertIn("self->solid = SOLID_NOT", SOURCE)
        self.assertIn("self->touch = nullptr", SOURCE)
        self.assertIn("flare->count = self->spawn_count", WEAPONS)
        self.assertIn("flare->owner->spawn_count == flare->count", WEAPONS)

    def test_fresh_zboss_entry_resets_only_that_clients_persistence(self) -> None:
        self.assertIn(
            'spawn_from_begin && level.zaero_mapper_contract &&\n\t\tQ_strcasecmp(level.mapname, "zboss") == 0',
            CLIENT,
        )
        self.assertIn("if (client->pers.health <= 0)", CLIENT)
        self.assertIn("const int32_t health = client->pers.health", CLIENT)
        self.assertIn(
            "InitClientPersistant(ent, client, init_client_persistant_mode_t::zaero_boss_entry)",
            CLIENT,
        )
        self.assertIn("client->pers.health = health", CLIENT)
        self.assertIn("if (zaero_boss_entry_reset && coop->integer)", CLIENT)
        self.assertIn("client->resp.coop_respawn = client->pers", CLIENT)

    def test_zboss_entry_loadout_bypasses_native_and_coop_extras(self) -> None:
        self.assertIn("if (coop->integer && !zaero_boss_entry)", CLIENT)
        self.assertIn("if (!zaero_boss_entry)\n\t\t\t{", CLIENT)
        self.assertIn("if (give_grapple && !zaero_boss_entry)", CLIENT)
        for item in (
            "IT_WEAPON_PUSH",
            "IT_WEAPON_BLASTER",
            "IT_WEAPON_FLAREGUN",
            "IT_AMMO_FLARES",
        ):
            self.assertIn(item, CLIENT)

    def test_finale_uses_five_second_white_per_client_fade(self) -> None:
        self.assertIn("ZAERO_FINALE_FADE_DURATION = 5_sec", FINALE)
        self.assertIn("level.zaero_mapper_contract && !deathmatch->integer", FINALE)
        self.assertIn('Q_strcasecmp(level.mapname, "zboss") == 0', FINALE)
        self.assertIn("level.time + ZAERO_FINALE_FADE_DURATION", FINALE)
        self.assertIn(
            "player->client->ps.screen_blend = { 1.0f, 1.0f, 1.0f, alpha }",
            FINALE,
        )
        self.assertIn("Zaero_BeginFinaleFade();", HUD)
        self.assertIn("Zaero_UpdateFinaleFade()", MAIN)
        self.assertIn(
            "zaero_finale_fade != zaero_finale_fade_state_t::running", MAIN
        )

    def test_authored_outro_victory_chain_remains_exact(self) -> None:
        self.assertIn('"map": "outro.cin+victory.pcx"', BSP_AUDIT)
        self.assertIn('G_Fmt("gamemap \\"{}\\"\\n", level.changemap)', MAIN)


if __name__ == "__main__":
    unittest.main()
