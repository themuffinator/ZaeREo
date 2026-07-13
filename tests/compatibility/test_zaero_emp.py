"""Source contracts and integration ledger for Zaero's EMP Nuke.

The oracle is the supplied ``z_item.c`` (SHA-256
23dcc0fda023260c73e26260bb86d2c78d6edfc29f0486a4b6472568561f94ae)
plus every supplied ``EMPNukeCheck`` call site.  Keeping the call-site matrix
here is important: Zaero did not blanket-disable all weapons in an EMP field.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = ROOT / "src" / "zaero" / "g_zaero_emp.cpp"
HEADER_PATH = ROOT / "src" / "zaero" / "g_zaero_emp.h"
SOURCE = SOURCE_PATH.read_text(encoding="utf-8")
HEADER = HEADER_PATH.read_text(encoding="utf-8")
SONIC_HEADER = (
    ROOT / "src" / "zaero" / "g_zaero_sonic.h"
).read_text(encoding="utf-8")
PROJECT = (ROOT / "src" / "game.vcxproj").read_text(encoding="utf-8")
FILTERS = (ROOT / "src" / "game.vcxproj.filters").read_text(encoding="utf-8")
ITEMS = (ROOT / "src" / "g_items.cpp").read_text(encoding="utf-8")
MAIN = (ROOT / "src" / "g_main.cpp").read_text(encoding="utf-8")
LOCAL = (ROOT / "src" / "g_local.h").read_text(encoding="utf-8")
SAVE = (ROOT / "src" / "g_save.cpp").read_text(encoding="utf-8")
PLAYER_WEAPONS = (ROOT / "src" / "p_weapon.cpp").read_text(encoding="utf-8")
SOURCE_AUDIT = json.loads(
    (ROOT / "docs" / "audits" / "source-delta.json").read_text(
        encoding="utf-8"
    )
)
ASSET_AUDIT = (
    ROOT / "docs" / "audits" / "assets.json"
).read_text(encoding="utf-8")


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


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


# Every query in the supplied source, including the second query at Sonic
# release.  The path in column one is the Rerelease integration destination;
# Zaero-only systems intentionally live under src/zaero.
LEGACY_QUERY_SITES = (
    ("src/g_combat.cpp", "CheckPowerArmor", 1),
    ("src/g_monster.cpp", "monster_fire_blaster", 1),
    ("src/g_monster.cpp", "monster_fire_rocket", 1),
    ("src/g_monster.cpp", "monster_fire_railgun", 1),
    ("src/g_monster.cpp", "monster_fire_bfg", 1),
    ("src/g_target.cpp", "use_target_blaster", 1),
    ("src/g_turret.cpp", "turret_breach_fire", 1),
    ("src/m_boss2.cpp", "boss2_firebullet_right", 1),
    ("src/m_boss2.cpp", "boss2_firebullet_left", 1),
    ("src/m_boss31.cpp", "jorg_firebullet_right", 1),
    ("src/m_boss31.cpp", "jorg_firebullet_left", 1),
    ("src/m_boss32.cpp", "makronBFG", 1),
    ("src/m_infantry.cpp", "InfantryMachineGun", 1),
    ("src/m_supertank.cpp", "supertankMachineGun", 1),
    ("src/m_tank.cpp", "TankMachineGun", 1),
    ("src/p_weapon.cpp", "Weapon_RocketLauncher_Fire", 1),
    ("src/p_weapon.cpp", "Blaster_Fire", 1),
    ("src/p_weapon.cpp", "Chaingun_Fire", 1),
    ("src/p_weapon.cpp", "weapon_railgun_fire", 1),
    ("src/p_weapon.cpp", "weapon_bfg_fire", 1),
    ("src/zaero/g_zaero_autocannon.cpp", "Zaero_AutocannonFire", 1),
    ("src/zaero/g_zaero_plasma_shield.cpp", "Use_ZaeroPlasmaShield", 1),
    ("src/zaero/g_zaero_sentien.cpp", "Zaero_SentienFireBullet", 1),
    ("src/zaero/g_zaero_sentien.cpp", "Zaero_SentienDoBlast", 1),
    ("src/zaero/g_zaero_sentien.cpp", "Zaero_SentienDoLaser", 1),
    ("src/zaero/g_zaero_ired.cpp", "Zaero_IREDLaserThink", 1),
    ("src/zaero/g_zaero_sonic.cpp", "Zaero_SonicEMPBlocked", 2),
)


# Shared work root must wire after this isolated source is accepted.  Save
# callback registration needs no g_save.cpp row: THINK creates registrations,
# and all field state uses already-registered edict members.
REQUIRED_INTEGRATION_POINTS = (
    "add g_zaero_emp files to src/game.vcxproj and src/game.vcxproj.filters",
    "include g_zaero_emp.h where the callback/query is used",
    "replace Weapon_ZaeroEMPNukePending in IT_AMMO_EMPNUKE",
    "remove IF_PENDING_IMPLEMENTATION from IT_AMMO_EMPNUKE",
    "call Zaero_SetSonicEMPCheck(Zaero_EMPNukeCheck) during game init",
    "use Zaero_FireEMPNuke for monster_zboss radius-1024 events",
    "route only LEGACY_QUERY_SITES through Zaero_EMPNukeCheck",
    "play Zaero_PlayEMPMisfire at blocked attack sites",
    "preserve/save the BFG latch: clear at frame 9, misfire once, suppress both callbacks",
    "update feature/entity/quirk/map ledgers and add live save/overlap tests",
)


class ZaeroEMPContractTests(unittest.TestCase):
    def test_supplied_source_oracle_and_explicit_query_matrix(self) -> None:
        records = SOURCE_AUDIT["comparison"]["file_records"]
        z_item = next(record for record in records if record["path"] == "z_item.c")
        self.assertEqual(
            z_item["zaero_sha256"],
            "23dcc0fda023260c73e26260bb86d2c78d6edfc29f0486a4b6472568561f94ae",
        )
        self.assertEqual(z_item["status"], "zaero_only")

        self.assertEqual(len(LEGACY_QUERY_SITES), 27)
        self.assertEqual(sum(site[2] for site in LEGACY_QUERY_SITES), 28)
        self.assertEqual(
            [site for site in LEGACY_QUERY_SITES if site[1] == "Zaero_SonicEMPBlocked"],
            [("src/zaero/g_zaero_sonic.cpp", "Zaero_SonicEMPBlocked", 2)],
        )

        # These omissions are as important as the affected list.  The source
        # never queried generic bullets/shotguns/grenades or Zaero's Push,
        # Flare, Sniper, A2K, and EMP deployment paths.
        affected_names = {site[1] for site in LEGACY_QUERY_SITES}
        for unaffected in (
            "monster_fire_bullet",
            "monster_fire_shotgun",
            "monster_fire_grenade",
            "Machinegun_Fire",
            "weapon_shotgun_fire",
            "weapon_supershotgun_fire",
            "weapon_grenadelauncher_fire",
            "Weapon_ZaeroPush",
            "Weapon_ZaeroFlareGun",
            "Weapon_ZaeroSniperRifle",
            "Weapon_ZaeroA2K",
            "Weapon_ZaeroEMPNuke",
        ):
            self.assertNotIn(unaffected, affected_names)

    def test_field_creation_is_full_radius_immediately_and_has_no_damage(self) -> None:
        fire = function_body(SOURCE, "edict_t *Zaero_FireEMPNuke")
        for contract in (
            "if (!level.is_zaero)",
            "return nullptr",
            "gi.sound(owner, CHAN_VOICE",
            "ZAERO_EMP_TRIGGER_SOUND",
            "empnuke->owner = owner",
            "empnuke->count = owner ? owner->spawn_count : 0",
            "empnuke->dmg = radius",
            "empnuke->s.origin = center",
            "empnuke->classname = ZAERO_EMP_CENTER_CLASSNAME",
            "empnuke->movetype = MOVETYPE_NONE",
            "gi.modelindex(ZAERO_EMP_BLAST_MODEL)",
            "empnuke->think = Zaero_EMPBlastAnim",
            "level.time + ZAERO_EMP_ANIMATION_TICK",
            "gi.linkentity(empnuke)",
        ):
            self.assertIn(contract, fire)

        self.assertIn("ZAERO_EMP_PLAYER_RADIUS = 1024", SOURCE)
        self.assertIn('ZAERO_EMP_CENTER_CLASSNAME = "EMPNukeCenter"', SOURCE)
        self.assertIn(
            'ZAERO_EMP_BLAST_MODEL = "models/objects/b_explode/tris.md2"',
            SOURCE,
        )
        self.assertNotIn("T_Damage", SOURCE)
        self.assertNotIn("T_RadiusDamage", SOURCE)
        self.assertNotIn("MOD_ZAERO_EMP", SOURCE)
        self.assertNotIn("DAMAGE_", SOURCE)

    def test_visible_blast_then_hidden_active_lifetime_is_exact_at_40hz(self) -> None:
        self.assertIn("ZAERO_EMP_LAST_VISIBLE_FRAME = 5", SOURCE)
        self.assertIn("ZAERO_EMP_ANIMATION_TICK = 100_ms", SOURCE)
        self.assertIn("ZAERO_EMP_ACTIVE_LIFETIME = 30_sec", SOURCE)
        self.assertIn("THINK(Zaero_EMPBlastAnim)", SOURCE)
        self.assertIn("THINK(Zaero_EMPNukeFinish)", SOURCE)

        animation = function_body(SOURCE, "THINK(Zaero_EMPBlastAnim)")
        for contract in (
            "self->s.frame++",
            "self->s.skinnum++",
            "self->s.frame > ZAERO_EMP_LAST_VISIBLE_FRAME",
            "self->svflags |= SVF_NOCLIENT",
            "self->s.modelindex = 0",
            "self->s.frame = 0",
            "self->s.skinnum = 0",
            "self->think = Zaero_EMPNukeFinish",
            "level.time + ZAERO_EMP_ACTIVE_LIFETIME",
            "level.time + ZAERO_EMP_ANIMATION_TICK",
        ):
            self.assertIn(contract, animation)

        finish = function_body(SOURCE, "THINK(Zaero_EMPNukeFinish)")
        self.assertIn("G_FreeEdict(self)", finish)

        # Six 100 ms visible transitions plus thirty hidden seconds.  The
        # center is queryable for the whole 30.6 seconds (1,224 ticks at 40 Hz).
        visible_server_ticks = 6 * (40 // 10)
        hidden_server_ticks = 30 * 40
        self.assertEqual(visible_server_ticks, 24)
        self.assertEqual(hidden_server_ticks, 1200)
        self.assertEqual(visible_server_ticks + hidden_server_ticks, 1224)

        # The shipped empactive.wav exists, but the active-loop assignment was
        # commented out in the supplied game code and must remain silent.
        self.assertNotIn("empactive.wav", SOURCE)
        self.assertNotIn("self->s.sound", SOURCE)

    def test_query_preserves_owner_exemption_overlap_and_no_los(self) -> None:
        query = function_body(SOURCE, "bool Zaero_EMPNukeCheck")
        for contract in (
            "if (!level.is_zaero)",
            "G_FindByString<&edict_t::classname>(center, ZAERO_EMP_CENTER_CLASSNAME)",
            "subject && center->owner == subject",
            "center->count == subject->spawn_count",
            "(center->s.origin - position).length() <= center->dmg",
            "return true",
            "return false",
        ):
            self.assertIn(contract, query)

        # G_FindByString's loop gives overlapping fields their legacy any-match
        # behavior.  There is intentionally no visibility, trace, team, class,
        # client, monster, or takedamage filter.
        for forbidden in (
            "visible(",
            "CanDamage(",
            "traceline",
            "OnSameTeam",
            "subject->client",
            "SVF_MONSTER",
            "takedamage",
        ):
            self.assertNotIn(forbidden, query)

    def test_weapon_animation_ammo_and_deathmatch_audio_quirks(self) -> None:
        for contract in (
            "ZAERO_EMP_ACTIVATE_LAST_FRAME = 9",
            "ZAERO_EMP_FIRE_LAST_FRAME = 16",
            "ZAERO_EMP_IDLE_LAST_FRAME = 43",
            "ZAERO_EMP_DEACTIVATE_LAST_FRAME = 47",
            "ZAERO_EMP_ACTIVATE_SOUND_FRAME = 0",
            "ZAERO_EMP_SPIN_SOUND_FRAME = 11",
            "ZAERO_EMP_IDLE_SOUND_FRAME = 35",
            "static const int pause_frames[] = {25, 34, 43, 0}",
            "static const int fire_frames[] = {0}",
        ):
            self.assertIn(contract, SOURCE)

        weapon = function_body(SOURCE, "void Weapon_ZaeroEMPNuke(edict_t *ent)")
        self.assertIn("if (!level.is_zaero || !ent || !ent->client)", weapon)
        self.assertIn("weapon_think_time <= level.time", weapon)
        self.assertIn(
            "g_instant_weapon_switch->integer&&"
            "ent->client->weaponstate==WEAPON_ACTIVATING",
            compact(weapon),
        )
        self.assertLess(
            weapon.index("Zaero_EMPPlayWeaponSound(ent)"),
            weapon.index("\n\tWeapon_Generic(ent,"),
        )
        self.assertIn("old_state == WEAPON_FIRING", weapon)
        self.assertIn("old_frame != ent->client->ps.gunframe", weapon)
        self.assertIn(
            "ent->client->ps.gunframe == ZAERO_EMP_FIRE_LAST_FRAME", weapon
        )
        self.assertIn("Zaero_EMPNukeFire(ent)", weapon)
        self.assertIn("Zaero_EMPNukeNoGenericFire", weapon)
        self.assertNotIn("Weapon_PowerupSound", SOURCE)

        sounds = function_body(SOURCE, "void Zaero_EMPPlayWeaponSound")
        self.assertIn("if (!deathmatch->integer)", sounds)
        for sound_constant in (
            "ZAERO_EMP_ACTIVATE_SOUND",
            "ZAERO_EMP_SPIN_SOUND",
            "ZAERO_EMP_IDLE_SOUND",
        ):
            self.assertIn(sound_constant, sounds)

        fire = function_body(SOURCE, "void Zaero_EMPNukeFire")
        self.assertLess(fire.index("Zaero_FireEMPNuke"), fire.index("ammo--"))
        self.assertNotIn("G_CheckInfiniteAmmo", fire)
        self.assertIn("if (ammo != 0)", fire)
        self.assertIn("weaponstate = WEAPON_ACTIVATING", fire)
        self.assertIn("ps.gunframe = 0", fire)
        self.assertLess(
            fire.index("NoAmmoWeaponChange(ent, false)"),
            fire.index("\n\t\tChangeWeapon(ent)"),
        )

    def test_exact_sound_assets_and_missfire_spelling(self) -> None:
        used_assets = (
            "models/objects/b_explode/tris.md2",
            "items/empnuke/emp_trg.wav",
            "items/empnuke/emp_act.wav",
            "items/empnuke/emp_spin.wav",
            "items/empnuke/emp_idle.wav",
            "items/empnuke/emp_missfire.wav",
        )
        for asset in used_assets:
            self.assertIn(asset, SOURCE)

        # The normalized asset audit includes the required files with the
        # engine's sound/ prefix, plus the intentionally unused active loop.
        for asset in used_assets[1:]:
            self.assertIn(f'"path": "sound/{asset}"', ASSET_AUDIT)
        self.assertIn(
            '"path": "models/objects/b_explode/tris.md2"', ASSET_AUDIT
        )
        self.assertIn(
            '"path": "sound/items/empnuke/empactive.wav"', ASSET_AUDIT
        )

        misfire = function_body(SOURCE, "void Zaero_PlayEMPMisfire")
        self.assertIn("if (!level.is_zaero || !subject)", misfire)
        self.assertIn("ZAERO_EMP_MISFIRE_SOUND", misfire)
        self.assertIn("CHAN_AUTO", misfire)

    def test_save_registration_state_and_cleanup_need_no_new_fields(self) -> None:
        # THINK registers both callbacks with the Rerelease JSON callback list.
        self.assertEqual(SOURCE.count("THINK(Zaero_EMPBlastAnim)"), 1)
        self.assertEqual(SOURCE.count("THINK(Zaero_EMPNukeFinish)"), 1)

        fire = function_body(SOURCE, "edict_t *Zaero_FireEMPNuke")
        for saved_edict_member in (
            "owner",
            "count",
            "dmg",
            "s.origin",
            "classname",
            "movetype",
            "s.modelindex",
            "s.skinnum",
            "think",
            "nextthink",
        ):
            self.assertIn(saved_edict_member, fire)

        # Active centers are discovered from saved entities; there is no
        # process-global list that could go stale on load/free/transition.
        self.assertNotIn("std::vector", SOURCE)
        self.assertNotIn("std::unordered", SOURCE)
        self.assertIn("G_FreeEdict(self)", SOURCE)

    def test_sonic_hook_signature_and_root_wiring_ledger_are_complete(self) -> None:
        self.assertIn(
            "bool Zaero_EMPNukeCheck(edict_t *subject, const vec3_t &position);",
            HEADER,
        )
        self.assertIn(
            "using zaero_sonic_emp_check_t = bool (*)(edict_t *subject, const vec3_t &origin);",
            SONIC_HEADER,
        )
        self.assertIn("void Weapon_ZaeroEMPNuke(edict_t *ent);", HEADER)
        self.assertIn("void Zaero_PlayEMPMisfire(edict_t *subject);", HEADER)
        self.assertIn("edict_t *Zaero_FireEMPNuke", HEADER)

        self.assertEqual(len(REQUIRED_INTEGRATION_POINTS), 10)
        self.assertTrue(
            any("Zaero_SetSonicEMPCheck" in step for step in REQUIRED_INTEGRATION_POINTS)
        )
        self.assertTrue(
            any("BFG" in step and "save" in step for step in REQUIRED_INTEGRATION_POINTS)
        )

    def test_live_item_project_and_shared_hook_wiring_is_complete(self) -> None:
        for manifest in (PROJECT, FILTERS):
            self.assertIn("zaero\\g_zaero_emp.h", manifest)
            self.assertIn("zaero\\g_zaero_emp.cpp", manifest)

        item = ITEMS[ITEMS.index('/* classname */ "ammo_empnuke"') :]
        item = item[: item.index("\n\t},")]
        self.assertIn("Weapon_ZaeroEMPNuke", item)
        self.assertIn("IF_AMMO | IF_NO_INFINITE_AMMO", item)
        self.assertNotIn("IF_PENDING_IMPLEMENTATION", item)
        self.assertNotIn("Weapon_ZaeroEMPNukePending", ITEMS)

        self.assertIn("Zaero_SetIREDEMPCheck(Zaero_EMPNukeCheck)", MAIN)
        self.assertIn("Zaero_SetSonicEMPCheck(Zaero_EMPNukeCheck)", MAIN)
        self.assertIn("bool zaero_bfg_emp_misfire", LOCAL)
        self.assertIn("FIELD_AUTO(zaero_bfg_emp_misfire)", SAVE)

    def test_all_current_legacy_query_sites_and_bfg_latch_are_wired(self) -> None:
        current_sites = (
            ("g_combat.cpp", "CheckPowerArmor", 1),
            ("g_monster.cpp", "monster_fire_blaster", 1),
            ("g_monster.cpp", "monster_fire_rocket", 1),
            ("g_monster.cpp", "monster_fire_railgun", 1),
            ("g_monster.cpp", "monster_fire_bfg", 1),
            ("g_target.cpp", "use_target_blaster", 1),
            ("g_turret.cpp", "turret_breach_fire", 1),
            ("m_boss2.cpp", "boss2_firebullet_right", 1),
            ("m_boss2.cpp", "boss2_firebullet_left", 1),
            ("m_boss31.cpp", "jorg_firebullet_right", 1),
            ("m_boss31.cpp", "jorg_firebullet_left", 1),
            ("m_boss32.cpp", "makronBFG", 1),
            ("m_infantry.cpp", "InfantryMachineGun", 1),
            ("m_supertank.cpp", "supertankMachineGun", 1),
            ("m_tank.cpp", "TankMachineGun", 1),
            ("p_weapon.cpp", "Weapon_RocketLauncher_Fire", 1),
            ("p_weapon.cpp", "Blaster_Fire", 1),
            ("p_weapon.cpp", "Chaingun_Fire", 1),
            ("p_weapon.cpp", "weapon_railgun_fire", 1),
            ("p_weapon.cpp", "weapon_bfg_fire", 1),
            ("zaero/g_zaero_autocannon.cpp", "Zaero_AutocannonFire", 1),
        )
        for relative, function, expected in current_sites:
            source = (ROOT / "src" / relative).read_text(encoding="utf-8")
            signature = function
            if relative in {"m_boss32.cpp", "m_infantry.cpp", "m_supertank.cpp"}:
                signature = f"\nvoid {function}(edict_t *self)\n"
            body = function_body(source, signature)
            self.assertEqual(
                body.count("Zaero_EMPNukeCheck"), expected, f"{relative}:{function}"
            )

        ired = (ROOT / "src" / "zaero" / "g_zaero_ired.cpp").read_text(
            encoding="utf-8"
        )
        sonic = (ROOT / "src" / "zaero" / "g_zaero_sonic.cpp").read_text(
            encoding="utf-8"
        )
        self.assertEqual(
            function_body(ired, "THINK(Zaero_IREDLaserThink)").count(
                "zaero_ired_emp_check"
            ),
            2,
        )
        self.assertEqual(
            function_body(sonic, "bool Zaero_SonicEMPBlocked").count(
                "zaero_sonic_emp_check"
            ),
            2,
        )

        bfg = function_body(PLAYER_WEAPONS, "void weapon_bfg_fire")
        self.assertLess(
            bfg.index("ps.gunframe == 9"),
            bfg.index("Zaero_EMPNukeCheck(ent, start)"),
        )
        self.assertIn("zaero_bfg_emp_misfire = false", bfg)
        self.assertIn("zaero_bfg_emp_misfire = true", bfg)
        self.assertIn("P_AddWeaponKick(ent, ent->client->v_forward * -2", bfg)

        for wrapper in (
            "Weapon_RocketLauncher_Fire,!level.is_zaero",
            "Weapon_Blaster_Fire,!level.is_zaero",
            "weapon_railgun_fire,!level.is_zaero",
            "weapon_bfg_fire,!level.is_zaero",
        ):
            self.assertIn(wrapper, compact(PLAYER_WEAPONS))
        self.assertTrue(
            any("ledgers" in step and "live" in step for step in REQUIRED_INTEGRATION_POINTS)
        )


if __name__ == "__main__":
    unittest.main()
