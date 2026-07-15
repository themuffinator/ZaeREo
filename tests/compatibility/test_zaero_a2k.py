"""Static contracts for Zaero's Armageddon 2000 (A2K)."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "src" / "zaero" / "g_zaero_a2k.cpp").read_text(
    encoding="utf-8"
)
HEADER = (ROOT / "src" / "zaero" / "g_zaero_a2k.h").read_text(
    encoding="utf-8"
)
LOCAL = (ROOT / "src" / "g_local.h").read_text(encoding="utf-8")
SAVE = (ROOT / "src" / "g_save.cpp").read_text(encoding="utf-8")
ITEMS = (ROOT / "src" / "g_items.cpp").read_text(encoding="utf-8")
COMBAT = (ROOT / "src" / "g_combat.cpp").read_text(encoding="utf-8")
HUD = (ROOT / "src" / "p_hud.cpp").read_text(encoding="utf-8")
CLIENT = (ROOT / "src" / "p_client.cpp").read_text(encoding="utf-8")
PLAYER_WEAPONS = (ROOT / "src" / "p_weapon.cpp").read_text(encoding="utf-8")
PROJECT = (ROOT / "src" / "game.vcxproj").read_text(encoding="utf-8")
FILTERS = (ROOT / "src" / "game.vcxproj.filters").read_text(encoding="utf-8")
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


def item_block(item_id: str) -> str:
    start = ITEMS.index(f"/* id */ {item_id}")
    end = ITEMS.index("\n\t},", start)
    return ITEMS[start:end]


class ZaeroA2KContractTests(unittest.TestCase):
    def test_supplied_source_oracles_are_identity_locked(self) -> None:
        expected = {
            "z_weapon.c": (
                "bd23c9d99bb4d7d5af6a0e329aa30db7baafc155a3d5cf0814166576e5669d90",
                "zaero_only",
            ),
            "g_combat.c": (
                "b600b4371abe59a0e7d3ac2fbb6e3c19cd17ae24100b3e3d9f34882d1d3180cb",
                "modified",
            ),
            "p_hud.c": (
                "310e2bc0e11fd73041d8a96ed04b6570377ebb180e92a5eb95b15dcabe359765",
                "modified",
            ),
            "p_client.c": (
                "f0e871b588fb4527bcafb42458bc810f4eef748c32f245646de760e9036db6a4",
                "modified",
            ),
        }
        records = {
            record["path"]: record
            for record in SOURCE_AUDIT["comparison"]["file_records"]
        }
        for path, (digest, status) in expected.items():
            self.assertEqual(records[path]["zaero_sha256"], digest)
            self.assertEqual(records[path]["status"], status)

    def test_five_second_deadline_and_held_frame_are_typed_and_exact(self) -> None:
        for contract in (
            "ZAERO_A2K_COUNTDOWN = 5_sec",
            "ZAERO_A2K_EXPLOSION_TICK = 100_ms",
            "ZAERO_A2K_START_FRAME = 14",
            "ZAERO_A2K_HOLD_FRAME = 19",
            "ZAERO_A2K_FIRE_LAST = 19",
            "ZAERO_A2K_IDLE_LAST = 49",
            "ZAERO_A2K_DEACTIVATE_LAST = 55",
            "pause_frames[] = {20, 30, 40, 0}",
        ):
            self.assertIn(contract, SOURCE)

        weapon = function_body(SOURCE, "void Weapon_ZaeroA2K(edict_t *ent)")
        self.assertIn("ps.gunframe == ZAERO_A2K_HOLD_FRAME", weapon)
        self.assertIn("level.time < ent->client->zaero_a2k_detonate_time", weapon)
        self.assertLess(
            weapon.index("Zaero_A2KDetonate(ent)"),
            weapon.index("Weapon_Generic(ent"),
        )
        self.assertIn("Zaero_A2KFireFrame, false", weapon)
        self.assertEqual(5 * 40, 200)

    def test_activation_consumes_once_and_creates_only_client_state(self) -> None:
        activate = function_body(SOURCE, "void Zaero_A2KFireFrame(edict_t *ent)")
        for contract in (
            "ps.gunframe != ZAERO_A2K_START_FRAME",
            "level.time + ZAERO_A2K_COUNTDOWN",
            "pers.inventory[ent->client->pers.weapon->ammo]--",
            "ent->client->ps.gunframe++",
            "ZAERO_A2K_COUNTDOWN_SOUND",
            "Zaero_A2KPlayQuadSound(ent)",
        ):
            self.assertIn(contract, activate)
        self.assertNotIn("G_Spawn", activate)
        self.assertNotIn("G_CheckInfiniteAmmo", activate)
        self.assertNotIn("dmflags", activate)

    def test_absolute_immunity_precedes_ordinary_invulnerability(self) -> None:
        protect = function_body(SOURCE, "bool Zaero_A2KProtects")
        self.assertIn("level.is_zaero", protect)
        self.assertIn("zaero_a2k_detonate_time > level.time", protect)

        a2k_check = COMBAT.index("if (Zaero_A2KProtects(targ))")
        invulnerability = COMBAT.index("// check for invincibility", a2k_check)
        self.assertLess(a2k_check, invulnerability)
        block = COMBAT[a2k_check:invulnerability]
        self.assertIn("take = 0", block)
        self.assertIn("save = damage", block)
        self.assertIn('gi.soundindex("items/protect4.wav")', block)
        self.assertIn("level.time + 2_sec", block)
        self.assertNotIn("DAMAGE_NO_PROTECTION", block)

    def test_dual_damage_passes_preserve_visibility_falloff_and_self_halving(self) -> None:
        visibility = function_body(SOURCE, "bool Zaero_A2KHasLineOfSight")
        for contract in (
            "start[2] += inflictor->viewheight",
            "end[2] += target->viewheight",
            "gi.traceline(start, end, inflictor, MASK_OPAQUE)",
            "trace.fraction == 1.0f",
        ):
            self.assertIn(contract, visibility)
        self.assertNotIn("visible(", visibility)

        radius = function_body(SOURCE, "void Zaero_A2KRadiusDamage")
        for contract in (
            "findradius(target, inflictor->s.origin, radius)",
            "require_visible && !Zaero_A2KHasLineOfSight(inflictor, target)",
            "target->s.origin + ((target->mins + target->maxs) * 0.5f)",
            "damage - (0.5f * distance)",
            "if (target == attacker)",
            "points *= 0.5f",
            "CanDamage(target, inflictor)",
            "target->s.origin - inflictor->s.origin",
            "DAMAGE_RADIUS",
            "MOD_ZAERO_A2K",
        ):
            self.assertIn(contract, radius)

        detonate = function_body(SOURCE, "void Zaero_A2KDetonate")
        first = "Zaero_A2KRadiusDamage(ent, ent, damage, radius, false)"
        second = "radius * ZAERO_A2K_OUTER_RADIUS_SCALE, true"
        self.assertIn(first, detonate)
        self.assertIn(second, detonate)
        self.assertLess(detonate.index(first), detonate.index(second))
        self.assertLess(detonate.index(second), detonate.index("Zaero_A2KSpawnExplosion"))

        # Independent golden falloff points. A visible target in the inner
        # radius takes each value twice; the attacker takes half per pass.
        for distance, expected in ((0, 2500), (512, 2244), (1024, 1988)):
            self.assertEqual(int(2500 - 0.5 * distance), expected)
        self.assertEqual(int((2500 - 0.5 * 0) * 0.5), 1250)

    def test_quad_is_sampled_at_blast_and_scales_damage_and_both_radii(self) -> None:
        detonate = function_body(SOURCE, "void Zaero_A2KDetonate")
        self.assertIn("ZAERO_A2K_DAMAGE = 2500.0f", SOURCE)
        self.assertIn("ZAERO_A2K_INNER_RADIUS = 512.0f", SOURCE)
        self.assertIn("ZAERO_A2K_OUTER_RADIUS_SCALE = 2.0f", SOURCE)
        self.assertIn("ZAERO_A2K_QUAD_SCALE = 4.0f", SOURCE)
        self.assertIn("ent->client->quad_time > level.time", detonate)
        self.assertIn("damage *= ZAERO_A2K_QUAD_SCALE", detonate)
        self.assertIn("radius *= ZAERO_A2K_QUAD_SCALE", detonate)
        self.assertLess(
            detonate.index("ent->client->quad_time > level.time"),
            detonate.index("Zaero_A2KRadiusDamage"),
        )
        self.assertEqual(2500 * 4, 10000)
        self.assertEqual(512 * 4, 2048)
        self.assertEqual(512 * 4 * 2, 4096)

    def test_detonation_only_helper_animates_six_legacy_frames_and_is_savable(self) -> None:
        spawn = function_body(SOURCE, "void Zaero_A2KSpawnExplosion")
        for contract in (
            'ZAERO_A2K_EXPLOSION_CLASSNAME = "A2K Explosion"',
            'ZAERO_A2K_EXPLOSION_MODEL = "models/objects/b_explode/tris.md2"',
            "explosion->solid = SOLID_NOT",
            "explosion->movetype = MOVETYPE_NONE",
            "explosion->s.skinnum = 6",
            "explosion->think = Zaero_A2KExplosionThink",
            "level.time + ZAERO_A2K_EXPLOSION_TICK",
            "gi.linkentity(explosion)",
            "ZAERO_A2K_EXPLOSION_SOUND",
        ):
            self.assertIn(contract, SOURCE if contract.startswith("ZAERO_") else spawn)

        animation = function_body(SOURCE, "THINK(Zaero_A2KExplosionThink)")
        self.assertIn("self->s.frame++", animation)
        self.assertIn("self->s.skinnum++", animation)
        self.assertIn("self->s.frame > ZAERO_A2K_LAST_VISIBLE_FRAME", animation)
        self.assertIn("G_FreeEdict(self)", animation)
        self.assertEqual(6 * (40 // 10), 24)

    def test_save_hud_lifecycle_and_split_client_wiring_is_explicit(self) -> None:
        field = "zaero_a2k_detonate_time"
        self.assertIn(f"gtime_t {field}", LOCAL)
        self.assertIn(f"FIELD_AUTO({field})", SAVE)
        self.assertIn("MOD_ZAERO_A2K", LOCAL)

        hud = function_body(SOURCE, "bool Zaero_A2KSetTimerStats")
        self.assertIn('gi.imageindex(ZAERO_A2K_ICON)', hud)
        self.assertIn("milliseconds() / 1000", hud)
        self.assertLess(
            HUD.index("Zaero_A2KSetTimerStats(ent)"),
            HUD.index("ent->client->owned_sphere"),
        )
        self.assertLess(
            HUD.index("Zaero_A2KSetTimerStats(ent)"),
            HUD.index("Zaero_SniperSetTimerStats(ent)"),
        )

        clear = function_body(SOURCE, "void Zaero_A2KClearClientState")
        self.assertIn(f"ent->client->{field} = 0_ms", clear)
        self.assertGreaterEqual(CLIENT.count("Zaero_A2KClearClientState"), 2)
        self.assertIn("Zaero_A2KClearClientState(ent)", PLAYER_WEAPONS)
        self.assertIn("IT_AMMO_A2K", PLAYER_WEAPONS)

    def test_item_project_and_obituary_replace_the_placeholder(self) -> None:
        item = item_block("IT_AMMO_A2K")
        for contract in (
            "Weapon_ZaeroA2K",
            "IF_AMMO | IF_POWERUP | IF_NO_WEAPON_SELECTION",
            "models/objects/b_explode/tris.md2",
        ):
            self.assertIn(contract, item)
        self.assertNotIn("Pending", item)
        self.assertNotIn("IF_PENDING_IMPLEMENTATION", item)
        self.assertNotIn("Weapon_ZaeroA2KPending", ITEMS)

        for manifest in (PROJECT, FILTERS):
            self.assertIn("zaero\\g_zaero_a2k.cpp", manifest)
            self.assertIn("zaero\\g_zaero_a2k.h", manifest)

        self.assertIn("void Weapon_ZaeroA2K", HEADER)
        self.assertIn("{} realized he was expendable\\n", CLIENT)
        # Preserve the supplied spelling, including its typo.
        self.assertIn("{} got dissassembled by {}\\n", CLIENT)


if __name__ == "__main__":
    unittest.main()
