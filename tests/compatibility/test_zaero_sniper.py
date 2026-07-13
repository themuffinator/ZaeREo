from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HEADER = (ROOT / "src" / "zaero" / "g_zaero_sniper.h").read_text(encoding="utf-8")
SOURCE = (ROOT / "src" / "zaero" / "g_zaero_sniper.cpp").read_text(encoding="utf-8")
ASSET_AUDIT = json.loads((ROOT / "docs" / "audits" / "assets.json").read_text(encoding="utf-8"))


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text)


class ZaeroSniperConstantsTests(unittest.TestCase):
    def test_exact_ammo_damage_kick_fov_range_and_cadence(self) -> None:
        for declaration in (
            "constexpr gtime_t ZAERO_SNIPER_LEGACY_TICK = 100_ms",
            "constexpr gtime_t ZAERO_SNIPER_CHARGE_TIME = 3_sec",
            "constexpr float ZAERO_SNIPER_TRACE_DISTANCE = 8192.0f",
            "constexpr int32_t ZAERO_SNIPER_AMMO_PER_SHOT = 3",
            "constexpr int32_t ZAERO_SNIPER_SP_DAMAGE = 250",
            "constexpr int32_t ZAERO_SNIPER_SP_KICK = 400",
            "constexpr int32_t ZAERO_SNIPER_DM_DAMAGE = 150",
            "constexpr int32_t ZAERO_SNIPER_DM_KICK = 300",
            "constexpr float ZAERO_SNIPER_SP_FOV = 15.0f",
            "constexpr float ZAERO_SNIPER_DM_FOV = 30.0f",
            "constexpr float ZAERO_SNIPER_RELEASE_FOV = 90.0f",
        ):
            self.assertIn(declaration, SOURCE)

    def test_exact_animation_boundaries_and_10hz_gate(self) -> None:
        for declaration in (
            "ZAERO_SNIPER_ACTIVATE_START = 0",
            "ZAERO_SNIPER_ACTIVATE_END = 8",
            "ZAERO_SNIPER_DEACTIVATE_START = 37",
            "ZAERO_SNIPER_DEACTIVATE_END = 41",
        ):
            self.assertIn(declaration, SOURCE)
        self.assertIn("weapon_think_time = level.time + ZAERO_SNIPER_LEGACY_TICK", SOURCE)
        self.assertIn("ent->client->ps.gunrate = 0", SOURCE)
        self.assertIn("(remaining_legacy_ticks % 10) == 1", SOURCE)
        self.assertIn("0.9,", SOURCE)
        self.assertIn("1.9, and 2.9 seconds", SOURCE)

    def test_all_runtime_assets_are_locked_and_present_in_canonical_audit(self) -> None:
        expected = {
            "models/weapons/g_sniper/tris.md2",
            "models/weapons/v_sniper/tris.md2",
            "models/weapons/v_sniper/scope/tris.md2",
            "models/weapons/v_sniper/dmscope/tris.md2",
            "pics/w_sniper.pcx",
            "sound/weapons/sniper/beep.wav",
            "sound/weapons/sniper/fire.wav",
            "sound/weapons/sniper/snip_act.wav",
            "sound/weapons/sniper/snip_bye.wav",
        }

        def collect_paths(value: object) -> set[str]:
            paths: set[str] = set()
            if isinstance(value, dict):
                path = value.get("path")
                if isinstance(path, str):
                    paths.add(path)
                for child in value.values():
                    paths.update(collect_paths(child))
            elif isinstance(value, list):
                for child in value:
                    paths.update(collect_paths(child))
            return paths

        audit_paths = collect_paths(ASSET_AUDIT)
        self.assertTrue(expected <= audit_paths)
        for path in expected - {"models/weapons/g_sniper/tris.md2", "pics/w_sniper.pcx"}:
            runtime_path = path.removeprefix("sound/")
            self.assertIn(runtime_path, SOURCE)


class ZaeroSniperTraceAndDamageTests(unittest.TestCase):
    def test_trace_ignores_windows_and_only_penetrates_plasma_shields(self) -> None:
        normalized = compact(SOURCE)
        self.assertIn("contents_t mask = MASK_SHOT & ~CONTENTS_WINDOW", normalized)
        self.assertIn("mask &= ~CONTENTS_PLAYER", SOURCE)
        self.assertIn("G_ShouldPlayersCollide(true)", SOURCE)
        self.assertIn('Q_strcasecmp(tr.ent->classname, "PlasmaShield")', SOURCE)
        self.assertIn("ignore = tr.ent", SOURCE)
        self.assertIn("trace_start = tr.endpos", SOURCE)
        self.assertNotIn("pierce_trace", SOURCE)

    def test_first_non_shield_hit_gets_legacy_impact_and_no_armor_damage(self) -> None:
        for effect in (
            "TE_GRENADE_EXPLOSION_WATER",
            "TE_ROCKET_EXPLOSION_WATER",
            "TE_GRENADE_EXPLOSION",
            "TE_ROCKET_EXPLOSION",
        ):
            self.assertIn(effect, SOURCE)
        self.assertIn("tr.plane.normal.z > 0.7f", SOURCE)
        self.assertIn("gi.multicast(tr.endpos, MULTICAST_PHS, false)", SOURCE)
        self.assertRegex(
            compact(SOURCE),
            r"T_Damage\(tr\.ent, self, self, aimdir, tr\.endpos, tr\.plane\.normal, damage, kick, DAMAGE_NO_ARMOR, MOD_ZAERO_SNIPER_RIFLE\)",
        )

    def test_eye_center_origin_recoil_noise_silencing_and_powerups(self) -> None:
        self.assertIn("ent->s.origin + vec3_t{0.0f, 0.0f, static_cast<float>(ent->viewheight)}", SOURCE)
        self.assertNotIn("P_ProjectSource(ent", SOURCE)
        self.assertIn("is_silenced ? 0.4f : 1.0f", SOURCE)
        self.assertIn("P_AddWeaponKick(ent, forward * -20.0f, {-2.0f, 0.0f, 0.0f})", SOURCE)
        self.assertIn("PlayerNoise(ent, start, PNOISE_WEAPON)", SOURCE)
        self.assertIn("Weapon_PowerupSound(ent)", SOURCE)
        self.assertIn("damage *= damage_multiplier", SOURCE)
        self.assertIn("kick *= damage_multiplier", SOURCE)

    def test_three_slugs_are_consumed_even_with_legacy_infinite_ammo(self) -> None:
        fire = SOURCE[SOURCE.index("void Zaero_SniperFire") : SOURCE.index("void Zaero_SniperStartPlayerAttackAnimation")]
        self.assertIn("slugs - ZAERO_SNIPER_AMMO_PER_SHOT", fire)
        self.assertNotRegex(fire, r"\bG_RemoveAmmo\s*\(")
        self.assertNotRegex(fire, r"\bG_CheckInfiniteAmmo\s*\(")


class ZaeroSniperStateMachineTests(unittest.TestCase):
    def test_scope_models_fov_and_dm_only_switch_sounds(self) -> None:
        self.assertIn("deathmatch->integer ? ZAERO_SNIPER_DM_SCOPE_MODEL : ZAERO_SNIPER_SP_SCOPE_MODEL", SOURCE)
        self.assertIn("deathmatch->integer ? ZAERO_SNIPER_DM_FOV : ZAERO_SNIPER_SP_FOV", SOURCE)
        self.assertRegex(
            compact(SOURCE),
            r"void Zaero_SniperPlayDMActivate\(edict_t \*ent\).*?if \(deathmatch->integer\).*?CHAN_WEAPON.*?ZAERO_SNIPER_ACTIVATE_SOUND",
        )
        self.assertRegex(
            compact(SOURCE),
            r"void Zaero_SniperPlayDMDeactivate\(edict_t \*ent\).*?if \(deathmatch->integer\).*?CHAN_AUX.*?ZAERO_SNIPER_DEACTIVATE_SOUND",
        )
        self.assertIn("CHAN_AUX, gi.soundindex(ZAERO_SNIPER_BEEP_SOUND)", SOURCE)

    def test_charge_blocks_input_without_discarding_it_then_restarts_after_fire(self) -> None:
        normalized = compact(SOURCE)
        self.assertIn("request_firing && level.time >= ent->client->zaero_sniper_charge_ready", normalized)
        self.assertIn("ent->client->weapon_fire_buffered ||", SOURCE)
        self.assertIn("ent->client->latched_buttons | ent->client->buttons", SOURCE)
        self.assertGreaterEqual(SOURCE.count("Zaero_SniperStartCharge(ent)"), 2)
        self.assertIn("ent->client->weaponstate = WEAPON_READY", SOURCE)

    def test_no_ammo_uses_legacy_channel_debounce_and_native_fallback_selection(self) -> None:
        no_ammo = SOURCE[SOURCE.index("void Zaero_SniperNoAmmo") : SOURCE.index("void Zaero_SniperBeepIfDue")]
        self.assertIn("CHAN_VOICE", no_ammo)
        self.assertIn('"weapons/noammo.wav"', no_ammo)
        self.assertIn("ent->pain_debounce_time = level.time + 1_sec", no_ammo)
        self.assertIn("NoAmmoWeaponChange(ent, false)", no_ammo)

    def test_view_bob_timer_and_forced_lifecycle_are_per_client_hooks(self) -> None:
        for declaration in (
            "bool Zaero_SniperSuppressGunOffset(const edict_t *ent)",
            "void Zaero_SniperApplyView(edict_t *ent)",
            "bool Zaero_SniperSetTimerStats(edict_t *ent)",
            "void Zaero_SniperClearClientState(edict_t *ent)",
        ):
            self.assertIn(declaration, HEADER)
            self.assertIn(declaration, SOURCE)
        self.assertIn("STAT_TIMER_ICON", SOURCE)
        self.assertIn("STAT_TIMER", SOURCE)
        self.assertIn("/ 1000", SOURCE)
        self.assertIn("ps.fov = ZAERO_SNIPER_RELEASE_FOV", SOURCE)

    def test_save_split_screen_and_shared_integration_requirements_are_explicit(self) -> None:
        requirements = (
            "gtime_t zaero_sniper_charge_ready",
            "FIELD_AUTO(zaero_sniper_charge_ready)",
            "IT_WEAPON_SNIPERRIFLE uses Weapon_ZaeroSniperRifle",
            "MOD_ZAERO_SNIPER_RIFLE",
            "was ventilated by {}'s bullet",
            "SV_CalcGunOffset",
            "G_SetStats",
            "death, disconnect, respawn, camera/intermission",
            "ClientUserinfoChanged",
            "project/filter manifests",
        )
        for requirement in requirements:
            self.assertIn(requirement, HEADER)
        self.assertNotRegex(SOURCE, r"\bstatic\s+(?:gtime_t|bool|int32_t|float)\s+zaero_sniper")

    def test_shared_integration_hooks_are_implemented_and_saved(self) -> None:
        project = (ROOT / "src" / "game.vcxproj").read_text(encoding="utf-8")
        filters = (ROOT / "src" / "game.vcxproj.filters").read_text(encoding="utf-8")
        items = (ROOT / "src" / "g_items.cpp").read_text(encoding="utf-8")
        local = (ROOT / "src" / "g_local.h").read_text(encoding="utf-8")
        save = (ROOT / "src" / "g_save.cpp").read_text(encoding="utf-8")
        client = (ROOT / "src" / "p_client.cpp").read_text(encoding="utf-8")
        hud = (ROOT / "src" / "p_hud.cpp").read_text(encoding="utf-8")
        view = (ROOT / "src" / "p_view.cpp").read_text(encoding="utf-8")
        weapon = (ROOT / "src" / "p_weapon.cpp").read_text(encoding="utf-8")

        for manifest in (project, filters):
            self.assertIn("zaero\\g_zaero_sniper.h", manifest)
            self.assertIn("zaero\\g_zaero_sniper.cpp", manifest)
        self.assertIn("Weapon_ZaeroSniperRifle", items)
        self.assertNotIn("Weapon_ZaeroSniperRiflePending", items)
        sniper_item = items[items.index('/* classname */ "weapon_sniperrifle"') :]
        sniper_item = sniper_item[: sniper_item.index("\n\t},")]
        self.assertIn("IF_NO_WEAPON_SELECTION", sniper_item)
        self.assertNotIn("IF_PENDING_IMPLEMENTATION", sniper_item)
        self.assertIn("MOD_ZAERO_SNIPER_RIFLE", local)
        self.assertIn("gtime_t zaero_sniper_charge_ready", local)
        self.assertIn("FIELD_AUTO(zaero_sniper_charge_ready)", save)
        self.assertIn("was ventilated by {}'s bullet", client)
        self.assertIn("Zaero_SniperApplyView(ent)", client)
        self.assertIn("Zaero_SniperSetTimerStats(ent)", hud)
        self.assertIn("Zaero_SniperSuppressGunOffset(ent)", view)
        self.assertIn("Zaero_SniperClearClientState(ent)", weapon)


if __name__ == "__main__":
    unittest.main()
