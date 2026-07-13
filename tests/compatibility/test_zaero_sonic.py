from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HEADER = (ROOT / "src" / "zaero" / "g_zaero_sonic.h").read_text(
    encoding="utf-8"
)
SOURCE = (ROOT / "src" / "zaero" / "g_zaero_sonic.cpp").read_text(
    encoding="utf-8"
)
ITEMS = (ROOT / "src" / "g_items.cpp").read_text(encoding="utf-8")
LOCAL = (ROOT / "src" / "g_local.h").read_text(encoding="utf-8")
SAVE = (ROOT / "src" / "g_save.cpp").read_text(encoding="utf-8")
CLIENT = (ROOT / "src" / "p_client.cpp").read_text(encoding="utf-8")
VIEW = (ROOT / "src" / "p_view.cpp").read_text(encoding="utf-8")


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


class ZaeroSonicContractTests(unittest.TestCase):
    def test_charge_constants_frames_and_40hz_timing_are_explicit(self) -> None:
        for contract in (
            "ZAERO_SONIC_MAX_CHARGE_TIME = 5_sec",
            "ZAERO_SONIC_WARMUP_TIME = 400_ms",
            "ZAERO_SONIC_EXPLOSION_STEP = 100_ms",
            "ZAERO_SONIC_BASE_DAMAGE = 10",
            "ZAERO_SONIC_DAMAGE_RANGE = 990",
            "ZAERO_SONIC_MAX_RADIUS = 500.0f",
            "ZAERO_SONIC_MAX_CELLS = 100",
            "ZAERO_SONIC_TRACE_DISTANCE = 8192.0f",
            "ZAERO_SONIC_CHARGE_FIRST_FRAME = 12",
            "ZAERO_SONIC_CHARGE_LAST_FRAME = 17",
            "ZAERO_SONIC_RELEASE_FRAME = 18",
            "ZAERO_SONIC_RERELEASE_LOOP_FRAME = 11",
            "static const int pause_frames[] = {32, 42, 52, 0}",
            "static const int fire_frames[] = {0}",
            "Weapon_Generic(ent, 6, 22, 52, 57",
        ):
            self.assertIn(contract, SOURCE)

        weapon = function_body(SOURCE, "void Weapon_ZaeroSonicCannon(edict_t *ent)")
        self.assertIn("frame != old_frame", weapon)
        self.assertIn("Zaero_SonicChargeFrame(ent);", weapon)
        self.assertIn("g_instant_weapon_switch->integer", weapon)
        self.assertIn("weapon_fire_finished <= level.time", weapon)

    def test_cell_charge_and_damage_golden_points(self) -> None:
        update = function_body(
            SOURCE,
            "void Zaero_SonicUpdateCharge(edict_t *self, int32_t &ammo)",
        )
        self.assertIn("static_cast<int32_t>(self->dmg_radius)", update)
        self.assertIn("charged_cells - old_cells", update)
        self.assertIn("requested_cells - ammo", update)
        self.assertIn("ammo = 0", update)
        self.assertIn("ammo -= requested_cells", update)

        charge = function_body(SOURCE, "void Zaero_SonicChargeFrame(edict_t *self)")
        self.assertLess(
            charge.index(">= ZAERO_SONIC_MAX_CHARGE_TIME"),
            charge.index("Zaero_SonicUpdateCharge(self, ammo)"),
            "the exact five-second boundary releases before recomputing 100 cells",
        )
        self.assertIn(
            "pers.inventory[self->client->pers.weapon->ammo]", charge
        )

        # Independent golden points for the supplied linear equations.
        for cells, expected_damage, expected_radius in (
            (1, 19.9, 5.0),
            (50, 505.0, 250.0),
            (100, 1000.0, 500.0),
        ):
            fraction = cells / 100.0
            self.assertAlmostEqual(10 + fraction * 990, expected_damage)
            self.assertAlmostEqual(fraction * 500, expected_radius)

    def test_trace_muzzle_and_charge_effect_preserve_supplied_geometry(self) -> None:
        trace = function_body(SOURCE, "zaero_sonic_trace_t Zaero_SonicTrace")
        for contract in (
            "static_cast<float>(self->viewheight - 8)",
            "self->client->pers.hand == LEFT_HANDED",
            "self->client->pers.hand == CENTER_HANDED",
            "G_ProjectSource(self->s.origin, offset, shot.forward, shot.right)",
            "MASK_PROJECTILE | CONTENTS_SLIME | CONTENTS_LAVA",
            "!G_ShouldPlayersCollide(true)",
            "mask &= ~CONTENTS_PLAYER",
            "shot.forward * ZAERO_SONIC_TRACE_DISTANCE",
        ):
            self.assertIn(contract, trace)

        effect = function_body(SOURCE, "void Zaero_SonicChargeEffect")
        self.assertIn("shot.trace.endpos - (shot.forward * 5.0f)", effect)
        self.assertEqual(effect.count("(crandom() * 10.0f) - 20.0f"), 3)
        self.assertIn("SpawnDamage(TE_SHIELD_SPARKS", effect)
        self.assertIn("P_AddWeaponKick", effect)

    def test_direct_and_radius_damage_keep_visibility_and_ignore_contract(self) -> None:
        radius = function_body(SOURCE, "void Zaero_SonicRadiusDamageAt")
        for contract in (
            "findradius(target, origin, radius)",
            "target == ignore",
            "damage - (0.5f * distance)",
            "if (target == attacker)",
            "points *= 0.5f",
            "CanDamage(target, inflictor)",
            "target->s.origin - origin",
            "DAMAGE_RADIUS",
            "MOD_ZAERO_SONIC_CANNON",
        ):
            self.assertIn(contract, radius)

        fire = function_body(SOURCE, "void Zaero_SonicFire(edict_t *self)")
        self.assertIn("shot.trace.ent != self", fire)
        self.assertIn("static_cast<int32_t>(damage)", fire)
        self.assertIn("shot.trace.ent,\n\t\tradius", fire)
        self.assertGreaterEqual(fire.count("MOD_ZAERO_SONIC_CANNON"), 1)

    def test_release_effects_delays_and_quad_audio_quirk_are_exact(self) -> None:
        fire = function_body(SOURCE, "void Zaero_SonicFire(edict_t *self)")
        for contract in (
            "TE_ROCKET_EXPLOSION",
            "gi.multicast(self->s.origin, MULTICAST_PHS, false)",
            "remaining_damage = damage - 100.0f",
            "delay = ZAERO_SONIC_EXPLOSION_STEP",
            'explosion->classname = "sconnanExplode"',
            "explosion->think = Zaero_SonicExplosionThink",
            "delay += ZAERO_SONIC_EXPLOSION_STEP",
            "remaining_damage -= 100.0f",
            "if (self->client->quad_time > level.time)",
            'gi.soundindex("items/damage3.wav")',
        ):
            self.assertIn(contract, fire)
        self.assertNotIn("damage *=", fire)
        self.assertNotIn("radius *=", fire)
        self.assertIn("THINK(Zaero_SonicExplosionThink)", SOURCE)

        # The empty native fire list prevents automatic Quad sound on each
        # charge frame; only Zaero_SonicFire emits it at discharge.
        self.assertEqual(SOURCE.count('gi.soundindex("items/damage3.wav")'), 1)

    def test_audio_emp_and_per_client_save_state_integration_contract(self) -> None:
        for sound in (
            "weapons/sonic/sc_act.wav",
            "weapons/sonic/sc_dact.wav",
            "weapons/sonic/sc_warm.wav",
            "weapons/sonic/sc_fire.wav",
            "weapons/sonic/sc_cool.wav",
            "items/empnuke/emp_missfire.wav",
        ):
            self.assertIn(sound, SOURCE)

        self.assertIn("using zaero_sonic_emp_check_t", HEADER)
        self.assertIn("void Zaero_SetSonicEMPCheck", HEADER)
        emp = function_body(SOURCE, "bool Zaero_SonicEMPBlocked")
        self.assertIn("zaero_sonic_emp_check(self, self->s.origin)", emp)

        # These two typed, per-client fields are the only new persisted state
        # required from the integration layer; charged cells remain in the
        # existing saved edict dmg_radius field.
        for field in (
            "zaero_sonic_charge_start",
            "zaero_sonic_warmup_until",
        ):
            self.assertIn(f"self->client->{field}", SOURCE)
        self.assertIn("self->dmg_radius", SOURCE)

        release = function_body(SOURCE, "void Zaero_SonicRelease")
        self.assertLess(
            release.index("Zaero_SonicEMPBlocked(self)"),
            release.index("Zaero_SonicFire(self)"),
        )
        self.assertIn("Zaero_SonicSoundVolume()", release)

    def test_shared_runtime_wiring_replaces_the_pending_placeholder(self) -> None:
        item_start = ITEMS.index("/* id */ IT_WEAPON_SONICCANNON")
        item_end = ITEMS.index("/* id */ IT_AMMO_A2K", item_start)
        item = ITEMS[item_start:item_end]
        self.assertIn("Weapon_ZaeroSonicCannon", item)
        self.assertNotIn("IF_PENDING_IMPLEMENTATION", item)

        self.assertIn("MOD_ZAERO_SONIC_CANNON", LOCAL)
        for field in ("zaero_sonic_charge_start", "zaero_sonic_warmup_until"):
            self.assertIn(f"gtime_t {field}", LOCAL)
            self.assertIn(f"FIELD_AUTO({field})", SAVE)

        self.assertIn("{} got carried away\\n", CLIENT)
        self.assertIn("{} got microwaved by {}\\n", CLIENT)
        self.assertIn("IT_WEAPON_SONICCANNON", VIEW)
        self.assertIn("weapons/sonic/sc_idle.wav", VIEW)


if __name__ == "__main__":
    unittest.main()
