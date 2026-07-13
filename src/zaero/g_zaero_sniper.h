// SPDX-License-Identifier: GPL-2.0-only
#pragma once

struct edict_t;

// Shared integration contract for the isolated Sniper Rifle port:
//
// * gclient_t owns `gtime_t zaero_sniper_charge_ready`; add it to the JSON
//   client-field table as `FIELD_AUTO(zaero_sniper_charge_ready)`.  The field
//   is an absolute level time, not a frame number, and is the only new mutable
//   sniper state.  Existing per-client weapon_think_time supplies the saved
//   10 Hz animation/beep cadence.  Never move either value to file globals.
// * IT_WEAPON_SNIPERRIFLE uses Weapon_ZaeroSniperRifle and drops
//   IF_PENDING_IMPLEMENTATION while retaining IF_NO_WEAPON_SELECTION.
// * mod_id_t appends MOD_ZAERO_SNIPER_RIFLE.  ClientObituary maps it to the
//   legacy attacker text: "{} was ventilated by {}'s bullet\n".
// * SV_CalcGunOffset includes Zaero_SniperSuppressGunOffset in its existing
//   no-bob branch.  This preserves the fixed scope model in every local view.
// * G_SetStats calls Zaero_SniperSetTimerStats after any higher-priority Zaero
//   A2K timer and before ordinary powerups.  The helper writes only this
//   client's stats, so split-screen clients cannot share zoom/HUD state.
// * Forced weapon removal (death, disconnect, respawn, camera/intermission,
//   or an instant switch that bypasses the normal drop frames) calls
//   Zaero_SniperClearClientState before discarding the current weapon.
//   ClientUserinfoChanged may call Zaero_SniperApplyView after writing FOV so
//   an active scope is not lost until the next weapon tick.
// * Add this implementation to the project/filter manifests and remove the
//   obsolete Weapon_ZaeroSniperRiflePending declaration/definition.

// Exact Zaero weapon callback.
void Weapon_ZaeroSniperRifle(edict_t *ent);

// View/HUD/lifecycle hooks for native Rerelease integration.  Each helper
// operates exclusively on the supplied client entity.
bool Zaero_SniperSuppressGunOffset(const edict_t *ent);
void Zaero_SniperApplyView(edict_t *ent);
bool Zaero_SniperSetTimerStats(edict_t *ent);
void Zaero_SniperClearClientState(edict_t *ent);
