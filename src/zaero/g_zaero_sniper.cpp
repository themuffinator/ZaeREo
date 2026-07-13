// SPDX-License-Identifier: GPL-2.0-only

#include "../g_local.h"
#include "../m_player.h"
#include "g_zaero_sniper.h"

namespace
{
// The supplied game advances this custom weapon once per 10 Hz server frame.
// Keep that cadence explicit while the Rerelease host itself runs at 40 Hz.
constexpr gtime_t ZAERO_SNIPER_LEGACY_TICK = 100_ms;
constexpr gtime_t ZAERO_SNIPER_CHARGE_TIME = 3_sec;
constexpr float ZAERO_SNIPER_TRACE_DISTANCE = 8192.0f;

constexpr int32_t ZAERO_SNIPER_AMMO_PER_SHOT = 3;
constexpr int32_t ZAERO_SNIPER_SP_DAMAGE = 250;
constexpr int32_t ZAERO_SNIPER_SP_KICK = 400;
constexpr int32_t ZAERO_SNIPER_DM_DAMAGE = 150;
constexpr int32_t ZAERO_SNIPER_DM_KICK = 300;
constexpr float ZAERO_SNIPER_SP_FOV = 15.0f;
constexpr float ZAERO_SNIPER_DM_FOV = 30.0f;
constexpr float ZAERO_SNIPER_RELEASE_FOV = 90.0f;

constexpr int32_t ZAERO_SNIPER_ACTIVATE_START = 0;
constexpr int32_t ZAERO_SNIPER_ACTIVATE_END = 8;
constexpr int32_t ZAERO_SNIPER_DEACTIVATE_START = 37;
constexpr int32_t ZAERO_SNIPER_DEACTIVATE_END = 41;

constexpr const char *ZAERO_SNIPER_VIEW_MODEL = "models/weapons/v_sniper/tris.md2";
constexpr const char *ZAERO_SNIPER_SP_SCOPE_MODEL = "models/weapons/v_sniper/scope/tris.md2";
constexpr const char *ZAERO_SNIPER_DM_SCOPE_MODEL = "models/weapons/v_sniper/dmscope/tris.md2";
constexpr const char *ZAERO_SNIPER_ICON = "w_sniper";
constexpr const char *ZAERO_SNIPER_BEEP_SOUND = "weapons/sniper/beep.wav";
constexpr const char *ZAERO_SNIPER_FIRE_SOUND = "weapons/sniper/fire.wav";
constexpr const char *ZAERO_SNIPER_ACTIVATE_SOUND = "weapons/sniper/snip_act.wav";
constexpr const char *ZAERO_SNIPER_DEACTIVATE_SOUND = "weapons/sniper/snip_bye.wav";

bool Zaero_SniperEquipped(const edict_t *ent)
{
	return ent && ent->client && ent->client->pers.weapon &&
		ent->client->pers.weapon->id == IT_WEAPON_SNIPERRIFLE;
}

bool Zaero_SniperScoped(const edict_t *ent)
{
	return Zaero_SniperEquipped(ent) &&
		(ent->client->weaponstate == WEAPON_READY || ent->client->weaponstate == WEAPON_FIRING);
}

void Zaero_SniperScheduleLegacyTick(edict_t *ent)
{
	ent->client->weapon_think_time = level.time + ZAERO_SNIPER_LEGACY_TICK;
	ent->client->ps.gunrate = 0;
}

void Zaero_SniperStartCharge(edict_t *ent)
{
	ent->client->zaero_sniper_charge_ready = level.time + ZAERO_SNIPER_CHARGE_TIME;

	// Rerelease input buffering consults this native deadline before calling a
	// weapon from ClientThink.  The dedicated Zaero field remains authoritative
	// because native haste bookkeeping may adjust weapon_fire_finished.
	ent->client->weapon_fire_finished = ent->client->zaero_sniper_charge_ready;
}

void Zaero_SniperResetCharge(edict_t *ent)
{
	ent->client->zaero_sniper_charge_ready = 0_ms;
	ent->client->weapon_fire_finished = 0_ms;
}

void Zaero_SniperPlayDMActivate(edict_t *ent)
{
	if (deathmatch->integer)
		gi.sound(ent, CHAN_WEAPON, gi.soundindex(ZAERO_SNIPER_ACTIVATE_SOUND), 1.0f, ATTN_NORM, 0);
}

void Zaero_SniperPlayDMDeactivate(edict_t *ent)
{
	if (deathmatch->integer)
	{
		// Legacy CHAN_WEAPON2 is numeric channel 5, named CHAN_AUX by the
		// Rerelease API.  It intentionally does not cut off CHAN_WEAPON.
		gi.sound(ent, CHAN_AUX, gi.soundindex(ZAERO_SNIPER_DEACTIVATE_SOUND), 1.0f, ATTN_NORM, 0);
	}
}

void Zaero_SniperImpact(const trace_t &tr)
{
	const bool in_water = (gi.pointcontents(tr.endpos) & MASK_WATER) != CONTENTS_NONE;
	const bool floor_hit = tr.plane.normal.z > 0.7f;

	gi.WriteByte(svc_temp_entity);
	if (in_water)
		gi.WriteByte(floor_hit ? TE_GRENADE_EXPLOSION_WATER : TE_ROCKET_EXPLOSION_WATER);
	else
		gi.WriteByte(floor_hit ? TE_GRENADE_EXPLOSION : TE_ROCKET_EXPLOSION);
	gi.WritePosition(tr.endpos);
	gi.multicast(tr.endpos, MULTICAST_PHS, false);
}

void Zaero_FireSniperBullet(edict_t *self, const vec3_t &start, const vec3_t &aimdir, int32_t damage, int32_t kick)
{
	const vec3_t end = start + (aimdir * ZAERO_SNIPER_TRACE_DISTANCE);
	vec3_t trace_start = start;
	edict_t *ignore = self;
	trace_t tr = {};

	// Zaero's MASK_SHOT_NO_WINDOW is MASK_SHOT without CONTENTS_WINDOW.
	// Preserve the Rerelease no-player-collision contract used by its other
	// hitscan weapons while retaining player hits in ordinary DM/friendly-fire.
	contents_t mask = MASK_SHOT & ~CONTENTS_WINDOW;
	if (self->client && !G_ShouldPlayersCollide(true))
		mask &= ~CONTENTS_PLAYER;

	for (;;)
	{
		tr = gi.traceline(trace_start, end, ignore, mask);
		if (tr.fraction >= 1.0f || !tr.ent)
			return;

		// Only Plasma Shields are penetrated.  The shot stops on the first
		// subsequent entity; unlike a rail slug, it does not pierce actors.
		if (tr.ent->classname && !Q_strcasecmp(tr.ent->classname, "PlasmaShield"))
		{
			ignore = tr.ent;
			trace_start = tr.endpos;
			continue;
		}

		break;
	}

	Zaero_SniperImpact(tr);

	if (tr.ent->takedamage)
	{
		T_Damage(tr.ent, self, self, aimdir, tr.endpos, tr.plane.normal,
			damage, kick, DAMAGE_NO_ARMOR, MOD_ZAERO_SNIPER_RIFLE);
	}
}

void Zaero_SniperFire(edict_t *ent)
{
	int32_t damage = deathmatch->integer ? ZAERO_SNIPER_DM_DAMAGE : ZAERO_SNIPER_SP_DAMAGE;
	int32_t kick = deathmatch->integer ? ZAERO_SNIPER_DM_KICK : ZAERO_SNIPER_SP_KICK;

	// For a real Quad, Rerelease damage_multiplier is exactly four.  Using the
	// native multiplier also composes correctly with its mission-pack Double
	// and no-stack rules without turning Double into a false four-times boost.
	if (is_quad)
	{
		damage *= damage_multiplier;
		kick *= damage_multiplier;
	}

	vec3_t forward;
	AngleVectors(ent->client->v_angle, forward, nullptr, nullptr);

	// The original deliberately fires from the exact eye centre.  Do not route
	// this through P_ProjectSource: handedness and aim correction would alter
	// both close-wall traces and the scope's apparent point of impact.
	const vec3_t start = ent->s.origin + vec3_t{0.0f, 0.0f, static_cast<float>(ent->viewheight)};
	Zaero_FireSniperBullet(ent, start, forward, damage, kick);

	const float volume = is_silenced ? 0.4f : 1.0f;
	gi.sound(ent, CHAN_WEAPON, gi.soundindex(ZAERO_SNIPER_FIRE_SOUND), volume, ATTN_NORM, 0);
	PlayerNoise(ent, start, PNOISE_WEAPON);
	Weapon_PowerupSound(ent);
	P_AddWeaponKick(ent, forward * -20.0f, {-2.0f, 0.0f, 0.0f});

	if (ent->client->pers.weapon->ammo)
	{
		int32_t &slugs = ent->client->pers.inventory[ent->client->pers.weapon->ammo];

		// This direct subtraction is intentional.  Unlike the ordinary Zaero
		// weapons, the supplied sniper consumes its three slugs even when the
		// legacy infinite-ammo flag is active (that mode merely grants 1000 on
		// pickup).  Do not replace it with G_RemoveAmmo.
		slugs = max(0, slugs - ZAERO_SNIPER_AMMO_PER_SHOT);
	}
}

void Zaero_SniperStartPlayerAttackAnimation(edict_t *ent)
{
	ent->client->anim_priority = ANIM_ATTACK;
	if (ent->client->ps.pmove.pm_flags & PMF_DUCKED)
	{
		ent->s.frame = FRAME_crattak1 - 1;
		ent->client->anim_end = FRAME_crattak9;
	}
	else
	{
		ent->s.frame = FRAME_attack1 - 1;
		ent->client->anim_end = FRAME_attack8;
	}
	ent->client->anim_time = 0_ms;
	ent->client->last_firing_time = level.time + COOP_DAMAGE_FIRING_TIME;
}

void Zaero_SniperNoAmmo(edict_t *ent)
{
	// Preserve the source's voice channel and entity pain debounce rather than
	// delegating the click to Rerelease's CHAN_WEAPON/empty_click_sound path.
	if (level.time >= ent->pain_debounce_time)
	{
		gi.sound(ent, CHAN_VOICE, gi.soundindex("weapons/noammo.wav"), 1.0f, ATTN_NORM, 0);
		ent->pain_debounce_time = level.time + 1_sec;
	}
	NoAmmoWeaponChange(ent, false);
}

void Zaero_SniperBeepIfDue(edict_t *ent)
{
	if (ent->client->zaero_sniper_charge_ready < level.time)
		return;

	const int64_t remaining_legacy_ticks =
		(ent->client->zaero_sniper_charge_ready - level.time).milliseconds() /
		ZAERO_SNIPER_LEGACY_TICK.milliseconds();

	// `(ready_frame - level.framenum) % 10 == 1` produces beeps 0.9,
	// 1.9, and 2.9 seconds into each three-second charge.
	if ((remaining_legacy_ticks % 10) == 1)
		gi.sound(ent, CHAN_AUX, gi.soundindex(ZAERO_SNIPER_BEEP_SOUND), 1.0f, ATTN_NORM, 0);
}
} // namespace

bool Zaero_SniperSuppressGunOffset(const edict_t *ent)
{
	// The supplied p_view check keys only on the current sniper classname, so
	// suppression spans activation, scoped use, and deactivation alike.
	return Zaero_SniperEquipped(ent);
}

void Zaero_SniperApplyView(edict_t *ent)
{
	if (!Zaero_SniperScoped(ent))
		return;

	ent->client->ps.gunindex = gi.modelindex(
		deathmatch->integer ? ZAERO_SNIPER_DM_SCOPE_MODEL : ZAERO_SNIPER_SP_SCOPE_MODEL);
	ent->client->ps.gunskin = 0;
	ent->client->ps.gunframe = 0;
	ent->client->ps.fov = deathmatch->integer ? ZAERO_SNIPER_DM_FOV : ZAERO_SNIPER_SP_FOV;
}

bool Zaero_SniperSetTimerStats(edict_t *ent)
{
	if (!ent || !ent->client || !ent->client->zaero_sniper_charge_ready ||
		ent->client->zaero_sniper_charge_ready < level.time)
	{
		return false;
	}

	ent->client->ps.stats[STAT_TIMER_ICON] = gi.imageindex(ZAERO_SNIPER_ICON);
	// Legacy integer division truncates rather than rounds up.
	ent->client->ps.stats[STAT_TIMER] = static_cast<int16_t>(
		(ent->client->zaero_sniper_charge_ready - level.time).milliseconds() / 1000);
	return true;
}

void Zaero_SniperClearClientState(edict_t *ent)
{
	if (!ent || !ent->client)
		return;

	const bool had_sniper_state = Zaero_SniperEquipped(ent) ||
		ent->client->zaero_sniper_charge_ready != 0_ms;
	Zaero_SniperResetCharge(ent);
	ent->client->weapon_fire_buffered = false;
	if (had_sniper_state)
		ent->client->ps.fov = ZAERO_SNIPER_RELEASE_FOV;
}

void Weapon_ZaeroSniperRifle(edict_t *ent)
{
	if (!Zaero_SniperEquipped(ent))
		return;

	ent->client->ps.gunrate = 0;

	if (ent->client->weaponstate == WEAPON_DROPPING)
	{
		if (ent->client->weapon_think_time > level.time)
			return;

		// The legacy function clears its HUD/reload counter on every dropping
		// frame, before testing the animation frame itself.
		Zaero_SniperResetCharge(ent);

		if (ent->client->ps.gunframe == ZAERO_SNIPER_DEACTIVATE_START)
		{
			// Deliberately restore 90 rather than the userinfo FOV.  This is a
			// visible Zaero quirk shared by both ordinary and fixed-FOV games.
			ent->client->ps.fov = ZAERO_SNIPER_RELEASE_FOV;
			Zaero_SniperPlayDMDeactivate(ent);
		}
		else if (ent->client->ps.gunframe == ZAERO_SNIPER_DEACTIVATE_END)
		{
			ChangeWeapon(ent);
			return;
		}

		ent->client->ps.gunframe++;
		Zaero_SniperScheduleLegacyTick(ent);
		return;
	}

	if (ent->client->weaponstate == WEAPON_ACTIVATING)
	{
		if (ent->client->weapon_think_time > level.time && !g_instant_weapon_switch->integer)
			return;

		if (ent->client->ps.gunframe == ZAERO_SNIPER_ACTIVATE_START)
			Zaero_SniperPlayDMActivate(ent);

		if (ent->client->ps.gunframe == ZAERO_SNIPER_ACTIVATE_END || g_instant_weapon_switch->integer)
		{
			ent->client->weaponstate = WEAPON_READY;
			ent->client->ps.gunframe = 0;
			Zaero_SniperApplyView(ent);
			Zaero_SniperStartCharge(ent);
			Zaero_SniperScheduleLegacyTick(ent);
			return;
		}

		ent->client->ps.gunframe++;
		Zaero_SniperScheduleLegacyTick(ent);
		return;
	}

	if (ent->client->newweapon && ent->client->weaponstate != WEAPON_FIRING)
	{
		if (ent->client->weapon_think_time > level.time && !g_instant_weapon_switch->integer)
			return;

		ent->client->ps.gunindex = gi.modelindex(ZAERO_SNIPER_VIEW_MODEL);
		ent->client->ps.gunskin = 0;
		ent->client->weaponstate = WEAPON_DROPPING;
		ent->client->ps.gunframe = ZAERO_SNIPER_DEACTIVATE_START;

		if (g_instant_weapon_switch->integer)
		{
			Zaero_SniperClearClientState(ent);
			Zaero_SniperPlayDMDeactivate(ent);
			ChangeWeapon(ent);
			return;
		}

		Zaero_SniperScheduleLegacyTick(ent);
		return;
	}

	Zaero_SniperApplyView(ent);

	if (ent->client->weapon_think_time > level.time)
		return;

	if (ent->client->weaponstate == WEAPON_READY)
	{
		Zaero_SniperBeepIfDue(ent);

		const bool request_firing = ent->client->weapon_fire_buffered ||
			((ent->client->latched_buttons | ent->client->buttons) & BUTTON_ATTACK);
		if (request_firing && level.time >= ent->client->zaero_sniper_charge_ready)
		{
			ent->client->latched_buttons &= ~BUTTON_ATTACK;
			ent->client->weapon_fire_buffered = false;

			const item_id_t ammo = ent->client->pers.weapon->ammo;
			if (!ammo || ent->client->pers.inventory[ammo] >= ZAERO_SNIPER_AMMO_PER_SHOT)
			{
				ent->client->weaponstate = WEAPON_FIRING;
				Zaero_SniperStartPlayerAttackAnimation(ent);
			}
			else
			{
				Zaero_SniperNoAmmo(ent);
			}
		}
	}

	if (ent->client->weaponstate == WEAPON_FIRING)
	{
		Zaero_SniperApplyView(ent);
		Zaero_SniperFire(ent);
		ent->client->weaponstate = WEAPON_READY;
		Zaero_SniperStartCharge(ent);
	}

	Zaero_SniperScheduleLegacyTick(ent);
}
