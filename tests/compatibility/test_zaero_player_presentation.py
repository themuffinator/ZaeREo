"""Static contracts for Zaero player commands, wheel HUD, and obituaries."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMMANDS = (ROOT / "src" / "g_cmds.cpp").read_text(encoding="utf-8")
CLIENT = (ROOT / "src" / "p_client.cpp").read_text(encoding="utf-8")
HUD = (ROOT / "src" / "p_hud.cpp").read_text(encoding="utf-8")
SPAWN = (ROOT / "src" / "g_spawn.cpp").read_text(encoding="utf-8")
LOCAL = (ROOT / "src" / "g_local.h").read_text(encoding="utf-8")
SAVE = (ROOT / "src" / "g_save.cpp").read_text(encoding="utf-8")
ITEMS = (ROOT / "src" / "g_items.cpp").read_text(encoding="utf-8")
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


class ZaeroPlayerPresentationContractTests(unittest.TestCase):
    def test_supplied_source_oracles_are_identity_locked(self) -> None:
        expected = {
            "g_cmds.c": "ea6fd0c0e44bbc4c3849dda0e0002167a54fa835e31fa89489a44e16ac6a3500",
            "p_client.c": "f0e871b588fb4527bcafb42458bc810f4eef748c32f245646de760e9036db6a4",
            "p_hud.c": "310e2bc0e11fd73041d8a96ed04b6570377ebb180e92a5eb95b15dcabe359765",
            "g_spawn.c": "60cf870a254e8f80aa5a2a28eb81b7522534f84c7221002247dfae9c091cc75b",
        }
        records = {
            record["path"]: record
            for record in SOURCE_AUDIT["comparison"]["file_records"]
        }
        for path, digest in expected.items():
            self.assertEqual(records[path]["zaero_sha256"], digest)
            self.assertEqual(records[path]["status"], "modified")

    def test_showorigin_is_client_local_saved_and_uses_private_stats(self) -> None:
        self.assertIn("bool zaero_show_origin", LOCAL)
        self.assertEqual(SAVE.count("FIELD_AUTO(zaero_show_origin)"), 1)

        toggle = function_body(COMMANDS, "void Cmd_ZaeroShowOrigin_f")
        self.assertIn("zaero_show_origin = !ent->client->zaero_show_origin", toggle)
        self.assertIn('"Show origin ON\\n"', toggle)
        self.assertIn('"Show origin OFF\\n"', toggle)
        command = function_body(COMMANDS, "void ClientCommand")
        self.assertIn('Q_strcasecmp(cmd, "showorigin")', command)
        self.assertIn("Cmd_ZaeroShowOrigin_f(ent)", command)

        stats = function_body(HUD, "void G_SetStats")
        for stat in (
            "STAT_ZAERO_SHOW_ORIGIN",
            "STAT_ZAERO_ORIGIN_X",
            "STAT_ZAERO_ORIGIN_Y",
            "STAT_ZAERO_ORIGIN_Z",
        ):
            self.assertIn(stat, stats)
        self.assertEqual(stats.count("static_cast<int32_t>(ent->s.origin["), 3)
        self.assertIn("STAT_ZAERO_ORIGIN_X] = 0", stats)
        self.assertIn("STAT_ZAERO_ORIGIN_Y] = 0", stats)
        self.assertIn("STAT_ZAERO_ORIGIN_Z] = 0", stats)

        statusbar = function_body(SPAWN, "static void G_InitStatusbar")
        expected_layout = (
            ".ifstat(STAT_ZAERO_SHOW_ORIGIN)\n"
            "\t\t.xl(0).yb(-120).num(5, STAT_ZAERO_ORIGIN_X)\n"
            "\t\t.yb(-96).num(5, STAT_ZAERO_ORIGIN_Y)\n"
            "\t\t.yb(-72).num(5, STAT_ZAERO_ORIGIN_Z)"
        )
        self.assertIn(expected_layout, statusbar)

    def test_wheel_owned_bits_cover_all_eligible_registered_weapons(self) -> None:
        stats = function_body(HUD, "void G_SetStats")
        wheel = stats[stats.index("uint32_t weaponbits") : stats.index("// Zaero's production showorigin")]
        self.assertIn("invIndex < IT_TOTAL", wheel)
        self.assertIn("weapon->flags & IF_WEAPON", wheel)
        self.assertIn("weapon->weapon_wheel_index >= 0", wheel)
        self.assertIn("1u << weapon->weapon_wheel_index", wheel)
        self.assertNotIn("invIndex <= IT_WEAPON_DISRUPTOR", wheel)

        for item_id in (
            "IT_WEAPON_FLAREGUN",
            "IT_AMMO_IRED",
            "IT_WEAPON_SONICCANNON",
        ):
            start = ITEMS.index(f"/* id */ {item_id}")
            end = ITEMS.index("\n\t},", start)
            block = ITEMS[start:end]
            self.assertIn("IF_WEAPON", block)
            self.assertNotIn("IF_NO_WEAPON_SELECTION", block)

    def test_five_second_kill_guard_stays_in_native_lifecycle(self) -> None:
        kill = function_body(COMMANDS, "void Cmd_Kill_f")
        self.assertIn("resp.spectator", kill)
        self.assertIn("(level.time - ent->client->respawn_time) < 5_sec", kill)
        self.assertIn("player_die(ent, ent, ent, 100000", kill)
        self.assertNotIn("respawn(ent)", kill)

    def test_all_25_monster_obituaries_are_exact_safe_fallbacks(self) -> None:
        expected = {
            "monster_soldier": "{} was slaughtered by a Shotgun Guard.\\n",
            "monster_soldier_light": "{} was exterminated by a Light Guard.\\n",
            "monster_soldier_ss": "{} was eradicated by a Machinegun Guard.\\n",
            "monster_tank": "{} felt the pain of a Tank.\\n",
            "monster_tank_commander": "{} was annihilated by a Tank Commander.\\n",
            "monster_hound": "{} was leg humped to death by a Hound.\\n",
            "monster_handler": "{} was ravished by an Enforcer.\\n",
            "monster_infantry": "{} was obliterated by an Enforcer.\\n",
            "monster_sentien": "{} was lobotomized by a badass Sentien.\\n",
            "monster_zboss": "{} was killed by a big, bad MOFO.\\n",
            "monster_gunner": "A Gunner went medievil on {}'s ass.\\n",
            "monster_berserk": "{} was shattered by a Berserker.  TRESPASSA!\\n",
            "monster_chick": "{} was bitch slapped by an Iron Maiden.\\n",
            "monster_parasite": "{} was sucked by a Parasite.\\n",
            "monster_mutant": "{} was demolished by a Mutant.\\n",
            "monster_flyer": "{} was killed by a Flyer.\\n",
            "monster_hover": "{} was waxed out by an Icarus.\\n",
            "monster_medic": "{} overdosed on Medics\\n",
            "monster_floater": "{} was tweaked by a Technician.\\n",
            "monster_flipper": "{} was killed by a Barracuda Shark.\\n",
            "monster_gladiator": "{} was made into swiss cheese by a Gladiator.\\n",
            "monster_brain": "{} was scanned by a Brain.\\n",
            "monster_supertank": "{} was stomped by a Super Tank.\\n",
            "monster_boss2": "{} was killed by some flying boss thingy.\\n",
            "monster_jorg": "{} was assassinated by a Jorg.\\n",
        }
        table = CLIENT[
            CLIENT.index("zaero_monster_obituaries =") : CLIENT.index(
                "const char *Zaero_GetMonsterObituary"
            )
        ]
        found = dict(
            re.findall(
                r'\{\s*"(monster_[^"]+)",\s*"([^"]+)",\s*(?:true|false)\s*\}',
                table,
            )
        )
        self.assertEqual(found, expected)
        self.assertNotIn("%s", table)

        lookup = function_body(CLIENT, "const char *Zaero_GetMonsterObituary")
        self.assertIn("attacker->svflags & SVF_MONSTER", lookup)
        self.assertIn("Q_strcasecmp(attacker->classname, obituary.classname)", lookup)
        self.assertIn("level.is_zaero || obituary.zaero_owned", lookup)

        obituary = function_body(CLIENT, "void ClientObituary")
        self.assertIn("Zaero_GetMonsterObituary(attacker)", obituary)
        self.assertIn("gi.LocBroadcast_Print(PRINT_MEDIUM, monster_obituary", obituary)

    def test_custom_mods_and_skin_first_gender_contract_are_explicit(self) -> None:
        obituary = function_body(CLIENT, "void ClientObituary")
        for mod in (
            "MOD_ZAERO_AUTOCANNON",
            "MOD_ZAERO_FLARE",
            "MOD_ZAERO_GL_POLYBLEND",
            "MOD_ZAERO_SONIC_CANNON",
            "MOD_ZAERO_TRIPBOMB",
            "MOD_ZAERO_SNIPER_RIFLE",
            "MOD_ZAERO_A2K",
        ):
            self.assertIn(f"case {mod}:", obituary)

        female = function_body(CLIENT, "bool Zaero_IsFemaleBySkin")
        self.assertIn('Info_ValueForKey(ent->client->pers.userinfo, "skin"', female)
        self.assertIn("skin[0] == 'f' || skin[0] == 'F'", female)
        self.assertNotIn('"gender"', female)

        for message in (
            "{} tripped on her own grenade.\\n",
            "{} tripped on his own grenade.\\n",
            "{} blew herself up.\\n",
            "{} blew himself up.\\n",
            "{} killed herself.\\n",
            "{} killed himself.\\n",
        ):
            self.assertIn(message, obituary)
        self.assertGreaterEqual(obituary.count("if (level.is_zaero)"), 3)


if __name__ == "__main__":
    unittest.main()
