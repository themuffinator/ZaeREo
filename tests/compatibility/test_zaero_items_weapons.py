from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCAL = (ROOT / "src" / "g_local.h").read_text(encoding="utf-8")
BG_LOCAL = (ROOT / "src" / "bg_local.h").read_text(encoding="utf-8")
ITEMS = (ROOT / "src" / "g_items.cpp").read_text(encoding="utf-8")
WEAPONS = (ROOT / "src" / "zaero" / "g_zaero_weapons.cpp").read_text(encoding="utf-8")
SAVE = (ROOT / "src" / "g_save.cpp").read_text(encoding="utf-8")
CLIENT = (ROOT / "src" / "p_client.cpp").read_text(encoding="utf-8")
P_WEAPON = (ROOT / "src" / "p_weapon.cpp").read_text(encoding="utf-8")
VIEW = (ROOT / "src" / "p_view.cpp").read_text(encoding="utf-8")
MONSTER = (ROOT / "src" / "g_monster.cpp").read_text(encoding="utf-8")
COMMANDS = (ROOT / "src" / "g_cmds.cpp").read_text(encoding="utf-8")


ZAERO_ITEMS = [
    ("IT_WEAPON_PUSH", "weapon_push", None, None, 0, "IT_NULL"),
    (
        "IT_WEAPON_FLAREGUN",
        "weapon_flaregun",
        "models/weapons/g_flare/tris.md2",
        "w_flare",
        1,
        "IT_AMMO_FLARES",
    ),
    (
        "IT_AMMO_IRED",
        "ammo_ired",
        "models/items/ammo/ireds/tris.md2",
        "w_ired",
        3,
        "IT_AMMO_IRED",
    ),
    (
        "IT_WEAPON_SNIPERRIFLE",
        "weapon_sniperrifle",
        "models/weapons/g_sniper/tris.md2",
        "w_sniper",
        3,
        "IT_AMMO_SLUGS",
    ),
    (
        "IT_WEAPON_SONICCANNON",
        "weapon_soniccannon",
        "models/weapons/g_sonic/tris.md2",
        "w_sonic",
        1,
        "IT_AMMO_CELLS",
    ),
    (
        "IT_AMMO_A2K",
        "ammo_a2k",
        "models/weapons/g_a2k/tris.md2",
        "w_a2k",
        1,
        "IT_AMMO_A2K",
    ),
    (
        "IT_AMMO_FLARES",
        "ammo_flares",
        "models/items/ammo/flares/tris.md2",
        "a_flares",
        3,
        "IT_NULL",
    ),
    (
        "IT_AMMO_EMPNUKE",
        "ammo_empnuke",
        "models/weapons/g_enuke/tris.md2",
        "w_enuke",
        1,
        "IT_AMMO_EMPNUKE",
    ),
    (
        "IT_ITEM_VISOR",
        "item_visor",
        "models/items/visor/tris.md2",
        "i_visor",
        30,
        "IT_AMMO_CELLS",
    ),
    (
        "IT_AMMO_PLASMASHIELD",
        "ammo_plasmashield",
        "models/items/plasma/tris.md2",
        "i_plasma",
        5,
        "IT_NULL",
    ),
    (
        "IT_KEY_LANDING_AREA",
        "key_landing_area",
        "models/items/keys/key/tris.md2",
        "k_bluekey",
        0,
        "IT_NULL",
    ),
    (
        "IT_KEY_LAB",
        "key_lab",
        "models/items/keys/pass/tris.md2",
        "k_security",
        0,
        "IT_NULL",
    ),
    (
        "IT_KEY_CLEARANCE_PASS",
        "key_clearancepass",
        "models/items/keys/pass/tris.md2",
        "k_security",
        0,
        "IT_NULL",
    ),
    (
        "IT_KEY_ENERGY",
        "key_energy",
        "models/items/keys/energy/tris.md2",
        "k_energy",
        0,
        "IT_NULL",
    ),
    (
        "IT_KEY_LAVA",
        "key_lava",
        "models/items/keys/lava/tris.md2",
        "k_lava",
        0,
        "IT_NULL",
    ),
    (
        "IT_KEY_SLIME",
        "key_slime",
        "models/items/keys/slime/tris.md2",
        "k_slime",
        0,
        "IT_NULL",
    ),
]


def item_block(item_id: str) -> str:
    start = ITEMS.index(f"/* id */ {item_id},")
    comma_end = ITEMS.find("\n\t},", start)
    list_end = ITEMS.find("\n\t}\n};", start)
    candidates = [end for end in (comma_end, list_end) if end >= 0]
    end = min(candidates)
    return ITEMS[start:end]


def item_flags(item_id: str) -> set[str]:
    block = item_block(item_id)
    match = re.search(r"/\* flags \*/ (?P<flags>.*?),\s*/\* vwep_model \*/", block, re.S)
    if match is None:
        raise AssertionError(f"missing flags field for {item_id}")
    return set(re.findall(r"IF_[A-Z_]+", match.group("flags")))


class ZaeroItemRegistryTests(unittest.TestCase):
    def test_all_production_classnames_have_stable_order_and_metadata(self) -> None:
        enum = re.search(r"enum item_id_t\s*:[^{]+\{(?P<body>.*?)\n\};", LOCAL, re.S)
        self.assertIsNotNone(enum)
        enum_body = enum.group("body")
        positions = [enum_body.index(item_id) for item_id, *_ in ZAERO_ITEMS]
        self.assertEqual(positions, sorted(positions))

        for item_id, classname, model, icon, quantity, ammo in ZAERO_ITEMS:
            block = item_block(item_id)
            self.assertIn(f'/* classname */ "{classname}"', block)
            if model is None:
                self.assertIn("/* world_model */ nullptr", block)
            else:
                self.assertIn(f'/* world_model */ "{model}"', block)
            if icon is None:
                self.assertIn("/* icon */ nullptr", block)
            else:
                self.assertIn(f'/* icon */ "{icon}"', block)
            self.assertIn(f"/* quantity */ {quantity}", block)
            self.assertIn(f"/* ammo */ {ammo}", block)

        self.assertIn("q_countof(itemlist) == IT_TOTAL", ITEMS)
        self.assertIn("IT_TOTAL <= MAX_ITEMS", LOCAL)

    def test_ammo_tags_caps_pack_and_wheels_are_complete(self) -> None:
        for ammo in ("FLARES", "IRED", "EMPNUKE", "A2K", "PLASMASHIELD"):
            self.assertIn(f"AMMO_{ammo}", BG_LOCAL)
            self.assertIn(f"/* tag */ AMMO_{ammo}", ITEMS)

        persist = CLIENT[CLIENT.index("client->pers.max_ammo.fill(50)") : CLIENT.index("NoAmmoWeaponChange(ent, false)")]
        expected_caps = {
            "AMMO_FLARES": 30,
            "AMMO_IRED": 30,
            "AMMO_A2K": 1,
            "AMMO_EMPNUKE": 50,
            "AMMO_PLASMASHIELD": 20,
        }
        for ammo, cap in expected_caps.items():
            self.assertIn(f"max_ammo[{ammo}] = {cap}", persist)

        pack = ITEMS[ITEMS.index("bool Pickup_Pack") : ITEMS.index("void Use_Quad")]
        for ammo, cap in {
            "AMMO_IRED": 100,
            "AMMO_A2K": 1,
            "AMMO_EMPNUKE": 100,
            "AMMO_PLASMASHIELD": 40,
        }.items():
            self.assertIn(f"G_AdjustAmmoCap(other, {ammo}, {cap})", pack)
            self.assertIn(f"G_AddAmmoAndCapQuantity(other, {ammo})", pack)
        self.assertNotIn("AMMO_FLARES", pack)

        self.assertIn("ZAERO_AMMO_WHEEL_SLOTS = 17", ITEMS)
        self.assertIn("ZAERO_WEAPON_WHEEL_SLOTS = 25", ITEMS)
        self.assertIn("AMMO_MAX == ZAERO_AMMO_WHEEL_SLOTS", ITEMS)
        self.assertIn("itemlist[i].flags & IF_NO_WEAPON_SELECTION", ITEMS)

    def test_ammo_spawnflag_contracts_are_zaero_only(self) -> None:
        pickup = ITEMS[ITEMS.index("bool Pickup_Ammo") : ITEMS.index("void Drop_Ammo")]
        spawn = ITEMS[ITEMS.index("void SpawnItem") : ITEMS.index("void SetItemNames")]

        self.assertIn("level.is_zaero && ent->spawnflags.has(SPAWNFLAG_ITEM_MAX)", pickup)
        self.assertIn("if (oldcount >= count)", pickup)
        self.assertIn("count -= oldcount", pickup)
        self.assertIn(
            "level.is_zaero && ent->spawnflags.has(SPAWNFLAG_ITEM_TOSS_SPAWN)", pickup
        )
        self.assertIn("SetRespawn(ent, 15_sec)", pickup)

        self.assertIn("valid_zaero_ammo_spawnflags", spawn)
        self.assertIn("level.is_zaero && (item->flags & IF_AMMO)", spawn)
        self.assertIn("!(ent->spawnflags.value & ~0x0Fu)", spawn)
        self.assertIn("!valid_zaero_ammo_spawnflags", spawn)

        # Native deathmatch world-item respawn remains the first branch.
        self.assertLess(pickup.index("SetRespawn(ent, 30_sec)"), pickup.index("SetRespawn(ent, 15_sec)"))

    def test_zero_stack_drop_queues_a_safe_zaero_fallback(self) -> None:
        drop = ITEMS[ITEMS.index("void Drop_Ammo") : ITEMS.index("THINK(MegaHealth_think)")]

        self.assertIn("empties_active_ammo_weapon", drop)
        self.assertIn("item->flags & IF_AMMO", drop)
        self.assertIn("if (empties_active_ammo_weapon && !level.is_zaero)", drop)
        self.assertIn("$g_cant_drop_weapon", drop)
        self.assertLess(
            drop.index("pers.inventory[index] -= dropped->count"),
            drop.index("NoAmmoWeaponChange(ent, false)"),
        )

        # The shared path covers both the stock throwable and Zaero's
        # ammo-as-weapon items rather than special-casing one classname.
        for item_id in ("IT_AMMO_GRENADES", "IT_AMMO_IRED", "IT_AMMO_A2K", "IT_AMMO_EMPNUKE"):
            self.assertIn("/* drop */ Drop_Ammo", item_block(item_id))

        remove_ammo = P_WEAPON[P_WEAPON.index("void G_RemoveAmmo(edict_t *ent, int32_t quantity)") :]
        self.assertIn("if (level.is_zaero)", remove_ammo)
        self.assertIn("ammo = max(0, ammo - quantity)", remove_ammo)

    def test_complex_items_use_dedicated_callbacks_and_never_stock_aliases(self) -> None:
        callbacks = {
            "IT_AMMO_A2K": "Weapon_ZaeroA2KPending",
            "IT_ITEM_VISOR": "Use_ZaeroVisorPending",
            "IT_AMMO_PLASMASHIELD": "Use_ZaeroPlasmaShieldPending",
        }
        for item_id, callback in callbacks.items():
            self.assertIn(callback, item_block(item_id))
            self.assertIn(f"void {callback}", WEAPONS)
        self.assertGreaterEqual(WEAPONS.count("is not implemented yet"), len(callbacks))

        expected_flags = {
            "IT_AMMO_A2K": {
                "IF_AMMO",
                "IF_POWERUP",
                "IF_NO_WEAPON_SELECTION",
                "IF_PENDING_IMPLEMENTATION",
            },
        }
        for item_id, flags in expected_flags.items():
            self.assertEqual(item_flags(item_id), flags)
            self.assertNotIn("IF_TRANSIENT_WEAPON", flags)

        completed = {
            "IT_AMMO_IRED": ({"IF_AMMO", "IF_WEAPON"}, "Weapon_ZaeroIRED"),
            "IT_WEAPON_SNIPERRIFLE": (
                {"IF_WEAPON", "IF_STAY_COOP", "IF_NO_WEAPON_SELECTION"},
                "Weapon_ZaeroSniperRifle",
            ),
            "IT_AMMO_EMPNUKE": (
                {"IF_AMMO", "IF_NO_INFINITE_AMMO"},
                "Weapon_ZaeroEMPNuke",
            ),
        }
        for item_id, (flags, callback) in completed.items():
            block = item_block(item_id)
            self.assertEqual(item_flags(item_id), flags)
            self.assertIn(callback, block)
            self.assertNotIn("Pending", block)

        self.assertIn("Weapon_ZaeroSonicCannon", item_block("IT_WEAPON_SONICCANNON"))
        self.assertNotIn("Pending", item_block("IT_WEAPON_SONICCANNON"))
        self.assertEqual(
            item_flags("IT_WEAPON_SONICCANNON"), {"IF_WEAPON", "IF_STAY_COOP"}
        )

        self.assertIn("IF_TRANSIENT_WEAPON | IF_PENDING_IMPLEMENTATION", P_WEAPON)
        self.assertIn("IF_TRANSIENT_WEAPON | IF_PENDING_IMPLEMENTATION", ITEMS)

    def test_legacy_item_hide_surfaces_remain_independent(self) -> None:
        self.assertEqual(
            item_flags("IT_WEAPON_PUSH"),
            {
                "IF_WEAPON",
                "IF_STAY_COOP",
                "IF_NOT_GIVEABLE",
                "IF_NOT_RANDOM",
                "IF_NO_INVENTORY",
                "IF_NO_WEAPON_SELECTION",
                "IF_TRANSIENT_WEAPON",
            },
        )
        self.assertNotIn("IF_NO_INVENTORY", item_flags("IT_WEAPON_SNIPERRIFLE"))
        self.assertNotIn("IF_NO_INVENTORY", item_flags("IT_AMMO_A2K"))

        self.assertGreaterEqual(COMMANDS.count("IF_NO_INVENTORY"), 4)
        self.assertGreaterEqual(COMMANDS.count("IF_NO_WEAPON_SELECTION"), 2)
        weaplast = COMMANDS[COMMANDS.index("void Cmd_WeapLast_f") : COMMANDS.index("void Cmd_InvDrop_f")]
        self.assertNotIn("IF_NO_WEAPON_SELECTION", weaplast)

        autoswitch = ITEMS[ITEMS.index("void G_CheckAutoSwitch") : ITEMS.index("bool Pickup_Ammo")]
        self.assertIn("if (item->flags & IF_NO_WEAPON_SELECTION)", autoswitch)


class ZaeroPushAndFlareTests(unittest.TestCase):
    def test_push_contract_is_hidden_transient_and_mass_sensitive(self) -> None:
        push = item_block("IT_WEAPON_PUSH")
        for flag in (
            "IF_NO_INVENTORY",
            "IF_NO_WEAPON_SELECTION",
            "IF_TRANSIENT_WEAPON",
            "IF_NOT_GIVEABLE",
            "IF_NOT_RANDOM",
        ):
            self.assertIn(flag, push)
        self.assertIn("Weapon_ZaeroPush", push)

        for contract in (
            "ZAERO_PUSH_RANGE = 64.0f",
            "ZAERO_PUSH_DAMAGE = 2",
            "ZAERO_PUSH_KICK = 512",
            "ZAERO_PUSH_CONTACT_FRAME = 4",
            "ZAERO_PUSH_END_FRAME = 8",
            "tr.ent->movetype == MOVETYPE_FALLFLOAT",
            "original_mass / 4",
            "DAMAGE_NO_KNOCKBACK, MOD_HIT",
            "tr.ent->spawn_count == original_spawn_count",
        ):
            self.assertIn(contract, WEAPONS)

        self.assertIn("zaero_transient_lastweapon", P_WEAPON)
        self.assertIn("FIELD_AUTO(zaero_transient_lastweapon)", SAVE)

    def test_default_loadout_matches_single_coop_and_deathmatch_contract(self) -> None:
        loadout = CLIENT[CLIENT.index("ZAERO's hidden Push utility") : CLIENT.index("NoAmmoWeaponChange(ent, false)")]
        self.assertIn("inventory[IT_WEAPON_PUSH] = 1", loadout)
        self.assertIn("if (!deathmatch->integer)", loadout)
        self.assertIn("inventory[IT_WEAPON_BLASTER] = 1", loadout)
        self.assertIn("inventory[IT_WEAPON_FLAREGUN] = 1", loadout)
        self.assertIn("inventory[IT_AMMO_FLARES] = max(3", loadout)

    def test_weapons_without_rerelease_vwep_models_pack_safely(self) -> None:
        self.assertIn(
            "ent->client->pers.weapon && ent->client->pers.weapon->vwep_index",
            CLIENT,
        )
        self.assertIn("packed.vwep_index = 0", CLIENT)

    def test_flare_projectile_timing_animation_and_light_match_reference(self) -> None:
        for contract in (
            "ZAERO_FLARE_SPEED = 600",
            "ZAERO_FLARE_LIFETIME_DISTANCE = 8000",
            "ZAERO_FLARE_FLASH_RANGE = 256.0f",
            "ZAERO_FLARE_TICK = 100_ms",
            "ZAERO_FLARE_IGNITION_DELAY = 1_sec",
            "ZAERO_FLARE_BURNOUT_DELAY = 4_sec",
            "MOVETYPE_BOUNCE",
            "EF_ROCKET",
            "models/objects/flare/tris.md2",
            "gtime_t::from_sec(ZAERO_FLARE_LIFETIME_DISTANCE / ZAERO_FLARE_SPEED)",
            "if (++self->s.frame > 14)",
            "self->s.frame = 5",
            "THINK(Zaero_FlareThink)",
        ):
            self.assertIn(contract, WEAPONS)

        self.assertEqual(8000 // 600, 13)
        self.assertIn("G_RemoveAmmo(ent)", WEAPONS)
        self.assertIn("Weapon_Generic(ent, 5, 14, 44, 48", WEAPONS)

    def test_flash_is_per_client_saved_and_keeps_compensation_quirk(self) -> None:
        for field in ("zaero_flare_flash_ticks", "zaero_flare_flash_base"):
            self.assertIn(f"FIELD_AUTO({field})", SAVE)
            self.assertIn(f"FIELD_AUTO(monsterinfo.{field})", SAVE)

        for contract in (
            '"gl_polyblend"',
            "ZDM_NO_GL_POLYBLEND_DAMAGE = 1 << 0",
            "ZAERO_FLARE_COMPENSATION_MAX_DAMAGE = 10",
            "MOD_ZAERO_GL_POLYBLEND",
            'strcmp(target->classname, "monster_zboss")',
            "FoundTarget(target)",
            "ZAERO_REFERENCE_TICKS_PER_SECOND = 10.0f",
            "static_cast<int32_t>(ratio * ZAERO_PLAYER_FLASH_ADD)",
            "static_cast<int32_t>(ratio * ZAERO_MONSTER_FLASH_ADD)",
        ):
            self.assertIn(contract, WEAPONS)

        self.assertIn("Zaero_AddFlareBlend(ent)", VIEW)
        self.assertIn("Zaero_UpdateMonsterFlareFlash(self)", MONSTER)
        self.assertIn("Zaero_MonsterMoveAwayFromFlare(self, dist)", (ROOT / "src" / "g_ai.cpp").read_text(encoding="utf-8"))
        self.assertIn('Q_strcasecmp(flare->classname, "flare")', WEAPONS)
        self.assertIn("SV_NewChaseDir(ent, goal, distance)", WEAPONS)
        self.assertIn("screen_blend", WEAPONS)
        self.assertIn("turned off gl_polyblend", CLIENT)


if __name__ == "__main__":
    unittest.main()
