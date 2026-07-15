"""Static contracts for Zaero's deployable Plasma Shield."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "src" / "zaero" / "g_zaero_plasma_shield.cpp").read_text(
    encoding="utf-8"
)
HEADER = (ROOT / "src" / "zaero" / "g_zaero_plasma_shield.h").read_text(
    encoding="utf-8"
)
COMBAT = (ROOT / "src" / "g_combat.cpp").read_text(encoding="utf-8")
ITEMS = (ROOT / "src" / "g_items.cpp").read_text(encoding="utf-8")
WEAPONS = (ROOT / "src" / "zaero" / "g_zaero_weapons.cpp").read_text(
    encoding="utf-8"
)
SNIPER = (ROOT / "src" / "zaero" / "g_zaero_sniper.cpp").read_text(
    encoding="utf-8"
)
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


class ZaeroPlasmaShieldContractTests(unittest.TestCase):
    def test_supplied_source_oracles_are_identity_locked(self) -> None:
        expected = {
            "z_item.c": (
                "23dcc0fda023260c73e26260bb86d2c78d6edfc29f0486a4b6472568561f94ae",
                "zaero_only",
            ),
            "g_combat.c": (
                "b600b4371abe59a0e7d3ac2fbb6e3c19cd17ae24100b3e3d9f34882d1d3180cb",
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

    def test_emp_blocks_before_consumption_sound_and_spawn(self) -> None:
        use = function_body(SOURCE, "void Use_ZaeroPlasmaShield")
        emp = use.index("Zaero_EMPNukeCheck(ent, ent->s.origin)")
        misfire = use.index("Zaero_PlayEMPMisfire(ent)")
        consume = use.index("pers.inventory[item->id]--")
        deploy_sound = use.index("ZAERO_PLASMA_SHIELD_DEPLOY_SOUND")
        spawn = use.index("G_Spawn()")
        self.assertLess(emp, misfire)
        self.assertLess(misfire, consume)
        self.assertLess(consume, deploy_sound)
        self.assertLess(deploy_sound, spawn)
        self.assertIn("if (!G_CheckInfiniteAmmo(item))", use)
        self.assertIn("if (deathmatch->integer)", use)
        self.assertIn("CHAN_VOICE", use)

    def test_placement_preserves_exact_rotated_two_point_box(self) -> None:
        use = function_body(SOURCE, "void Use_ZaeroPlasmaShield")
        for contract in (
            'ZAERO_PLASMA_SHIELD_CLASSNAME = "PlasmaShield"',
            "ZAERO_PLASMA_SHIELD_FORWARD_OFFSET = 50.0f",
            "shield->movetype = MOVETYPE_PUSH",
            "shield->solid = SOLID_BBOX",
            "shield->s.effects |= EF_POWERSCREEN",
            "shield->s.sound = gi.soundindex(ZAERO_PLASMA_SHIELD_ACTIVE_SOUND)",
            "AngleVectors(ent->client->v_angle, forward, right, up)",
            "shield->s.angles = vectoangles(forward)",
            "ent->s.origin + (forward * ZAERO_PLASMA_SHIELD_FORWARD_OFFSET)",
            "(forward * 10.0f) - (right * 30.0f) - (up * 30.0f)",
            "(forward * 5.0f) + (right * 30.0f) + (up * 50.0f)",
            "ClearBounds(shield->mins, shield->maxs)",
            "AddPointToBounds(front_bottom_left, shield->mins, shield->maxs)",
            "AddPointToBounds(back_top_right, shield->mins, shield->maxs)",
            "gi.linkentity(shield)",
        ):
            self.assertIn(contract, SOURCE if contract.startswith("ZAERO_") else use)

    def test_health_expiry_callbacks_and_mode_sounds_are_exact(self) -> None:
        use = function_body(SOURCE, "void Use_ZaeroPlasmaShield")
        expire = function_body(SOURCE, "THINK(Zaero_PlasmaShieldExpire)")
        die = function_body(SOURCE, "DIE(Zaero_PlasmaShieldDie)")
        for contract in (
            "ZAERO_PLASMA_SHIELD_HEALTH = 4000",
            "ZAERO_PLASMA_SHIELD_LIFETIME = 10_sec",
            "shield->health = shield->max_health = ZAERO_PLASMA_SHIELD_HEALTH",
            "shield->takedamage = true",
            "shield->die = Zaero_PlasmaShieldDie",
            "shield->think = Zaero_PlasmaShieldExpire",
            "level.time + ZAERO_PLASMA_SHIELD_LIFETIME",
        ):
            self.assertIn(contract, SOURCE if contract.startswith("ZAERO_") else use)
        self.assertIn("if (deathmatch->integer)", expire)
        self.assertIn("ZAERO_PLASMA_SHIELD_DIE_SOUND", expire)
        self.assertIn("CHAN_VOICE", expire)
        self.assertIn("G_FreeEdict(self)", expire)
        self.assertIn("Zaero_PlasmaShieldExpire(self)", die)

    def test_no_gameplay_owner_but_saved_generation_metadata_is_retained(self) -> None:
        use = function_body(SOURCE, "void Use_ZaeroPlasmaShield")
        self.assertNotIn("shield->owner", use)
        self.assertIn("shield->activator = ent", use)
        self.assertIn("shield->count = ent->spawn_count", use)

        stale = function_body(SOURCE, "void Zaero_ClearStalePlasmaShieldPlacer")
        self.assertIn("!self->activator->inuse", stale)
        self.assertIn("self->activator->spawn_count != self->count", stale)
        self.assertIn("self->activator = nullptr", stale)
        self.assertIn("self->count = 0", stale)

    def test_source_power_armor_formula_is_isolated_from_native_drift(self) -> None:
        helper = function_body(SOURCE, "bool Zaero_PlasmaShieldCheckPowerArmor")
        for contract in (
            "strcmp(ent->classname, ZAERO_PLASMA_SHIELD_CLASSNAME) == 0",
            "const int shield_damage = (2 * damage) / 3",
            "save = min(ent->health * 2, shield_damage)",
        ):
            self.assertIn(contract, SOURCE if contract.startswith("strcmp") else helper)
        for native_drift in (
            "ctf->integer",
            "DAMAGE_ENERGY",
            "TE_SCREEN_SPARKS",
            "G_CheckPowerArmor",
        ):
            self.assertNotIn(native_drift, helper)
        self.assertNotIn("ent->health -=", helper)

        # Golden ordinary-hit arithmetic, including the low-damage rounding
        # boundary and the one-hit destruction threshold at full health.
        for damage, absorbed, health_damage in (
            (1, 0, 1),
            (2, 1, 1),
            (3, 2, 1),
            (300, 200, 100),
            (11997, 7998, 3999),
            (11998, 7998, 4000),
            (11999, 7999, 4000),
            (12000, 8000, 4000),
        ):
            actual_absorbed = min(4000 * 2, (2 * damage) // 3)
            self.assertEqual(actual_absorbed, absorbed)
            self.assertEqual(damage - actual_absorbed, health_damage)

        emp = COMBAT.index("Zaero_EMPNukeCheck(ent, point)")
        shield = COMBAT.index("Zaero_PlasmaShieldCheckPowerArmor", emp)
        client = COMBAT.index("if (client)", shield)
        self.assertLess(emp, shield)
        self.assertLess(shield, client)
        integration = COMBAT[shield:client]
        self.assertIn("SpawnDamage(TE_SHIELD_SPARKS", integration)
        self.assertIn("level.time + 200_ms", integration)
        self.assertIn("return zaero_plasma_shield_save", integration)

    def test_sniper_penetrates_only_the_exact_shield_path(self) -> None:
        fire = function_body(SNIPER, "void Zaero_FireSniperBullet")
        shield = fire.index('Q_strcasecmp(tr.ent->classname, "PlasmaShield")')
        ignore = fire.index("ignore = tr.ent", shield)
        resume = fire.index("continue", ignore)
        damage = fire.index("T_Damage", resume)
        self.assertLess(shield, ignore)
        self.assertLess(ignore, resume)
        self.assertLess(resume, damage)

    def test_item_and_project_replace_the_placeholder(self) -> None:
        item = item_block("IT_AMMO_PLASMASHIELD")
        self.assertIn("Use_ZaeroPlasmaShield", item)
        self.assertIn("IF_AMMO | IF_POWERUP_WHEEL", item)
        self.assertNotIn("Pending", item)
        self.assertNotIn("Use_ZaeroPlasmaShieldPending", ITEMS)
        self.assertNotIn("Use_ZaeroPlasmaShieldPending", WEAPONS)

        self.assertIn("void Use_ZaeroPlasmaShield", HEADER)
        self.assertIn("bool Zaero_PlasmaShieldCheckPowerArmor", HEADER)
        for manifest in (PROJECT, FILTERS):
            self.assertIn("zaero\\g_zaero_plasma_shield.cpp", manifest)
            self.assertIn("zaero\\g_zaero_plasma_shield.h", manifest)


if __name__ == "__main__":
    unittest.main()
